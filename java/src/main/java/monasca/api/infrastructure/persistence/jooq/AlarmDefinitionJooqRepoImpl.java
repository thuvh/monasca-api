/*
 * Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
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

package monasca.api.infrastructure.persistence.jooq;

import static monasca.common.jooq.Tables.ALARM;
import static monasca.common.jooq.Tables.ALARM_ACTION;
import static monasca.common.jooq.Tables.SUB_ALARM_DEFINITION;
import static monasca.common.jooq.Tables.SUB_ALARM_DEFINITION_DIMENSION;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import javax.inject.Inject;
import javax.inject.Named;
import javax.sql.DataSource;

import com.google.common.base.Joiner;
import com.google.common.base.Splitter;
import com.google.common.collect.Iterables;
import com.google.common.collect.Lists;

import monasca.api.domain.exception.EntityNotFoundException;
import monasca.api.domain.model.alarmdefinition.AlarmDefinition;
import monasca.api.domain.model.alarmdefinition.AlarmDefinitionRepo;
import monasca.api.infrastructure.persistence.DimensionQueries;
import monasca.api.infrastructure.persistence.PersistUtils;
import monasca.api.infrastructure.persistence.SubAlarmDefinitionQueries;

import monasca.common.jooq.Tables;
import monasca.common.jooq.tables.Alarm;
import monasca.common.jooq.tables.AlarmAction;
import monasca.common.jooq.tables.SubAlarmDefinition;
import monasca.common.jooq.tables.SubAlarmDefinitionDimension;

import monasca.common.model.alarm.AggregateFunction;
import monasca.common.model.alarm.AlarmOperator;
import monasca.common.model.alarm.AlarmState;
import monasca.common.model.alarm.AlarmSubExpression;
import monasca.common.model.metric.MetricDefinition;

import org.jooq.BatchBindStep;
import org.jooq.Configuration;
import org.jooq.DSLContext;
import org.jooq.Delete;
import org.jooq.Field;
import org.jooq.Record;
import org.jooq.RecordMapper;
import org.jooq.Result;
import org.jooq.SQLDialect;
import org.jooq.Select;
import org.jooq.SelectConditionStep;
import org.jooq.SelectLimitStep;
import org.jooq.SelectOnConditionStep;
import org.jooq.SelectWhereStep;
import org.jooq.Table;
import org.jooq.TransactionalRunnable;
import org.jooq.conf.MappedSchema;
import org.jooq.conf.RenderMapping;
import org.jooq.conf.Settings;
import org.jooq.impl.DSL;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;



/**
 * Alarm repository implementation.
 */
public class AlarmDefinitionJooqRepoImpl implements AlarmDefinitionRepo {
  private static final Logger LOG = LoggerFactory.getLogger(AlarmDefinitionJooqRepoImpl.class);
  private static final Joiner COMMA_JOINER = Joiner.on(',');

  private final DataSource ds;
  private final SQLDialect dialect;
  private final PersistUtils persistUtils;
  private final Settings settings;

  /**
   * Creates a new <code>AlarmDefinitionJooqRepoImpl</code> instance.
   *
   * @param ds a <code>DataSource</code> value
   * @param dialect a <code>SQLDialect</code> value
   * @param persistUtils a <code>PersistUtils</code> value
   */
  @Inject
  public AlarmDefinitionJooqRepoImpl(@Named("datasource") DataSource ds,
                                     @Named("dialect") SQLDialect dialect,
                                     PersistUtils persistUtils) {
    this.dialect = dialect;
    this.ds = ds;
    this.persistUtils = persistUtils;
    this.settings = new Settings().withRenderSchema(false);
  }

