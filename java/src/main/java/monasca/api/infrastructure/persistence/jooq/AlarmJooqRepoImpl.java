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

import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import javax.inject.Inject;
import javax.inject.Named;
import javax.sql.DataSource;

import monasca.api.domain.exception.EntityNotFoundException;
import monasca.api.domain.model.alarm.Alarm;
import monasca.api.domain.model.alarm.AlarmRepo;
import monasca.api.infrastructure.persistence.DimensionQueries;
import monasca.api.infrastructure.persistence.PersistUtils;
import monasca.common.jooq.Tables;
import monasca.common.model.alarm.AlarmState;
import monasca.common.model.alarm.AlarmSubExpression;
import monasca.common.model.metric.MetricDefinition;

import org.joda.time.DateTime;
import org.joda.time.DateTimeZone;
import org.jooq.Batch;
import org.jooq.BatchBindStep;
import org.jooq.Configuration;
import org.jooq.Converter;
import org.jooq.DSLContext;
import org.jooq.Field;
import org.jooq.Record;
import org.jooq.Record2;
import org.jooq.Record3;
import org.jooq.RecordMapper;
import org.jooq.Result;
import org.jooq.SQLDialect;
import org.jooq.Select;
import org.jooq.SelectConditionStep;
import org.jooq.SelectJoinStep;
import org.jooq.SelectLimitStep;
import org.jooq.SelectOnConditionStep;
import org.jooq.SelectOrderByStep;
import org.jooq.SelectWhereStep;
import org.jooq.Table;
import org.jooq.TransactionalRunnable;
import org.jooq.Update;
import org.jooq.UpdateSetFirstStep;
import org.jooq.UpdateWhereStep;
import org.jooq.conf.MappedSchema;
import org.jooq.conf.RenderMapping;
import org.jooq.conf.Settings;
import org.jooq.impl.DSL;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Alarmed metric repository implementation.
 */
public class AlarmJooqRepoImpl implements AlarmRepo {

  private static final Logger logger = LoggerFactory.getLogger(AlarmJooqRepoImpl.class);

  private final DataSource ds;
  private final SQLDialect dialect;
  private final PersistUtils persistUtils;
  private final DateTimeZoneConverter timeConverter;
  private final Settings settings;

  /**
   * Constructor.
   * @param ds - datasource
   * @param dialect - dialect of database
   * @param persistUtils - helper
   */
  @Inject
  public AlarmJooqRepoImpl(@Named("datasource") DataSource ds,
                           @Named("dialect") SQLDialect dialect,
                           PersistUtils persistUtils) {
    this.dialect = dialect;
    this.ds = ds;
    this.persistUtils = persistUtils;
    this.timeConverter = new DateTimeZoneConverter();
    this.settings = new Settings().withRenderSchema(false);
  }

  private Select  buildJoinClauseFor(Select query, Map<String, String> dimensions) {

    if (dimensions == null) {
      return query;
    }

    Select res = query;

    monasca.common.jooq.tables.MetricDefinitionDimensions mdd =
        Tables.METRIC_DEFINITION_DIMENSIONS.as("mdd");
    for (int i = 0; i < dimensions.size(); i++) {
      monasca.common.jooq.tables.MetricDimension md =
          Tables.METRIC_DIMENSION.as(String.format("md%1$d", i));

      res = ((SelectOnConditionStep)res).join(md)
        .on(md.NAME.equal(DSL.param(String.format("dname%1$d", i), String.class)))
        .and(md.VALUE.equal(DSL.param(String.format("dvalue%1$d", i), String.class)))
        .and(mdd.METRIC_DIMENSION_SET_ID.equal(md.DIMENSION_SET_ID));
    }

    return res;
  }

  @Override
  public void deleteById(String tenantId, String id) {

    DSLContext create = DSL.using(this.ds, this.dialect, this.settings);

    monasca.common.jooq.tables.Alarm at = Tables.ALARM.as("a");

    // This will throw an EntityNotFoundException if Alarm doesn't exist
    // or has a different tenant id
    findAlarm(tenantId, id, create);

    create.delete(at)
      .where(at.ID.equal((Field<String>)null))
      .bind(1, id)
      .execute();

  }

