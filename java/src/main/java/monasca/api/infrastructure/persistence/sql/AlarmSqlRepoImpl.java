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
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

import javax.inject.Inject;
import javax.inject.Named;

import monasca.api.domain.exception.EntityNotFoundException;
import monasca.api.domain.model.alarm.Alarm;
import monasca.api.domain.model.alarm.AlarmRepo;
import monasca.common.hibernate.db.AlarmDb;
import monasca.common.hibernate.db.SubAlarmDb;
import monasca.common.model.alarm.AlarmSeverity;
import monasca.common.model.alarm.AlarmState;
import monasca.common.model.alarm.AlarmSubExpression;
import monasca.common.model.metric.MetricDefinition;

import org.hibernate.Query;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.joda.time.DateTime;
import org.joda.time.DateTimeZone;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Alarmed metric repository implementation.
 */
public class AlarmSqlRepoImpl implements AlarmRepo {

  private static final Logger logger = LoggerFactory.getLogger(AlarmSqlRepoImpl.class);
  private static final String ALARM_SQL =
      "select ad.id as alarm_definition_id, ad.severity, ad.name as alarm_definition_name, "
          + "a.id, a.state, a.updated_at as state_updated_timestamp, a.created_at as created_timestamp,"
          + "md.name as metric_name, mdg.id.name, mdg.id.value, a.lifecycle_state, a.link, a.state_updated_at from AlarmDb as a, "
          + "AlarmDefinitionDb as ad, "
          + "AlarmMetricDb as am, "
          + "MetricDefinitionDimensionsDb as mdd, "
          + "MetricDefinitionDb as md,"
          + "MetricDimensionDb as mdg "
          + "where "
          + "mdg.id.dimension_set_id = mdd.metric_dimension_set_id and "
          + "md.id = mdd.metric_definition_id and ad.id = a.alarm_definition_id and am.alarmMetricId.alarm_id = a.id "
          + "and mdd.id = am.alarmMetricId.metric_definition_dimensions_id "
          + "and ad.tenant_id = :tenantId and ad.deleted_at is null ";
  private final SessionFactory sessionFactory;

  @Inject
  public AlarmSqlRepoImpl(@Named("orm") SessionFactory sessionFactory) {
    this.sessionFactory = sessionFactory;
  }

  @Override
  public void deleteById(String tenantId, String id) {
    Session session = null;
    try {
      session = sessionFactory.openSession();
      session.beginTransaction();

      List resultList =
          session
              .createQuery(
                  "select a from AlarmDb as a, AlarmDefinitionDb as ad where ad.id = a.alarm_definition_id and ad.deleted_at is NULL and a.id = :id and ad.tenant_id = :tenantId")
              .setString("id", id).setString("tenantId", tenantId).list();

      // This will throw an EntityNotFoundException if Alarm doesn't exist or has a different tenant
      // id
      if (resultList == null || resultList.isEmpty()) {
        throw new EntityNotFoundException("No alarm exists for %s", id);
      }

      // delete alarm
      session.createQuery("delete from AlarmDb where id = :id").setString("id", id).executeUpdate();

      session.getTransaction().commit();
    } finally {
      if (session != null) {
        session.close();
      }
    }

  }