  @Override
  public AlarmDefinition create(final String tenantId,
                                final String id,
                                final String name,
                                final String description,
                                final String severity,
                                final String expression,
                                final Map<String,
                                AlarmSubExpression> subExpressions,
                                final List<String> matchBy,
                                final List<String> alarmActions,
                                final List<String> okActions,
                                final List<String> undeterminedActions) {

    LOG.debug("create");

    final AlarmDefinition[] res = new AlarmDefinition[1];
    DSLContext context = DSL.using(this.ds, this.dialect, this.settings);
    context.transaction(new TransactionalRunnable() {
        @Override
        public void run(Configuration configuration) throws Exception {
          DSLContext create = DSL.using(configuration);
          monasca.common.jooq.tables.AlarmDefinition ad = Tables.ALARM_DEFINITION;
          create.batch(create.insertInto(ad, ad.ID,
                                         ad.TENANT_ID,
                                         ad.NAME,
                                         ad.DESCRIPTION,
                                         ad.SEVERITY,
                                         ad.EXPRESSION,
                                         ad.MATCH_BY,
                                         ad.ACTIONS_ENABLED,
                                         ad.CREATED_AT,
                                         ad.UPDATED_AT,
                                         ad.DELETED_AT)
                       .values(null, null, null, null,
                               null, null, null, null,
                               DSL.currentTimestamp(),
                               DSL.currentTimestamp(),
                               (Field<Timestamp>) null)
                       ).bind(id,
                              tenantId,
                              name,
                              description,
                              severity,
                              expression,
                              matchBy == null || Iterables.isEmpty(matchBy)
                              ? null : COMMA_JOINER.join(matchBy),
                              true,
                              null).execute();
          createSubExpressions(create, id, subExpressions);

          // Persist actions
          persistActions(create, id, AlarmState.ALARM, alarmActions);
          persistActions(create, id, AlarmState.OK, okActions);
          persistActions(create, id, AlarmState.UNDETERMINED, undeterminedActions);
          res[0] = new AlarmDefinition(id,
                                       name,
                                       description,
                                       severity,
                                       expression,
                                       matchBy,
                                       true,
                                       alarmActions,
                                       okActions == null
                                       ? Collections.<String>emptyList()
                                       : okActions,
                                       undeterminedActions == null
                                       ? Collections.<String>emptyList()
                                       : undeterminedActions);
        }
      });

    return res[0];
  }

  @Override
  public void deleteById(final String tenantId, final String alarmDefId) {
    LOG.debug("deleteById");

    DSLContext context = DSL.using(this.ds, this.dialect, this.settings);

    monasca.common.jooq.tables.AlarmDefinition ad = Tables.ALARM_DEFINITION.as("ad");
    int updatedRowCount = context.update(ad)
        .set(ad.DELETED_AT, DSL.currentTimestamp())
        .where(ad.TENANT_ID.equal((Field<String>)null))
        .and(ad.ID.equal((Field<String>)null))
        .and(ad.DELETED_AT.isNull())
        .bind(1, tenantId)
        .bind(2, alarmDefId)
        .execute();

    if (updatedRowCount == 0) {
      throw new EntityNotFoundException("No alarm definition exists for %s", alarmDefId);
    }

    // Cascade soft delete to alarms
    monasca.common.jooq.tables.Alarm at = Tables.ALARM;
    context.delete(at)
      .where(at.ALARM_DEFINITION_ID.equal((Field<String>)null))
      .bind(1, alarmDefId)
      .execute();

  }

  @Override
  public String exists(final String tenantId, final String name) {
    LOG.debug("exists");

    DSLContext create = DSL.using(this.ds, this.dialect, this.settings);

    String id = null;

    monasca.common.jooq.tables.AlarmDefinition ad = Tables.ALARM_DEFINITION.as("ad");
    Record res = create.select(ad.ID)
        .from(ad)
        .where(ad.TENANT_ID.equal((Field<String>)null))
        .and(ad.NAME.equal((Field<String>)null))
        .and(ad.DELETED_AT.isNull())
        .bind(1, tenantId)
        .bind(2, name)
        .fetchAny();
    if (res != null) {
      id = (String)(res.getValue("id"));
    }

    return id;
  }