  @Override
  public List<Alarm> find(String tenantId, String alarmDefId, String metricName,
                          Map<String, String> metricDimensions, AlarmState state,
                          String lifecycleState, String link,
                          DateTime stateUpdatedStart, String offset,
                          int limit, boolean enforceLimit) {

    DSLContext create = DSL.using(this.ds, this.dialect, this.settings);

    monasca.common.jooq.tables.AlarmDefinition ad = Tables.ALARM_DEFINITION.as("ad");
    monasca.common.jooq.tables.Alarm at = Tables.ALARM.as("a");
    monasca.common.jooq.tables.AlarmMetric am = Tables.ALARM_METRIC.as("am");

    Select alarmIdList = create.select(at.ID)
        .from(at, ad)
        .where(ad.ID.equal(at.ALARM_DEFINITION_ID))
        .and(ad.DELETED_AT.isNull())
        .and(ad.TENANT_ID.equal(DSL.param("tenantId", String.class)));


    if (alarmDefId != null) {
      alarmIdList = ((SelectConditionStep)alarmIdList)
        .and(ad.ID.equal(DSL.param("alarmDefId", String.class)));
    }


    monasca.common.jooq.tables.MetricDefinitionDimensions mdd =
        Tables.METRIC_DEFINITION_DIMENSIONS.as("mdd");

    if (metricName != null || metricDimensions != null) {
      Select nestedQuery = create.selectDistinct(at.ID)
          .from(at)
          .join(am).on(am.ALARM_ID.equal(at.ID))
          .join(mdd).on(mdd.ID.equal(am.METRIC_DEFINITION_DIMENSIONS_ID));

      if (metricName != null) {
        monasca.common.jooq.tables.MetricDefinition mdf = Tables.METRIC_DEFINITION.as("mdf");

        Table metricNameTable = create.selectDistinct(mdf.ID)
            .from(mdf)
            .where(mdf.NAME.equal(DSL.param("metricName", String.class)))
            .asTable("md");

        nestedQuery = ((SelectJoinStep)nestedQuery)
          .join(metricNameTable).on(metricNameTable.field("id").equal(mdd.METRIC_DEFINITION_ID));

      }

      nestedQuery = buildJoinClauseFor(nestedQuery, metricDimensions);
      alarmIdList = ((SelectConditionStep)alarmIdList).and(at.ID.in(nestedQuery));
    }

    if (state != null) {
      alarmIdList = ((SelectConditionStep)alarmIdList)
        .and(at.STATE.equal(DSL.param("state", String.class)));
    }

    if (lifecycleState != null) {
      alarmIdList = ((SelectConditionStep)alarmIdList)
        .and(at.LIFECYCLE_STATE.equal(DSL.param("lifecycleState", String.class)));
    }

    if (link != null) {
      alarmIdList = ((SelectConditionStep)alarmIdList)
        .and(at.LINK.equal(DSL.param("link", String.class)));
    }

    if (stateUpdatedStart != null) {
      alarmIdList = ((SelectConditionStep)alarmIdList)
        .and(at.STATE_UPDATED_AT.greaterOrEqual(DSL.param("stateUpdatedStart", Timestamp.class)));
    }

    if (offset != null) {
      alarmIdList = ((SelectConditionStep)alarmIdList)
      .and(at.ID.greaterThan(DSL.param("offset", String.class)));
    }

    alarmIdList = ((SelectOrderByStep)alarmIdList)
      .orderBy(at.ID.asc());

    if (enforceLimit && limit > 0) {
      alarmIdList = ((SelectLimitStep)alarmIdList)
        .limit(DSL.param("limit", Integer.class));
    }

    monasca.common.jooq.tables.MetricDefinition md =
        Tables.METRIC_DEFINITION.as("md");
    monasca.common.jooq.tables.MetricDimension mg = Tables.METRIC_DIMENSION.as("mg");

    Table mdg = create.select(mg.DIMENSION_SET_ID,
                              DSL.groupConcat(DSL.concat(mg.NAME,
                                                         DSL.val("="),
                                                         mg.VALUE),
                                              ",").as("dimensions"))
        .from(mg)
        .groupBy(mg.DIMENSION_SET_ID).asTable("mdg");

    Table alarmIdListTable = alarmIdList.asTable("alarmIdList");

    Select qq = create.select(ad.ID.as("alarm_definition_id"),
                              ad.SEVERITY,
                              ad.NAME.as("alarm_definition_name"),
                              at.ID,
                              at.STATE,
                              at.LIFECYCLE_STATE,
                              at.LINK,
                              at.STATE_UPDATED_AT.as("state_updated_timestamp"),
                              at.UPDATED_AT.as("updated_timestamp"),
                              at.CREATED_AT.as("created_timestamp"),
                              md.NAME.as("metric_name"),
                             mdg.field("dimensions").as("metric_dimensions")
                             )
        .from(at)
        .join(alarmIdListTable).on(alarmIdListTable.field("id").equal(at.ID))
        .join(ad).on(ad.ID.equal(at.ALARM_DEFINITION_ID))
        .join(am).on(am.ALARM_ID.equal(at.ID))
        .join(mdd).on(mdd.ID.equal(am.METRIC_DEFINITION_DIMENSIONS_ID))
        .join(md).on(md.ID.equal(mdd.METRIC_DEFINITION_ID))
        .leftOuterJoin(mdg).on(mdg.field("dimension_set_id").equal(mdd.METRIC_DIMENSION_SET_ID))
        .orderBy(at.ID.asc());

    qq.bind("tenantId", tenantId);

    if (alarmDefId != null) {
      qq.bind("alarmDefId", alarmDefId);
    }

    if (metricName != null) {
      qq.bind("metricName", metricName);
    }

    if (state != null) {
      qq.bind("state", state.name());
    }

    if (lifecycleState != null) {
      qq.bind("lifecycleState", lifecycleState);
    }

    if (link != null) {
      qq.bind("link", link);
    }

    if (stateUpdatedStart != null) {
      qq.bind("stateUpdatedStart", timeConverter.to(stateUpdatedStart));
    }

    if (offset != null) {
      qq.bind("offset", offset);
    }

    if (enforceLimit && limit > 0) {
      qq.bind("limit", limit + 1);
    }

    if (metricDimensions != null) {
      int ind = 0;
      for (Iterator<Map.Entry<String, String>> it =
             metricDimensions.entrySet().iterator();
           it.hasNext();
           ind++) {
        Map.Entry<String, String> entry = it.next();
        qq.bind("dname" + ind, entry.getKey());
        qq.bind("dvalue" + ind, entry.getValue());
      }
    }

    Result<Record> rows = qq.fetch();

    final List<Alarm> alarms = createAlarms(tenantId, rows);

    return alarms;
  }

