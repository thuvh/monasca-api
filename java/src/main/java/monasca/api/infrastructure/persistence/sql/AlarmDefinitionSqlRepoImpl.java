/*
 * Copyright 2015 FUJITSU LIMITED
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */
package monasca.api.infrastructure.persistence.sql;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;

import javax.inject.Inject;
import javax.inject.Named;

import monasca.api.domain.exception.EntityNotFoundException;
import monasca.api.domain.model.alarmdefinition.AlarmDefinition;
import monasca.api.domain.model.alarmdefinition.AlarmDefinitionRepo;
import monasca.api.infrastructure.persistence.SubAlarmDefinitionQueries;
import monasca.common.hibernate.db.AlarmActionDb;
import monasca.common.hibernate.db.AlarmDefinitionDb;
import monasca.common.hibernate.db.SubAlarmDefinitionDb;
import monasca.common.hibernate.db.SubAlarmDefinitionDimensionDb;
import monasca.common.model.alarm.AggregateFunction;
import monasca.common.model.alarm.AlarmOperator;
import monasca.common.model.alarm.AlarmSeverity;
import monasca.common.model.alarm.AlarmState;
import monasca.common.model.alarm.AlarmSubExpression;
import monasca.common.model.metric.MetricDefinition;

import org.hibernate.Query;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.joda.time.DateTime;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.common.base.Joiner;
import com.google.common.base.Splitter;
import com.google.common.collect.Iterables;
import com.google.common.collect.Lists;

/**
 * Alarm repository implementation.
 */
public class AlarmDefinitionSqlRepoImpl implements AlarmDefinitionRepo {

  private static final Logger logger = LoggerFactory.getLogger(AlarmDefinitionSqlRepoImpl.class);
  private static final String ID = "ID";
  private static final String NAME = "NAME";
  private static final String DESCRIPTION = "DESCRIPTION";
  private static final String EXPRESSION = "EXPRESSION";
  private static final String SEVERITY = "SEVERITY";
  private static final String MATCH_BY = "MATCH_BY";
  private static final String ACTIONS_ENABLED = "ACTIONS_ENABLED";
  private static final String STATE = "STATES";
  private static final String NOTIFICATION_ID = "NOTIFICATIONIDS";
  private static final Joiner COMMA_JOINER = Joiner.on(',');
  private static final Splitter COMMA_SPLITTER = Splitter.on(',').omitEmptyStrings().trimResults();
  private static final String QUERY_FIND_SUBALARMDEF_BY_ID = "from SubAlarmDefinitionDb sad where sad.alarm_definition_id = :id";
  private static final String QUERY_INNER_JOIN_SUB_ALARM_DEF_WITH_DIMENSION =
      "SELECT sadd from SubAlarmDefinitionDb sad, SubAlarmDefinitionDimensionDb sadd "
          + "where sadd.subAlarmDefinitionDimensionId.sub_alarm_definition_id = sad.id AND sad.alarm_definition_id = :id";
  private final SessionFactory sessionFactory;

  @Inject
  public AlarmDefinitionSqlRepoImpl(@Named("orm") SessionFactory sessionFactory) {
    this.sessionFactory = sessionFactory;
  }

  @Override
  public AlarmDefinition create(String tenantId, String id, String name, String description, String severity, String expression,
      Map<String, AlarmSubExpression> subExpressions, List<String> matchBy, List<String> alarmActions, List<String> okActions,
      List<String> undeterminedActions) {

    Transaction tx = null;
    Session session = null;
    try {
      session = sessionFactory.openSession();
      tx = session.beginTransaction();

      AlarmDefinitionDb alarmDefinitionDb =
          new AlarmDefinitionDb(id, tenantId, name, description, expression, AlarmSeverity.valueOf(severity), matchBy == null
              || Iterables.isEmpty(matchBy) ? null : COMMA_JOINER.join(matchBy), 1, new DateTime(), new DateTime(), null);
      session.save(alarmDefinitionDb);

      createSubExpressions(session, id, subExpressions);

      // Persist actions
      persistActions(session, id, AlarmState.ALARM, alarmActions);
      persistActions(session, id, AlarmState.OK, okActions);
      persistActions(session, id, AlarmState.UNDETERMINED, undeterminedActions);

      tx.commit();
      return new AlarmDefinition(id, name, description, severity, expression, matchBy, true, alarmActions,
          okActions == null ? Collections.<String>emptyList() : okActions, undeterminedActions == null ? Collections.<String>emptyList()
              : undeterminedActions);

    } catch (RuntimeException e) {
      try {
        tx.rollback();
      } catch (RuntimeException rbe) {
        logger.error("Couldn’t roll back transaction", rbe);
      }
      throw e;
    } finally {
      if (session != null) {
        session.close();
      }
    }
  }