  @SuppressWarnings("unchecked")
  @Override
  public List<AlarmDefinition> find(String tenantId, String name,
                                    Map<String, String> dimensions, String offset, int limit) {

    LOG.debug("find");

    DSLContext create = DSL.using(this.ds, this.dialect, this.settings);

    monasca.common.jooq.tables.AlarmDefinition ad = Tables.ALARM_DEFINITION.as("ad");
    SubAlarmDefinition sad = SUB_ALARM_DEFINITION.as("sad");
    SubAlarmDefinitionDimension dim = SUB_ALARM_DEFINITION_DIMENSION.as("dim");

    Select nestedQuery =
        create.selectDistinct(ad.ID,
                              ad.TENANT_ID,
                              ad.NAME,
                              ad.DESCRIPTION,
                              ad.EXPRESSION,
                              ad.SEVERITY,
                              ad.MATCH_BY,
                              ad.ACTIONS_ENABLED,
                              ad.CREATED_AT,
                              ad.UPDATED_AT,
                              ad.DELETED_AT)
        .from(ad)
        .leftOuterJoin(sad)
        .on(ad.ID.equal(sad.ALARM_DEFINITION_ID))
        .leftOuterJoin(dim)
        .on(sad.ID.equal(dim.SUB_ALARM_DEFINITION_ID));

    if (dimensions != null) {
      for (int i = 0; i < dimensions.size(); i++) {
        SubAlarmDefinitionDimension dt =
            SUB_ALARM_DEFINITION_DIMENSION.as(String.format("d%1$d", i));
        nestedQuery = ((SelectOnConditionStep)nestedQuery).join(dt)
            .on(dt.DIMENSION_NAME.equal(DSL.param(String.format("dname%1$d", i), String.class)))
            .and(dt.VALUE.equal(DSL.param(String.format("dvalue%1$d", i), String.class)))
            .and(dim.SUB_ALARM_DEFINITION_ID.equal(dt.SUB_ALARM_DEFINITION_ID));
      }
    }

    nestedQuery = ((SelectWhereStep)nestedQuery)
      .where(ad.TENANT_ID.equal(DSL.param("tenantId", String.class)))
      .and(ad.DELETED_AT.isNull());

    if (name != null) {
      nestedQuery = ((SelectOnConditionStep)nestedQuery)
        .and(ad.NAME.equal(DSL.param("name", String.class)));
    }

    if (offset != null) {
      nestedQuery = ((SelectOnConditionStep)nestedQuery)
        .and(ad.ID.greaterThan(DSL.param("offset", String.class)));
    }

    if (limit > 0) {
      nestedQuery = ((SelectLimitStep)nestedQuery).limit(DSL.param("limit", Integer.class));
    }

    Table tt = nestedQuery.asTable("t");
    AlarmAction aa = ALARM_ACTION.as("aa");

    Select qq = create.select(tt.field("id"),
                              tt.field("tenant_id"),
                              tt.field("name"),
                              tt.field("expression"),
                              tt.field("severity"),
                              tt.field("match_by"),
                              tt.field("actions_enabled"),
                              tt.field("created_at"),
                              tt.field("updated_at"),
                              tt.field("deleted_at"),
                              tt.field("description"),
                              DSL.groupConcat(aa.ALARM_STATE, ",").as("states"),
                              DSL.groupConcat(aa.ACTION_ID, ",").as("notificationIds")
                              )
        .from(tt)
        .leftOuterJoin(aa)
        .on(tt.field("id").equal(aa.ALARM_DEFINITION_ID))
        .groupBy(tt.field("id"),
                 tt.field("tenant_id"),
                 tt.field("name"),
                 tt.field("expression"),
                 tt.field("severity"),
                 tt.field("match_by"),
                 tt.field("actions_enabled"),
                 tt.field("created_at"),
                 tt.field("updated_at"),
                 tt.field("deleted_at"),
                 tt.field("description")
                 )
        .orderBy(tt.field("id").asc(), tt.field("created_at").asc());

    qq.bind("tenantId", tenantId);

    if (name != null) {
      qq.bind("name", name);
    }

    if (offset != null) {
      qq.bind("offset", offset);
    }

    if (limit > 0) {
      qq.bind("limit", limit + 1);
    }

    if (dimensions != null) {
      int ind = 0;
      for (Iterator<Map.Entry<String, String>> it =
               dimensions.entrySet().iterator(); it.hasNext(); ind++) {
        Map.Entry<String, String> entry = it.next();
        qq.bind("dname" + ind, entry.getKey());
        qq.bind("dvalue" + ind, entry.getValue());
      }
    }

    return qq.fetch().map(new AlarmDefinitionMapper());
  }