  @Override
  public Alarm findById(String tenantId, String alarmId) {
    DSLContext create = DSL.using(this.ds, this.dialect, this.settings);

    return findAlarm(tenantId, alarmId, create);
  }

  private Alarm findAlarm(String tenantId, String alarmId, DSLContext create) {

    monasca.common.jooq.tables.AlarmDefinition ad = Tables.ALARM_DEFINITION.as("ad");
    monasca.common.jooq.tables.Alarm at = Tables.ALARM.as("a");
    monasca.common.jooq.tables.AlarmMetric am = Tables.ALARM_METRIC.as("am");
    monasca.common.jooq.tables.MetricDimension mg = Tables.METRIC_DIMENSION.as("mg");
    monasca.common.jooq.tables.MetricDefinitionDimensions mdd =
        Tables.METRIC_DEFINITION_DIMENSIONS.as("mdd");
    monasca.common.jooq.tables.MetricDefinition md = Tables.METRIC_DEFINITION.as("md");

    Table mdg = create.select(mg.DIMENSION_SET_ID,
                              DSL.groupConcat(DSL.concat(mg.NAME,
                                                         DSL.val("="),
                                                         mg.VALUE),
                                              ",").as("dimensions"))
        .from(mg)
        .groupBy(mg.DIMENSION_SET_ID).asTable("mdg");


    Result<Record> rows = create.select(ad.ID.as("alarm_definition_id"),
                                        ad.SEVERITY,
                                        ad.NAME.as("alarm_definition_name"),
                                        at.ID,
                                        at.STATE,
                                        at.LIFECYCLE_STATE,
                                        at.LINK,
                                        at.STATE_UPDATED_AT.as("state_updated_timestamp"),
                                        at.UPDATED_AT.as("updated_timestamp"),
                                        at.CREATED_AT.as("created_timestamp"),
                                        md.NAME.as("metric_name"),
                                        mdg.field("dimensions").as("metric_dimensions")
                                        )
        .from(at)
        .join(ad).on(ad.ID.equal(at.ALARM_DEFINITION_ID))
        .join(am).on(am.ALARM_ID.equal(at.ID))
        .join(mdd).on(mdd.ID.equal(am.METRIC_DEFINITION_DIMENSIONS_ID))
        .join(md).on(md.ID.equal(mdd.METRIC_DEFINITION_ID))
        .leftOuterJoin(mdg).on(mdg.field("dimension_set_id").equal(mdd.METRIC_DIMENSION_SET_ID))
        .where(ad.TENANT_ID.equal(DSL.param("tenantId", String.class)))
        .and(ad.DELETED_AT.isNull())
        .and(at.ID.equal(DSL.param("id", String.class)))
        .orderBy(at.ID.asc())
        .bind("id", alarmId)
        .bind("tenantId", tenantId)
        .fetch();

    if (rows.isEmpty()) {
      throw new EntityNotFoundException("No alarm exists for %s", alarmId);
    }

    return createAlarms(tenantId, rows).get(0);
  }