  @Override
  public List<Alarm> find(String tenantId, String alarmDefId, String metricName, Map<String, String> metricDimensions, AlarmState state,
      String lifecycleState, String link, DateTime stateUpdatedStart, String offset, int limit, boolean enforceLimit) {
    Session session = null;
    StringBuilder sbJoinDimensions = new StringBuilder();
    List<Alarm> alarms = new LinkedList<>();

    try {
      session = sessionFactory.openSession();
      StringBuilder sbWhere = new StringBuilder();

      sbWhere.append(ALARM_SQL);

      if (alarmDefId != null) {
        sbWhere.append("and ad.id = :alarmDefId ");
      }
      if (state != null) {
        sbWhere.append(" and a.state = :state");
      }
      if (lifecycleState != null) {
        sbWhere.append(" and a.lifecycle_state = :lifecycleState");
      }
      if (link != null) {
        sbWhere.append(" and a.link = :link");
      }
      if (stateUpdatedStart != null) {
        sbWhere.append(" and a.state_updated_at >= :stateUpdatedStart");

      }
      if (offset != null) {
        sbWhere.append(" and a.id > :offset");
      }
      if (metricName != null) {
        sbWhere.append(" and a.id in (select distinct a.id from AlarmDb as a, " + "AlarmMetricDb as am, " + "MetricDefinitionDimensionsDb as mdd, "
            + "MetricDefinitionDb as md");

        if (metricDimensions != null && metricDimensions.size() > 0) {

          int index = 0;
          for (String key : metricDimensions.keySet()) {

            sbWhere.append(" ,MetricDimensionDb mdim").append(index);

            sbJoinDimensions.append(" and mdim").append(index).append(".id.name = ").append("'").append(key).append("'").append(" and ")
                .append("mdim").append(index).append(".id.value = ").append("'").append(metricDimensions.get(key)).append("'")
                .append(" and mdd.metric_dimension_set_id = mdim").append(index).append(".id.dimension_set_id");
            index++;
          }
        }

        sbWhere.append(
            " where md.id = mdd.metric_definition_id and mdd.id = am.alarmMetricId.metric_definition_dimensions_id and "
                + "am.alarmMetricId.alarm_id = a.id and md.name = :metricName ").append(sbJoinDimensions.toString());

        sbWhere.append(")");

      }

      Query qAlarmDefinition = session.createQuery(sbWhere.toString()).setString("tenantId", tenantId);

      if (alarmDefId != null) {
        qAlarmDefinition.setString("alarmDefId", alarmDefId);
      }

      if (offset != null) {
        qAlarmDefinition.setString("offset", offset);
      }

      if (metricName != null) {
        qAlarmDefinition.setString("metricName", metricName);
      }

      if (state != null) {
        qAlarmDefinition.setString("state", state.name());
      }

      if (link != null) {
        qAlarmDefinition.setString("link", link);
      }

      if (lifecycleState != null) {
        qAlarmDefinition.setString("lifecycleState", lifecycleState);
      }

      if (stateUpdatedStart != null) {
        qAlarmDefinition.setDate("stateUpdatedStart", stateUpdatedStart.toDate());
      }

      if (enforceLimit && limit > 0) {
        qAlarmDefinition.setMaxResults(limit + 1);
      }

      List<Object[]> alarmList = (List<Object[]>) qAlarmDefinition.list();
      alarms = createAlarms(alarmList);

    } finally {
      if (session != null) {
        session.close();
      }
    }
    return alarms;
  }

  @Override
  public Alarm findById(String tenantId, String id) {
    Session session = null;
    List<Alarm> alarms = new LinkedList<>();
    try {
      session = sessionFactory.openSession();
      StringBuilder sbWhere = new StringBuilder();
      sbWhere.append(ALARM_SQL).append(" and a.id = :id");
      Query qAlarmDefinition =
          session.createQuery(sbWhere.toString()).setString("tenantId", tenantId)
              .setString("id", id);
      List<Object[]> alarmList = (List<Object[]>) qAlarmDefinition.list();
      if (alarmList.isEmpty()) {
        throw new EntityNotFoundException("No alarm exists for %s", id);
      }

      alarms = createAlarms(alarmList);

    } finally {
      if (session != null) {
        session.close();
      }
    }
    return alarms.get(0);
  }

  @Override
  public Alarm update(String tenantId, String id, AlarmState state, String lifecycleState, String link) {
    Session session = null;
    Alarm originalAlarm = null;
    try {
      session = sessionFactory.openSession();
      session.beginTransaction();
      originalAlarm = findById(tenantId, id);
      AlarmDb result =
          (AlarmDb) session.createQuery("from AlarmDb where id = :id").setString("id", id)
              .uniqueResult();
      if (!originalAlarm.getState().equals(state)) {
        result.setState_updated_at(new DateTime());
        result.setState(state);
      }
      result.setUpdated_at(new DateTime());
      result.setLink(link);
      result.setLifecycle_state(lifecycleState);
      session.update(result);
      session.getTransaction().commit();
    } finally {
      if (session != null) {
        session.close();
      }
    }
    return originalAlarm;
  }

  @Override
  public Map<String, AlarmSubExpression> findAlarmSubExpressions(String alarmId) {
    Session session = null;
    final Map<String, AlarmSubExpression> subAlarms = new HashMap<String, AlarmSubExpression>();
    logger.debug("AlarmSqlRepoImpl[findAlarmSubExpressions] called");
    try {

      session = sessionFactory.openSession();
      final List<SubAlarmDb> result =
          session.createQuery("from SubAlarmDb where alarm_id = :id").setString("id", alarmId)
              .list();

      if (result != null) {
        for (SubAlarmDb row : result) {
          subAlarms.put(row.getId(), AlarmSubExpression.of(row.getExpression()));
        }
      }
    } finally {
      if (session != null) {
        session.close();
      }
    }
    return subAlarms;
  }