  @Override
  public AlarmDefinition findById(String tenantId, String alarmDefId) {
    LOG.debug("findById");

    DSLContext create = DSL.using(this.ds, this.dialect, this.settings);

    monasca.common.jooq.tables.AlarmDefinition ad = Tables.ALARM_DEFINITION.as("ad");
    SubAlarmDefinition sad = SUB_ALARM_DEFINITION.as("sad");
    AlarmAction aa = ALARM_ACTION.as("aa");

    Select qq = create.select(ad.ID, ad.TENANT_ID, ad.NAME, ad.DESCRIPTION, ad.EXPRESSION,
                              ad.SEVERITY, ad.MATCH_BY, ad.ACTIONS_ENABLED, ad.CREATED_AT,
                              ad.UPDATED_AT, ad.DELETED_AT,
                              DSL.groupConcat(aa.ACTION_ID, ",").as("notificationIds"),
                              DSL.groupConcat(aa.ALARM_STATE, ",").as("states")
                              )
        .from(ad)
        .leftOuterJoin(aa)
        .on(ad.ID.equal(aa.ALARM_DEFINITION_ID))
        .where(ad.TENANT_ID.equal(DSL.param("tenantId", String.class)))
        .and(ad.ID.equal(DSL.param("alarmDefId", String.class)))
        .and(ad.DELETED_AT.isNull())
        .groupBy(ad.ID);

    qq.bind("tenantId", tenantId);
    qq.bind("alarmDefId", alarmDefId);

    Record alarmDefinitionRec = qq.fetchAny();
    if (alarmDefinitionRec == null) {
      throw new EntityNotFoundException("No alarm definition exists for %s", alarmDefId);
    }
    AlarmDefinition alarmDefinition =
        (AlarmDefinition) alarmDefinitionRec.map(new AlarmDefinitionMapper());
    return alarmDefinition;
  }

  /** Find sub alarm.
   *
   * @param alarmDefId - alarm definition id.
   * @return Result
   */
  public Result<Record> findSubAlarm(String alarmDefId) {

    LOG.debug("findSubAlarm");

    DSLContext context = DSL.using(this.ds, this.dialect, this.settings);
    SubAlarmDefinitionDimension sadd = SUB_ALARM_DEFINITION_DIMENSION.as("sadd");
    Table nested =
        context.select(sadd.SUB_ALARM_DEFINITION_ID,
                       DSL.groupConcat(
                         DSL.concat(sadd.DIMENSION_NAME,
                                    DSL.val("="),
                                    sadd.VALUE),
                         ",").as("dimensions"))
        .from(sadd)
        .groupBy(sadd.SUB_ALARM_DEFINITION_ID)
        .asTable("sad");

    SubAlarmDefinition sa = SUB_ALARM_DEFINITION.as("sa");
    return context
      .select(sa.fields())
      .select(nested.field("dimensions"))
      .from(sa)
      .leftOuterJoin(nested)
      .on(nested.field("sub_alarm_definition_id").equal(sa.ID))
      .where(sa.ALARM_DEFINITION_ID.equal(DSL.param("alarmDefId", String.class)))
      .bind("alarmDefId", alarmDefId).fetch();
  }