  @Override
  public void deleteById(String tenantId, String alarmDefId) {
    Session session = null;
    Transaction tx = null;
    try {
      session = sessionFactory.openSession();
      tx = session.beginTransaction();

      AlarmDefinitionDb result =
          (AlarmDefinitionDb) session.createQuery("from AlarmDefinitionDb where tenant_id = :tenant_id and id = :id and deleted_at is NULL")
              .setString("tenant_id", tenantId).setString("id", alarmDefId).uniqueResult();

      result.setDeleted_at(new DateTime());
      session.update(result);

      // Cascade soft delete to alarms
      session.createQuery("delete from AlarmDb where alarm_definition_id = :alarm_definition_id").setString("alarm_definition_id", alarmDefId)
          .executeUpdate();

      tx.commit();
    } catch (RuntimeException e) {
      try {
        tx.rollback();
      } catch (RuntimeException rbe) {
        logger.error("Couldn’t roll back transaction", rbe);
      }
      throw e;
    } finally {
      if (session != null) {
        session.close();
      }
    }
  }

  @Override
  public String exists(String tenantId, String name) {
    Session session = null;
    try {
      session = sessionFactory.openSession();

      Query query =
          session.createQuery("select id from AlarmDefinitionDb where tenant_id = :tenantId and name = :name and deleted_at is NULL")
              .setString("tenantId", tenantId).setString("name", name);
      List<String> ids = query.list();
      if (ids != null) {
        if (ids.size() != 0) {
          return ids.get(0);
        } else {
          return null;
        }
      } else {
        return null;
      }
    } finally {
      if (session != null) {
        session.close();
      }
    }
  }

  @Override
  public List<AlarmDefinition> find(String tenantId, String name, Map<String, String> dimensions, String offset, int limit) {
    Session session = null;
    List<AlarmDefinition> resultSet = new ArrayList<AlarmDefinition>();

    String query =
        "  SELECT t.id, t.tenant_id, t.name, t.description, t.expression, t.severity, t.match_by, "
            + "t.actions_enabled, aa.alarm_state AS states, aa.action_id AS notificationIds "
            + "FROM (SELECT distinct ad.id, ad.tenant_id, ad.name, ad.description, ad.expression, "
            + "ad.severity, ad.match_by, ad.actions_enabled, ad.created_at, ad.updated_at, ad.deleted_at "
            + "FROM alarm_definition AS ad LEFT OUTER JOIN sub_alarm_definition AS sad ON ad.id = sad.alarm_definition_id "
            + "LEFT OUTER JOIN sub_alarm_definition_dimension AS dim ON sad.id = dim.sub_alarm_definition_id %1$s "
            + "WHERE ad.tenant_id = :tenantId AND ad.deleted_at IS NULL %2$s %3$s) AS t "
            + "LEFT OUTER JOIN alarm_action AS aa ON t.id = aa.alarm_definition_id ORDER BY t.id, t.created_at";

    StringBuilder sbWhere = new StringBuilder();

    if (name != null) {
      sbWhere.append(" and ad.name = :name");
    }

    if (offset != null) {
      sbWhere.append(" and ad.id > :offset");
    }

    String limitPart = "";
    if (limit > 0) {
      limitPart = " limit :limit";
    }

    String sql = String.format(query, SubAlarmDefinitionQueries.buildJoinClauseFor(dimensions), sbWhere, limitPart);

    try {
      session = sessionFactory.openSession();

      Query qAlarmDefinition = session.createSQLQuery(sql).setString("tenantId", tenantId);
      qAlarmDefinition.setResultTransformer(ResultTransformer.INSTANCE);

      if (name != null) {
        qAlarmDefinition.setString("name", name);
      }

      if (offset != null) {
        qAlarmDefinition.setString("offset", offset);
      }

      if (limit > 0) {
        qAlarmDefinition.setInteger("limit", limit + 1);
      }

      bindDimensionsToQuery(qAlarmDefinition, dimensions);

      final List<Map> alarmDefinitionDbList = qAlarmDefinition.list();

      if (alarmDefinitionDbList != null && alarmDefinitionDbList.size() > 0) {
        resultSet = createAlarmDefinitions(alarmDefinitionDbList);
      }
    } finally {
      if (session != null) {
        session.close();
      }
    }
    return resultSet;
  }