  private List<Alarm> createAlarms(String tenantId, Result<Record> rows) {
    Alarm alarm = null;
    String previousAlarmId = null;
    final List<Alarm> alarms = new LinkedList<>();
    List<MetricDefinition> alarmedMetrics = null;
    for (Record row : rows) {
      final String alarmId = (String) row.getValue("id");
      if (!alarmId.equals(previousAlarmId)) {
        alarmedMetrics = new ArrayList<>();
        alarm =
          new Alarm(alarmId,
                    (String)row.getValue("alarm_definition_id"),
                    (String)row.getValue("alarm_definition_name"),
                    (String)row.getValue("severity"),
                    alarmedMetrics,
                    AlarmState.valueOf((String)row.getValue("state")),
                    (String)row.getValue("lifecycle_state"),
                    (String)row.getValue("link"),
                    row.getValue("state_updated_timestamp", timeConverter),
                    row.getValue("updated_timestamp", timeConverter),
                    row.getValue("created_timestamp", timeConverter));
        alarms.add(alarm);
      }
      previousAlarmId = alarmId;
      final Map<String, String> dimensionMap = new HashMap<>();

      // Not all Metrics have dimensions (at least theoretically)
      if (row.field("metric_dimensions") != null) {
        final String dimensions = (String)row.getValue("metric_dimensions");
        if (dimensions != null && !dimensions.isEmpty()) {
          for (String dimension : dimensions.split(",")) {
            final String[] parsed_dimension = dimension.split("=");
            if (parsed_dimension.length == 2) {
              dimensionMap.put(parsed_dimension[0], parsed_dimension[1]);
            } else {
              logger.error("Failed to parse dimension. Dimension is malformed: {}", dimension);
            }
          }
        }
      }

      alarmedMetrics.add(new MetricDefinition((String)row.getValue("metric_name"), dimensionMap));
    }
    return alarms;
  }