  @Override
  public Map<String, MetricDefinition> findSubAlarmMetricDefinitions(String alarmDefId) {
    LOG.debug("findSubAlarmMetricDefinitions");

    Result<Record> rows = findSubAlarm(alarmDefId);
    Map<String, MetricDefinition> subAlarmMetricDefs = new HashMap<>();
    for (Record record : rows) {
      String id = (String) record.getValue("id");
      String metricName = (String) record.getValue("metric_name");
      Map<String, String> dimensions =
          DimensionQueries.dimensionsFor((String) record.getValue("dimensions"));
      subAlarmMetricDefs.put(id, new MetricDefinition(metricName, dimensions));
    }

    return subAlarmMetricDefs;
  }

  @Override
  public Map<String, AlarmSubExpression> findSubExpressions(String alarmDefId) {
    LOG.debug("findSubExpressions");

    Result<Record> rows = findSubAlarm(alarmDefId);
    Map<String, AlarmSubExpression> subExpressions = new HashMap<>();
    for (Record record : rows) {
      String id = (String) record.getValue("id");
      AggregateFunction function = AggregateFunction.fromJson((String) record.getValue("function"));
      String metricName = (String) record.getValue("metric_name");
      AlarmOperator operator = AlarmOperator.fromJson((String) record.getValue("operator"));
      Double threshold = (Double) record.getValue("threshold");
      Integer period = (Integer) record.getValue("period");
      Integer periods = (Integer) record.getValue("periods");
      Map<String, String> dimensions =
          DimensionQueries.dimensionsFor((String) record.getValue("dimensions"));
      subExpressions.put(id, new AlarmSubExpression(function,
                                                    new MetricDefinition(metricName,
                                                                         dimensions),
                                                    operator, threshold, period, periods));
    }

    return subExpressions;
  }