  @Override
  public AlarmDefinition findById(String tenantId, String alarmDefId) {
    Session session = null;
    List<String> okActionIds = new ArrayList<String>();
    List<String> alarmActionIds = new ArrayList<String>();
    List<String> undeterminedActionIds = new ArrayList<String>();
    boolean isEnabled = true;

    try {
      session = sessionFactory.openSession();

      Query qAlarmDefinition =
          session
              .createQuery(
                  "from AlarmDefinitionDb alarm_definition WHERE alarm_definition.tenant_id = :tenant_id AND alarm_definition.id= :alarmDefId AND alarm_definition.deleted_at "
                      + " IS NULL GROUP BY alarm_definition.id").setString("tenant_id", tenantId).setString("alarmDefId", alarmDefId);
      AlarmDefinitionDb alarmDefinitionDb = (AlarmDefinitionDb) qAlarmDefinition.uniqueResult();

      Query qAlarmAction =
          session
              .createQuery(
                  "SELECT distinct alarm_action from AlarmActionDb alarm_action, AlarmDefinitionDb alarm_definition "
                      + "where alarm_definition.id=alarm_action.alarmActionId.alarm_definition_id AND alarm_definition.deleted_at IS NULL AND alarm_definition.tenant_id= :tenantId AND alarm_definition.id= :alarmDefId")
              .setString("tenantId", tenantId).setString("alarmDefId", alarmDefId);

      List<AlarmActionDb> alarmActionList = qAlarmAction.list();

      for (AlarmActionDb alarmAction : alarmActionList) {

        if (alarmAction.getAlarmActionId().getAlarm_state().name().equals(AlarmState.UNDETERMINED.name())) {
          undeterminedActionIds.add(alarmAction.getAlarmActionId().getAction_id());
        } else if (alarmAction.getAlarmActionId().getAlarm_state().name().equals(AlarmState.OK.name())) {
          okActionIds.add(alarmAction.getAlarmActionId().getAction_id());
        } else if (alarmAction.getAlarmActionId().getAlarm_state().name().equals(AlarmState.ALARM.name())) {
          alarmActionIds.add(alarmAction.getAlarmActionId().getAction_id());
        }
      }

      if (alarmDefinitionDb.isActions_enabled() == 0) {
        isEnabled = false;
      }

      List<String> matchBy = splitStringIntoList(alarmDefinitionDb.getMatch_by());

      return new AlarmDefinition(alarmDefinitionDb.getId(), alarmDefinitionDb.getName(), alarmDefinitionDb.getDescription(), alarmDefinitionDb
          .getSeverity().name(), alarmDefinitionDb.getExpression(), matchBy, isEnabled, alarmActionIds, okActionIds, undeterminedActionIds);

    } catch (RuntimeException e) {
      throw new EntityNotFoundException("No alarm definition exists for %s", alarmDefId);
    } finally {
      if (session != null) {
        session.close();
      }
    }
  }