  @Override
  public Alarm update(final String tenantId, final String id, final AlarmState state,
                      final String lifecycleState, final String link) {

    DSLContext context = DSL.using(this.ds, this.dialect, this.settings);

    final Alarm[] res = new Alarm[1];

    context.transaction(new TransactionalRunnable() {
        @Override
        public void run(Configuration configuration) throws Exception {
          DSLContext create = DSL.using(configuration);
          monasca.common.jooq.tables.Alarm at = Tables.ALARM.as("a");

          final Alarm originalAlarm = findAlarm(tenantId, id, create);

          Update qq = create.update(at)
              .set(at.LIFECYCLE_STATE, (Field<String>)null)
              .set(at.LINK, (Field<String>)null)
              .set(at.UPDATED_AT, DSL.currentTimestamp());

          List bindValues = new ArrayList();
          bindValues.add(lifecycleState);
          bindValues.add(link);


          if (!originalAlarm.getState().equals(state)) {
            qq = ((UpdateSetFirstStep)qq)
              .set(at.STATE, (Field<String>)null)
              .set(at.STATE_UPDATED_AT, DSL.currentTimestamp());
            bindValues.add(state.name());
          }

          qq = ((UpdateWhereStep)qq)
            .where(at.ID.equal((Field<String>)null));

          Batch batch = create.batch(qq);

          bindValues.add(id);

          ((BatchBindStep)batch).bind(bindValues.toArray());
          batch.execute();

          res[0] = originalAlarm;
        }
      });
    return res[0];
  }

  public static class SubAlarm {

    private String id;
    private String expression;

    public SubAlarm() {
    }

    public SubAlarm(String id, String expression) {
      this.id = id;
      this.expression = expression;
    }

    public String getId() {
      return id;
    }

    public void setId(String id) {
      this.id = id;
    }

    public String getExpression() {
      return expression;
    }

    public void setExpression(String expression) {
      this.expression = expression;
    }
  }

  @Override
  public Map<String, AlarmSubExpression> findAlarmSubExpressions(String alarmId) {

    DSLContext context = DSL.using(this.ds, this.dialect, this.settings);

    monasca.common.jooq.tables.SubAlarm sa = Tables.SUB_ALARM.as("sa");

    Result<Record2<String, String>> result = context.select(sa.ID, sa.EXPRESSION)
        .from(sa)
        .where(sa.ALARM_ID.equal(DSL.param("alarmId", String.class)))
        .bind("alarmId", alarmId)
        .fetch();

    final Map<String, AlarmSubExpression> subAlarms = new HashMap<>(result.size());

    for (Record2 row : result) {
      subAlarms.put((String)row.getValue("id"),
                    AlarmSubExpression.of((String)row.getValue("expression")));
    }

    return subAlarms;
  }

  @Override
  public Map<String, Map<String, AlarmSubExpression>>
      findAlarmSubExpressionsForAlarmDefinition(String alarmDefinitionId) {

    DSLContext context = DSL.using(this.ds, this.dialect, this.settings);

    monasca.common.jooq.tables.SubAlarm sa = Tables.SUB_ALARM.as("sa");
    monasca.common.jooq.tables.Alarm at = Tables.ALARM.as("a");

    Result<Record3<String, String, String>> rows = context.select(sa.ID, sa.EXPRESSION, sa.ALARM_ID)
        .from(sa, at)
        .where(sa.ALARM_ID.equal(at.ID))
        .and(at.ALARM_DEFINITION_ID.equal(DSL.param("alarmDefinitionId", String.class)))
        .bind("alarmDefinitionId", alarmDefinitionId)
        .fetch();

    Map<String, Map<String, AlarmSubExpression>> subAlarms = new HashMap<>();
    for (Record3 row : rows) {
      final String alarmId = (String) row.getValue("alarm_id");
      Map<String, AlarmSubExpression> alarmMap = subAlarms.get(alarmId);
      if (alarmMap == null) {
        alarmMap = new HashMap<>();
        subAlarms.put(alarmId, alarmMap);
      }

      final String id = (String) row.getValue("id");
      final String expression = (String) row.getValue("expression");
      alarmMap.put(id, AlarmSubExpression.of(expression));
    }

    return subAlarms;
  }


  static class DateTimeZoneConverter implements Converter<Timestamp, DateTime> {

    @Override
    public DateTime from(Timestamp databaseObject) {

      return new DateTime(databaseObject,
                          DateTimeZone.forID("UTC"));
    }

    @Override
    public Timestamp to(DateTime userObject) {
      return new Timestamp(userObject.getMillis());
    }

    @Override
    public Class<Timestamp> fromType() {
      return Timestamp.class;
    }

    @Override
    public Class<DateTime> toType() {
      return DateTime.class;
    }
  }
}