  @Override
  public void update(final String tenantId, final String id, final boolean patch, final String name,
                     final String description, final String expression, final List<String> matchBy,
                     final String severity, final boolean actionsEnabled,
                     final Collection<String> oldSubAlarmIds,
                     final Map<String, AlarmSubExpression> changedSubAlarms,
                     final Map<String, AlarmSubExpression> newSubAlarms,
                     final List<String> alarmActions,
                     final List<String> okActions, final List<String> undeterminedActions) {

    LOG.debug("update");

    DSLContext context = DSL.using(this.ds, this.dialect, this.settings);
    context.transaction(new TransactionalRunnable() {
        @Override
        public void run(Configuration configuration) throws Exception {
          DSLContext create = DSL.using(configuration);
          monasca.common.jooq.tables.AlarmDefinition ad = Tables.ALARM_DEFINITION.as("ad");
          BatchBindStep batch = create.batch(create.update(ad)
                                             .set(ad.NAME, (Field<String>)null)
                                             .set(ad.DESCRIPTION, (Field<String>)null)
                                             .set(ad.EXPRESSION, (Field<String>)null)
                                             .set(ad.MATCH_BY, (Field<String>)null)
                                             .set(ad.SEVERITY, (Field<String>)null)
                                             .set(ad.ACTIONS_ENABLED, (Field<Boolean>)null)
                                             .set(ad.UPDATED_AT, DSL.currentTimestamp())
                                             .where(ad.TENANT_ID.equal((Field<String>)null))
                                             .and(ad.ID.equal((Field<String>)null))
                                             );
          batch.bind(name,
                     description,
                     expression,
                     matchBy == null || Iterables.isEmpty(matchBy) ? null
                     : COMMA_JOINER.join(matchBy), severity, actionsEnabled, tenantId, id);
          batch.execute();

          // Delete old sub-alarms
          if (oldSubAlarmIds != null) {
            monasca.common.jooq.tables.SubAlarmDefinition sad = Tables.SUB_ALARM_DEFINITION;
            List<monasca.common.jooq.tables.records.SubAlarmDefinitionRecord> deleteList =
                 new ArrayList<monasca.common.jooq.tables.records.SubAlarmDefinitionRecord>();
            for (String oldSubAlarmId : oldSubAlarmIds) {
              monasca.common.jooq.tables.records.SubAlarmDefinitionRecord rec =
                  new monasca.common.jooq.tables.records.SubAlarmDefinitionRecord();
              rec.setId(oldSubAlarmId);
              deleteList.add(rec);
            }
            create.batchDelete(deleteList)
              .execute();
          }

          // Update changed sub-alarms
          if (changedSubAlarms != null) {
            monasca.common.jooq.tables.SubAlarmDefinition sad =
                Tables.SUB_ALARM_DEFINITION.as("sad");
            batch = create.batch(create.update(sad)
                                 .set(sad.OPERATOR, (Field<String>)null)
                                 .set(sad.THRESHOLD, (Field<Double>)null)
                                 .set(sad.UPDATED_AT, DSL.currentTimestamp())
                                 .where(sad.ID.equal((Field<String>)null))
                                 );
            for (Map.Entry<String, AlarmSubExpression> entry : changedSubAlarms.entrySet()) {
              AlarmSubExpression sa = entry.getValue();
              batch.bind(sa.getOperator().name(), sa.getThreshold(), entry.getKey());
            }
            batch.execute();
          }
          // Insert new sub-alarms
          createSubExpressions(create, id, newSubAlarms);
          // Delete old actions
          if (patch) {
            deleteActions(create, id, AlarmState.ALARM, alarmActions);
            deleteActions(create, id, AlarmState.OK, okActions);
            deleteActions(create, id, AlarmState.UNDETERMINED, undeterminedActions);
          } else {
            monasca.common.jooq.tables.AlarmAction aa = Tables.ALARM_ACTION;
            create.delete(aa)
              .where(aa.ALARM_DEFINITION_ID.equal((Field<String>)null))
              .bind(1, id)
              .execute();

          }

          // Insert new actions
          persistActions(create, id, AlarmState.ALARM, alarmActions);
          persistActions(create, id, AlarmState.OK, okActions);
          persistActions(create, id, AlarmState.UNDETERMINED, undeterminedActions);
        }
      });
  }

  private void deleteActions(DSLContext create,
                             String id,
                             AlarmState alarmState,
                             List<String> actions) {
    LOG.debug("deleteActions");
    if (actions != null) {
      monasca.common.jooq.tables.AlarmAction aa = Tables.ALARM_ACTION;
      create.delete(aa)
        .where(aa.ALARM_DEFINITION_ID.equal((Field<String>)null))
        .and(aa.ALARM_STATE.equal((Field<String>)null))
        .bind(1, id)
        .bind(2, alarmState.name())
        .execute();
    }
  }

  private void persistActions(DSLContext create,
                              String id,
                              AlarmState alarmState,
                              List<String> actions) {
    LOG.debug("persistActions");
    if (actions != null) {
      AlarmAction aa = ALARM_ACTION;
      BatchBindStep batch = create.batch(create.insertInto(aa)
                                         .values((Integer) null, null, null)
                                         );
      for (String action : actions) {
        batch.bind(id, alarmState.name(), action);
      }
      batch.execute();
    }
  }