  @Override
  public Map<String, MetricDefinition> findSubAlarmMetricDefinitions(String alarmDefId) {
    Session session = null;
    Map<String, MetricDefinition> subAlarmMetricDefs = new HashMap<>();
    try {

      session = sessionFactory.openSession();

      Query querySybAlarmDef = session.createQuery(QUERY_FIND_SUBALARMDEF_BY_ID).setString("id", alarmDefId);

      List<SubAlarmDefinitionDb> subAlarmDefList = querySybAlarmDef.list();

      Query querySybAlarmDefDimension = session.createQuery(QUERY_INNER_JOIN_SUB_ALARM_DEF_WITH_DIMENSION).setString("id", alarmDefId);

      List<SubAlarmDefinitionDimensionDb> subAlarmDefDimensionList = querySybAlarmDefDimension.list();

      Map<String, Map<String, String>> subAlarmDefDimensionMapExpression = mapAlarmDefDimensionExpression(subAlarmDefDimensionList);

      for (SubAlarmDefinitionDb subAlarmDef : subAlarmDefList) {
        String id = subAlarmDef.getId();
        String metricName = subAlarmDef.getMetric_name();
        Map<String, String> dimensions = Collections.emptyMap();
        if (subAlarmDefDimensionMapExpression.containsKey(id)) {
          dimensions = subAlarmDefDimensionMapExpression.get(id);
        }
        subAlarmMetricDefs.put(id, new MetricDefinition(metricName, dimensions));
      }
      return subAlarmMetricDefs;

    } finally {
      if (session != null) {
        session.close();
      }
    }
  }

  @Override
  public Map<String, AlarmSubExpression> findSubExpressions(String alarmDefId) {
    Session session = null;
    Map<String, AlarmSubExpression> subExpressions = new HashMap<>();
    try {

      session = sessionFactory.openSession();

      Query querySybAlarmDef = session.createQuery(QUERY_FIND_SUBALARMDEF_BY_ID).setString("id", alarmDefId);

      List<SubAlarmDefinitionDb> subAlarmDefList = querySybAlarmDef.list();

      Query querySybAlarmDefDimension = session.createQuery(QUERY_INNER_JOIN_SUB_ALARM_DEF_WITH_DIMENSION).setString("id", alarmDefId);

      List<SubAlarmDefinitionDimensionDb> subAlarmDefDimensionList = querySybAlarmDefDimension.list();

      Map<String, Map<String, String>> subAlarmDefDimensionMapExpression = mapAlarmDefDimensionExpression(subAlarmDefDimensionList);

      for (SubAlarmDefinitionDb subAlarmDef : subAlarmDefList) {
        String id = subAlarmDef.getId();
        AggregateFunction function = AggregateFunction.fromJson((String) subAlarmDef.getFunction());
        String metricName = subAlarmDef.getMetric_name();
        AlarmOperator operator = AlarmOperator.fromJson((String) subAlarmDef.getOperator());
        double threshold = subAlarmDef.getThreshold();
        int period = subAlarmDef.getPeriod();
        int periods = subAlarmDef.getPeriods();
        Map<String, String> dimensions = Collections.emptyMap();

        if (subAlarmDefDimensionMapExpression.containsKey(id)) {
          dimensions = subAlarmDefDimensionMapExpression.get(id);
        }

        subExpressions.put(id, new AlarmSubExpression(function, new MetricDefinition(metricName, dimensions), operator, threshold, period, periods));
      }

      return subExpressions;

    } finally {
      if (session != null) {
        session.close();
      }
    }
  }