  @Override
  public Map<String, Map<String, AlarmSubExpression>> findAlarmSubExpressionsForAlarmDefinition(
      String alarmDefinitionId) {
    Session session = null;
    Map<String, Map<String, AlarmSubExpression>> subAlarms = new HashMap<>();

    try {
      session = sessionFactory.openSession();
      final List<SubAlarmDb> rows =
          session
              .createQuery(
                  "select sa from SubAlarmDb as sa, AlarmDb as a where sa.alarm_id=a.id and a.alarm_definition_id = :id")
              .setString("id", alarmDefinitionId).list();

      for (SubAlarmDb row : rows) {
        final String alarmId = row.getAlarm_id();
        Map<String, AlarmSubExpression> alarmMap = subAlarms.get(alarmId);
        if (alarmMap == null) {
          alarmMap = new HashMap<>();
          subAlarms.put(alarmId, alarmMap);
        }

        final String id = row.getId();
        final String expression = row.getExpression();
        alarmMap.put(id, AlarmSubExpression.of(expression));
      }

    } finally {
      if (session != null) {
        session.close();
      }
    }
    return subAlarms;
  }

  private Map<String, List<MetricDefinition>> createAlarmedMetrics(List<Object[]> alarmList) {

    Map<String, List<MetricDefinition>> resultList = new HashMap<String, List<MetricDefinition>>();
    Map<String, Map<String, Map<String, String>>> metricList =
        new HashMap<String, Map<String, Map<String, String>>>();

    for (Object[] alarmRow : alarmList) {
      String id = (String) alarmRow[3];
      String metric_name = (String) alarmRow[7];
      String dimension_name = (String) alarmRow[8];
      String dimension_value = (String) alarmRow[9];

      if (!metricList.containsKey(id)) {
        metricList.put(id, new TreeMap<String, Map<String, String>>());
      }
      Map<String, Map<String, String>> dimensions = metricList.get(id);
      if (!dimensions.containsKey(metric_name)) {
        dimensions.put(metric_name, new TreeMap<String, String>());
      }
      dimensions.get(metric_name).put(dimension_name, dimension_value);
    }

    for (String keyId : metricList.keySet()) {
      List<MetricDefinition> valueList = new ArrayList<MetricDefinition>();
      Map<String, Map<String, String>> metrics = metricList.get(keyId);
      for (String keyMetricName : metrics.keySet()) {
        MetricDefinition md = new MetricDefinition(keyMetricName, metrics.get(keyMetricName));
        valueList.add(md);
      }
      resultList.put(keyId, valueList);
    }
    return resultList;
  }

  private List<Alarm> createAlarms(List<Object[]> alarmList) {
    List<Alarm> alarms = new LinkedList<Alarm>();
    Alarm alarm = null;
    HashSet<String> existingAlarmId = new HashSet<String>();
    Map<String, List<MetricDefinition>> alarmMetrics = createAlarmedMetrics(alarmList);

    for (Object[] alarmRow : alarmList) {
      String alarm_definition_id = (String) alarmRow[0];
      AlarmSeverity severity = (AlarmSeverity) alarmRow[1];
      String alarm_definition_name = (String) alarmRow[2];
      String id = (String) alarmRow[3];
      AlarmState alarmState = (AlarmState) alarmRow[4];
      DateTime updated_timestamp = new DateTime(((DateTime) alarmRow[5]).getMillis(), DateTimeZone.forID("UTC"));
      DateTime created_timestamp = new DateTime(((DateTime) alarmRow[6]).getMillis(), DateTimeZone.forID("UTC"));
      String lifecycle_state = (String) alarmRow[10];
      String link = (String) alarmRow[11];
      DateTime state_updated_timestamp = new DateTime(((DateTime) alarmRow[12]).getMillis(), DateTimeZone.forID("UTC"));

      if (!existingAlarmId.contains(id)) {
        alarm =
            new Alarm(id, alarm_definition_id, alarm_definition_name, severity.name(), alarmMetrics.get(id), alarmState, lifecycle_state, link,
                state_updated_timestamp, updated_timestamp, created_timestamp);
        alarms.add(alarm);
      }
      existingAlarmId.add(id);
    }
    return alarms;
  }
}