  private void createSubExpressions(DSLContext create, String id,
                                    Map<String, AlarmSubExpression> alarmSubExpressions) {
    LOG.debug("createSubExpressions");
    if (alarmSubExpressions != null) {
      SubAlarmDefinition sad = SUB_ALARM_DEFINITION;
      BatchBindStep batch = create.batch(create.insertInto(sad,
                                                           sad.ID,
                                                           sad.ALARM_DEFINITION_ID,
                                                           sad.FUNCTION,
                                                           sad.METRIC_NAME,
                                                           sad.OPERATOR,
                                                           sad.THRESHOLD,
                                                           sad.PERIOD,
                                                           sad.PERIODS,
                                                           sad.CREATED_AT,
                                                           sad.UPDATED_AT)
                                         .values((Field<String>) null,
                                                 null,
                                                 null,
                                                 null,
                                                 null,
                                                 null,
                                                 null,
                                                 null,
                                                 DSL.currentTimestamp(),
                                                 DSL.currentTimestamp())
                                         );
      for (Map.Entry<String, AlarmSubExpression> subEntry : alarmSubExpressions.entrySet()) {
        String subAlarmId = subEntry.getKey();
        AlarmSubExpression subExpr = subEntry.getValue();
        MetricDefinition metricDef = subExpr.getMetricDefinition();

        // Persist sub-alarm
        batch.bind(subAlarmId,
                   id,
                   subExpr.getFunction().name(),
                   metricDef.name,
                   subExpr.getOperator().name(),
                   subExpr.getThreshold(),
                   subExpr.getPeriod(),
                   subExpr.getPeriods());
        batch.execute();

        // Persist sub-alarm dimensions
        if (metricDef.dimensions != null && !metricDef.dimensions.isEmpty()) {
          SubAlarmDefinitionDimension sadd = SUB_ALARM_DEFINITION_DIMENSION;
          batch = create.batch(create.insertInto(sadd)
                               .values((Integer) null, null, null)
                               );
          for (Map.Entry<String, String> dimEntry : metricDef.dimensions.entrySet()) {
            batch.bind(subAlarmId, dimEntry.getKey(), dimEntry.getValue());
          }
          batch.execute();
        }
      }
    }
  }

  private static class AlarmDefinitionMapper implements RecordMapper<Record, AlarmDefinition> {

    private static final Splitter
        COMMA_SPLITTER =
        Splitter.on(',').omitEmptyStrings().trimResults();

    @Override
    public AlarmDefinition map(Record rec) {
      String notificationIds = (String)(rec.getValue("notificationIds"));
      String states = (String)(rec.getValue("states"));
      String matchBy = (String)(rec.getValue("match_by"));
      List<String> notifications = splitStringIntoList(notificationIds);
      List<String> state = splitStringIntoList(states);
      List<String> match = splitStringIntoList(matchBy);

      List<String> okActionIds = new ArrayList<String>();
      List<String> alarmActionIds = new ArrayList<String>();
      List<String> undeterminedActionIds = new ArrayList<String>();

      int stateAndActionIndex = 0;
      for (String singleState : state) {
        if (singleState.equals(AlarmState.UNDETERMINED.name())) {
          undeterminedActionIds.add(notifications.get(stateAndActionIndex));
        }
        if (singleState.equals(AlarmState.OK.name())) {
          okActionIds.add(notifications.get(stateAndActionIndex));
        }
        if (singleState.equals(AlarmState.ALARM.name())) {
          alarmActionIds.add(notifications.get(stateAndActionIndex));
        }
        stateAndActionIndex++;
      }

      return new AlarmDefinition((String)(rec.getValue("id")),
                                 (String)(rec.getValue("name")),
                                 (String)(rec.getValue("description")),
                                 (String)(rec.getValue("severity")),
                                 (String)(rec.getValue("expression")),
                                 match,
                                 (Boolean)(rec.getValue("actions_enabled")),
                                 alarmActionIds,
                                 okActionIds,
                                 undeterminedActionIds);
    }

    private List<String> splitStringIntoList(String commaDelimitedString) {
      if (commaDelimitedString == null) {
        return new ArrayList<String>();
      }
      Iterable<String> split = COMMA_SPLITTER.split(commaDelimitedString);
      return Lists.newArrayList(split);
    }
  }
}