  @Override
  public void update(String tenantId, String id, boolean patch, String name, String description, String expression, List<String> matchBy,
      String severity, boolean actionsEnabled, Collection<String> oldSubAlarmIds, Map<String, AlarmSubExpression> changedSubAlarms,
      Map<String, AlarmSubExpression> newSubAlarms, List<String> alarmActions, List<String> okActions, List<String> undeterminedActions) {
    Transaction tx = null;
    Session session = null;
    try {
      session = sessionFactory.openSession();
      tx = session.beginTransaction();

      Query qAlarmDefinition =
          session.createQuery("from AlarmDefinitionDb alarm_definition WHERE alarm_definition.tenant_id=:tenantId AND alarm_definition.id= :id")
              .setString("tenantId", tenantId).setString("id", id);
      AlarmDefinitionDb alarmDefinitionDb = (AlarmDefinitionDb) qAlarmDefinition.uniqueResult();

      alarmDefinitionDb.setName(name);
      alarmDefinitionDb.setDescription(description);
      alarmDefinitionDb.setExpression(expression);
      alarmDefinitionDb.setMatch_by(matchBy == null || Iterables.isEmpty(matchBy) ? null : COMMA_JOINER.join(matchBy));
      alarmDefinitionDb.setSeverity(AlarmSeverity.valueOf(severity));
      alarmDefinitionDb.setActions_enabled(actionsEnabled == true ? 1 : 0);

      session.update(alarmDefinitionDb);

      // Delete old sub-alarms
      if (oldSubAlarmIds != null) {
        for (String oldSubAlarmId : oldSubAlarmIds) {
          session.createQuery("delete SubAlarmDefinitionDb where id = :id").setString("id", oldSubAlarmId).executeUpdate();
        }
      }
      // Update changed sub-alarms
      if (changedSubAlarms != null)
        for (Map.Entry<String, AlarmSubExpression> entry : changedSubAlarms.entrySet()) {
          AlarmSubExpression sa = entry.getValue();
          SubAlarmDefinitionDb subAlarmDefinitionDb = (SubAlarmDefinitionDb) session.get(SubAlarmDefinitionDb.class, entry.getKey());
          subAlarmDefinitionDb.setOperator(sa.getOperator().name());
          subAlarmDefinitionDb.setThreshold(sa.getThreshold());
          subAlarmDefinitionDb.setUpdated_at(new DateTime());
          session.update(subAlarmDefinitionDb);
        }

      // Insert new sub-alarms
      createSubExpressions(session, id, newSubAlarms);

      // Delete old actions
      if (patch) {
        deleteActions(session, id, AlarmState.ALARM, alarmActions);
        deleteActions(session, id, AlarmState.OK, okActions);
        deleteActions(session, id, AlarmState.UNDETERMINED, undeterminedActions);
      } else
        session.createQuery("delete AlarmActionDb alarmAction where alarmAction.alarmActionId.alarm_definition_id = :id").setString("id", id)
            .executeUpdate();

      // Insert new actions
      persistActions(session, id, AlarmState.ALARM, alarmActions);
      persistActions(session, id, AlarmState.OK, okActions);
      persistActions(session, id, AlarmState.UNDETERMINED, undeterminedActions);

      tx.commit();
    } catch (RuntimeException e) {
      try {
        tx.rollback();
      } catch (RuntimeException rbe) {
        logger.error("Couldn’t roll back transaction", rbe);
      }
      throw e;
    } finally {
      if (session != null) {
        session.close();
      }
    }
  }

  private List<String> splitStringIntoList(String commaDelimitedString) {
    if (commaDelimitedString == null) {
      return new ArrayList<String>();
    }
    Iterable<String> split = COMMA_SPLITTER.split(commaDelimitedString);
    return Lists.newArrayList(split);
  }

  private void persistActions(Session session, String id, AlarmState alarmState, List<String> actions) {
    if (actions != null) {
      for (String action : actions) {
        session.save(new AlarmActionDb(id, alarmState, action));
      }
    }
  }

  private void createSubExpressions(Session session, String id, Map<String, AlarmSubExpression> alarmSubExpressions) {
    if (alarmSubExpressions != null) {
      for (Map.Entry<String, AlarmSubExpression> subEntry : alarmSubExpressions.entrySet()) {
        String subAlarmId = subEntry.getKey();
        AlarmSubExpression subExpr = subEntry.getValue();
        MetricDefinition metricDef = subExpr.getMetricDefinition();

        // Persist sub-alarm
        SubAlarmDefinitionDb subAlarmDefinitionDb =
            new SubAlarmDefinitionDb(subAlarmId, id, subExpr.getFunction().name(), metricDef.name, subExpr.getOperator().name(),
                subExpr.getThreshold(), subExpr.getPeriod(), subExpr.getPeriods(), new DateTime(), new DateTime());

        session.save(subAlarmDefinitionDb);

        // Persist sub-alarm dimensions
        if (metricDef.dimensions != null && !metricDef.dimensions.isEmpty())
          for (Map.Entry<String, String> dimEntry : metricDef.dimensions.entrySet())
            session.save(new SubAlarmDefinitionDimensionDb(subAlarmId, dimEntry.getKey(), dimEntry.getValue()));

      }
    }
  }

  private void deleteActions(Session session, String id, AlarmState alarmState, List<String> actions) {
    if (actions != null)
      session.createQuery("delete AlarmActionDb where alarmActionId.alarm_definition_id = :id and alarmActionId.alarm_state = :alarm_state")
          .setString("id", id).setString("alarm_state", alarmState.name()).executeUpdate();
  }

  private Map<String, Map<String, String>> mapAlarmDefDimensionExpression(List<SubAlarmDefinitionDimensionDb> subAlarmDefDimensionList) {
    Map<String, Map<String, String>> subAlarmDefDimensionMapExpression = new HashMap<String, Map<String, String>>();

    // Map expressions on sub_alarm_definition_dimension.sub_alarm_definition_id =
    // sub_alarm_definition.id
    for (SubAlarmDefinitionDimensionDb subAlarmDefDimension : subAlarmDefDimensionList) {
      String subAlarmDefId = subAlarmDefDimension.getSubAlarmDefinitionDimensionId().getSub_alarm_definition_id();
      String name = subAlarmDefDimension.getSubAlarmDefinitionDimensionId().getDimension_name();
      String value = subAlarmDefDimension.getValue();

      if (subAlarmDefDimensionMapExpression.containsKey(subAlarmDefId)) {
        subAlarmDefDimensionMapExpression.get(subAlarmDefId).put(name, value);
      } else {
        Map<String, String> expressionMap = new HashMap<String, String>();
        expressionMap.put(name, value);
        subAlarmDefDimensionMapExpression.put(subAlarmDefId, expressionMap);
      }
    }
    return subAlarmDefDimensionMapExpression;
  }

  private List<AlarmDefinition> createAlarmDefinitions(List<Map> rows) {
    final List<AlarmDefinition> result = new ArrayList<AlarmDefinition>();
    Map<String, List<String>> okActionIdsMap = new HashMap<String, List<String>>();
    Map<String, List<String>> alarmActionIdsMap = new HashMap<String, List<String>>();
    Map<String, List<String>> undeterminedActionIdsMap = new HashMap<String, List<String>>();
    Set<String> alarmDefinitionSet = new HashSet<String>();

    for (Map row : rows) {

      String alarmDefId = (String) row.get(ID);
      String singleState = (String) row.get(STATE);
      String notificationId = (String) row.get(NOTIFICATION_ID);

      if (!okActionIdsMap.containsKey(alarmDefId)) {
        okActionIdsMap.put(alarmDefId, new ArrayList<String>());
      }
      if (!alarmActionIdsMap.containsKey(alarmDefId)) {
        alarmActionIdsMap.put(alarmDefId, new ArrayList<String>());
      }
      if (!undeterminedActionIdsMap.containsKey(alarmDefId)) {
        undeterminedActionIdsMap.put(alarmDefId, new ArrayList<String>());
      }

      if (singleState != null && notificationId != null) {
        if (singleState.equals(AlarmState.UNDETERMINED.name())) {
          undeterminedActionIdsMap.get(alarmDefId).add(notificationId);
        }
        if (singleState.equals(AlarmState.OK.name())) {
          okActionIdsMap.get(alarmDefId).add(notificationId);
        }
        if (singleState.equals(AlarmState.ALARM.name())) {
          alarmActionIdsMap.get(alarmDefId).add(notificationId);
        }
      }
    }

    for (Map row : rows) {
      String alarmDefId = (String) row.get(ID);
      if (!alarmDefinitionSet.contains(alarmDefId)) {
        String name = (String) row.get(NAME);
        String description = (String) row.get(DESCRIPTION);
        String severity = (String) row.get(SEVERITY);
        String expression = (String) row.get(EXPRESSION);
        List<String> match = splitStringIntoList((String) row.get(MATCH_BY));
        boolean actionEnabled = ((Integer) row.get(ACTIONS_ENABLED)) == 1 ? true : false;

        result.add(new AlarmDefinition(alarmDefId, name, description, severity, expression, match, actionEnabled, alarmActionIdsMap.get(alarmDefId),
            okActionIdsMap.get(alarmDefId), undeterminedActionIdsMap.get(alarmDefId)));
      }
      alarmDefinitionSet.add(alarmDefId);
    }
    return result;
  }

  private void bindDimensionsToQuery(Query query, Map<String, String> dimensions) {

    if (dimensions != null) {
      int i = 0;
      for (Iterator<Map.Entry<String, String>> it = dimensions.entrySet().iterator(); it.hasNext(); i++) {
        Map.Entry<String, String> entry = it.next();
        query.setString("dname" + i, entry.getKey());
        query.setString("dvalue" + i, entry.getValue());
      }
    }
  }
}
