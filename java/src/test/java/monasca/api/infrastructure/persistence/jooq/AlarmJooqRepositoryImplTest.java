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

import static org.testng.Assert.assertEquals;
import static org.testng.Assert.assertNotEquals;
import static org.testng.Assert.assertTrue;

import java.nio.charset.Charset;
import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import javax.sql.DataSource;

import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableMap.Builder;
import com.google.common.io.Resources;

import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import monasca.api.domain.exception.EntityNotFoundException;
import monasca.api.domain.model.alarm.Alarm;
import monasca.api.domain.model.alarm.AlarmRepo;
import monasca.api.infrastructure.persistence.PersistUtils;
import monasca.common.jooq.Tables;
import monasca.common.model.alarm.AlarmOperator;
import monasca.common.model.alarm.AlarmState;
import monasca.common.model.alarm.AlarmSubExpression;
import monasca.common.model.metric.MetricDefinition;

import org.joda.time.DateTime;
import org.joda.time.DateTimeZone;
import org.joda.time.format.DateTimeFormatter;
import org.joda.time.format.ISODateTimeFormat;

import org.jooq.Configuration;
import org.jooq.DSLContext;
import org.jooq.Field;
import org.jooq.Record;
import org.jooq.RecordMapper;
import org.jooq.SQLDialect;
import org.jooq.Select;
import org.jooq.SelectConditionStep;
import org.jooq.SelectLimitStep;
import org.jooq.SelectOrderByStep;
import org.jooq.TransactionalRunnable;
import org.jooq.conf.MappedSchema;
import org.jooq.conf.RenderMapping;
import org.jooq.conf.Settings;
import org.jooq.impl.DSL;
import org.jooq.tools.jdbc.JDBCUtils;
import org.skife.jdbi.v2.DBI;
import org.skife.jdbi.v2.Handle;
import org.testng.annotations.AfterClass;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;


@Test(groups = "jooq")
public class AlarmJooqRepositoryImplTest {
  private static final String TENANT_ID = "bob";
  private static final String ALARM_ID = "234111";
  private static final DateTimeFormatter ISO_8601_FORMATTER =
      ISODateTimeFormat.dateOptionalTimeParser().withZoneUTC();
  private DBI db;
  private Handle handle;
  private DataSource ds;
  private SQLDialect dialect;

  private AlarmRepo repo;
  private List<String> alarmActions;
  private Alarm compoundAlarm;
  private Alarm alarm1;
  private Alarm alarm2;
  private Alarm alarm3;
  private Settings settings;

  private AlarmJooqRepoImpl.DateTimeZoneConverter timeConverter;

  @BeforeClass
  protected void setupClass() throws Exception {

    HikariConfig config = new HikariConfig();

    //config.setJdbcUrl("jdbc:mysql://localhost:3306/mon");
    //config.setJdbcUrl("jdbc:postgresql://localhost:5432/mon");
    config.setJdbcUrl("jdbc:h2:mem:test_ad;DB_CLOSE_DELAY=-1;MODE=MySQL;DATABASE_TO_UPPER=false");
    config.setDriverClassName("org.h2.Driver");
    //config.setDriverClassName("org.postgresql.Driver");
    //config.setDriverClassName("org.mariadb.jdbc.Driver");
    config.setUsername("tester");
    config.setPassword("testing");
    //config.setUsername("monapi");
    //config.setPassword("password");
    config.setConnectionTestQuery("SELECT 1");
    //config.addDataSourceProperty("cachePrepStmts", "true");
    //config.addDataSourceProperty("prepStmtCacheSize", "250");
    //config.addDataSourceProperty("prepStmtCacheSqlLimit", "2048");

    try {
      ds = new HikariDataSource(config);

      //dialect = JDBCUtils.dialect("jdbc:mysql://localhost:3306/mon");
      dialect = JDBCUtils.dialect("jdbc:h2:mem;MODE=PostgreSQL");
      //dialect = JDBCUtils.dialect("jdbc:postgresql://localhost:5432/mon");

      settings = new Settings().withRenderSchema(false);

      db = new DBI(ds);
      handle = db.open();

      // String ddl = Resources.toString(getClass()
      //                                 .getResource("alarm_mysql.sql"),
      //                                 Charset.defaultCharset());
      // String ddl = Resources.toString(getClass()
      //                                 .getResource("alarm_postgresql.sql"),
      //                                 Charset.defaultCharset());
      String ddl = Resources.toString(getClass()
                                      .getResource("alarm.sql"),
                                      Charset.defaultCharset());

      handle
        .createScript(ddl).execute();

    } catch (Exception e) {
      if (e.getCause() instanceof java.sql.SQLException) {
        java.sql.SQLException cause = (java.sql.SQLException)e.getCause();
        System.out.println(cause.getNextException());
      }
    }
    repo = new AlarmJooqRepoImpl(ds, dialect, new PersistUtils());

    timeConverter = new AlarmJooqRepoImpl.DateTimeZoneConverter();

    alarmActions = new ArrayList<String>();
    alarmActions.add("29387234");
    alarmActions.add("77778687");
  }

  @AfterClass
  protected void afterClass() {
    handle.close();
  }

  @BeforeMethod
  protected void beforeMethod() {

    DSLContext context = DSL.using(this.ds, this.dialect, this.settings);

    final monasca.common.jooq.tables.NotificationMethod nm = Tables.NOTIFICATION_METHOD;
    final monasca.common.jooq.tables.AlarmAction aa = Tables.ALARM_ACTION;
    final monasca.common.jooq.tables.Alarm a = Tables.ALARM;
    final monasca.common.jooq.tables.SubAlarm sa = Tables.SUB_ALARM;
    final monasca.common.jooq.tables.SubAlarmDefinition sad = Tables.SUB_ALARM_DEFINITION;
    final monasca.common.jooq.tables.AlarmDefinition ad = Tables.ALARM_DEFINITION;
    final monasca.common.jooq.tables.AlarmMetric am = Tables.ALARM_METRIC;
    final monasca.common.jooq.tables.MetricDefinition md = Tables.METRIC_DEFINITION;
    final monasca.common.jooq.tables.MetricDefinitionDimensions mdd =
        Tables.METRIC_DEFINITION_DIMENSIONS;
    final monasca.common.jooq.tables.MetricDimension mdi = Tables.METRIC_DIMENSION;

    final DateTime timestamp1 = ISO_8601_FORMATTER
        .parseDateTime("2015-03-14T09:26:53")
        .withZoneRetainFields(DateTimeZone.forID("UTC"));
    final DateTime timestamp2 = ISO_8601_FORMATTER
        .parseDateTime("2015-03-14T09:26:54")
        .withZoneRetainFields(DateTimeZone.forID("UTC"));
    final DateTime timestamp3 = ISO_8601_FORMATTER
        .parseDateTime("2015-03-14T09:26:55")
        .withZoneRetainFields(DateTimeZone.forID("UTC"));
    final DateTime timestamp4 = ISO_8601_FORMATTER
        .parseDateTime("2015-03-15T09:26:53Z");

    context.transaction(new TransactionalRunnable() {
        @Override
        public void run(Configuration configuration) throws Exception {
          DSLContext create = DSL.using(configuration);

          create.delete(nm).execute();
          create.delete(a).execute();
          create.delete(sa).execute();
          create.delete(sad).execute();
          create.delete(aa).execute();
          create.delete(ad).execute();
          create.delete(am).execute();
          create.delete(md).execute();
          create.delete(mdd).execute();
          create.delete(mdi).execute();
          try {
          create.batch(create.insertInto(ad, ad.ID, ad.TENANT_ID, ad.NAME, ad.SEVERITY,
                                         ad.EXPRESSION, ad.MATCH_BY, ad.ACTIONS_ENABLED,
                                         ad.CREATED_AT, ad.UPDATED_AT, ad.DELETED_AT)
                       .values(null, null, null, null,
                               null, null, null,
                               DSL.currentTimestamp(),
                               DSL.currentTimestamp(),
                               (Field<Timestamp>) null
                               )
                       )
            .bind("1", "bob", "90% CPU", "LOW",
                  "avg(cpu.idle_perc{flavor_id=777, image_id=888, device=1}) > 10",
                  "flavor_id,image_id", 1, null
                  )
            .bind("234", "bob", "50% CPU", "LOW",
                  "avg(cpu.sys_mem{service=monitoring}) > 20 and"
                  + " avg(cpu.idle_perc{service=monitoring}) < 10",
                  "hostname,region", 1, null)
            .execute();
          } catch (org.jooq.exception.DataAccessException e) {
            if (e.getCause() instanceof java.sql.SQLException) {
              java.sql.SQLException cause = (java.sql.SQLException)e.getCause();
              System.out.println(cause.getNextException());
            }
          }
          create.batch(create.insertInto(a, a.ID, a.ALARM_DEFINITION_ID, a.STATE, a.LIFECYCLE_STATE,
                                         a.LINK, a.CREATED_AT, a.UPDATED_AT, a.STATE_UPDATED_AT)
                       .values(null, null, null, null,
                               null,
                               (Field<Timestamp>) null,
                               (Field<Timestamp>) null,
                               (Field<Timestamp>) null
                               )
                       )
            .bind("1", "1", "OK", "OPEN",
                  "http://somesite.com/this-alarm-info",
                  timeConverter.to(timestamp1),
                  timeConverter.to(timestamp1),
                  timeConverter.to(timestamp1)
                  )
            .bind("2", "1", "UNDETERMINED", "OPEN",
                  null,
                  timeConverter.to(timestamp2),
                  timeConverter.to(timestamp2),
                  timeConverter.to(timestamp2)
                  )
            .bind("3", "1", "ALARM", null,
                  "http://somesite.com/this-alarm-info",
                  timeConverter.to(timestamp3),
                  timeConverter.to(timestamp3),
                  timeConverter.to(timestamp3)
                  )
            .bind("234111", "234", "UNDETERMINED", null,
                  null,
                  timeConverter.to(timestamp4),
                  timeConverter.to(timestamp4),
                  timeConverter.to(timestamp4)
                  )
            .execute();

          long subAlarmId = 42;
          long alarmId = 1;
          Timestamp nowT = timeConverter.to(new DateTime(DateTimeZone.forID("UTC")));

          create.batch(create.insertInto(sad, sad.ID, sad.ALARM_DEFINITION_ID, sad.FUNCTION,
                                         sad.METRIC_NAME, sad.OPERATOR, sad.THRESHOLD,
                                         sad.PERIOD, sad.PERIODS,
                                         sad.CREATED_AT, sad.UPDATED_AT)
                       .values((String)null, null, null,
                               null, null, null,
                               null, null,
                               null, null
                               )
                       )
            .bind(String.valueOf(subAlarmId + alarmId),
                  "234",
                  String.format("f_%d", subAlarmId + alarmId),
                  String.format("m_%d", (subAlarmId++) + (alarmId++)),
                  AlarmOperator.GT.toString(), 0.0,
                  1, 2,
                  nowT, nowT)
            .bind(String.valueOf(subAlarmId + alarmId),
                  "234",
                  String.format("f_%d", subAlarmId + alarmId),
                  String.format("m_%d", (subAlarmId++) + (alarmId++)),
                  AlarmOperator.GT.toString(), 0.0,
                  1, 2,
                  nowT, nowT)
            .bind(String.valueOf(subAlarmId + alarmId),
                  "234",
                  String.format("f_%d", subAlarmId + alarmId),
                  String.format("m_%d", (subAlarmId++) + (alarmId++)),
                  AlarmOperator.GT.toString(), 0.0,
                  1, 2,
                  nowT, nowT)
            .bind("8484",
                  "234",
                  String.format("f_%d", subAlarmId + alarmId),
                  String.format("m_%d", (subAlarmId++) + (alarmId++)),
                  AlarmOperator.GT.toString(), 0.0,
                  1, 2,
                  nowT, nowT)
            .bind("8686",
                  "234",
                  String.format("f_%d", subAlarmId + alarmId),
                  String.format("m_%d", (subAlarmId++) + (alarmId++)),
                  AlarmOperator.GT.toString(), 0.0,
                  1, 2,
                  nowT, nowT)
            .execute();

          subAlarmId = 42;
          alarmId = 1;

          create.batch(create.insertInto(sa,
                                         sa.SUB_EXPRESSION_ID,
                                         sa.ID,
                                         sa.ALARM_ID,
                                         sa.EXPRESSION,
                                         sa.CREATED_AT,
                                         sa.UPDATED_AT)
                       .values(null, (String)null, null,
                               null,
                               null, null
                               )
                       )
            .bind(String.valueOf(subAlarmId + alarmId), String.valueOf(subAlarmId++), alarmId++,
                  "avg(cpu.idle_perc{flavor_id=777, image_id=888, device=1}) > 10",
                  nowT, nowT)
            .bind(String.valueOf(subAlarmId + alarmId), String.valueOf(subAlarmId++), alarmId++,
                  "avg(cpu.idle_perc{flavor_id=777, image_id=888, device=1}) > 10",
                  nowT, nowT)
            .bind(String.valueOf(subAlarmId + alarmId), String.valueOf(subAlarmId++), alarmId++,
                  "avg(cpu.idle_perc{flavor_id=777, image_id=888, device=1}) > 10",
                  nowT, nowT)
            .execute();

          create.batch(create.insertInto(sa,
                                         sa.SUB_EXPRESSION_ID,
                                         sa.ID,
                                         sa.ALARM_ID,
                                         sa.EXPRESSION,
                                         sa.CREATED_AT,
                                         sa.UPDATED_AT)
                       .values((String)null, null, null, null,
                               null, null
                               )
                       )
            .bind("8686", "4343", "234111", "avg(cpu.sys_mem{service=monitoring}) > 20",
                  nowT, nowT)
            .bind("8484", "4242", "234111", "avg(cpu.idle_perc{service=monitoring}) < 10",
                  nowT, nowT)
            .execute();

          create.batch(create.insertInto(am, am.ALARM_ID, am.METRIC_DEFINITION_DIMENSIONS_ID)
                       .values((String)null, (byte[])null)
                       )
            .bind("1", new byte[]{11})
            .bind("1", new byte[]{22})
            .bind("2", new byte[]{11})
            .bind("3", new byte[]{22})
            .bind("234111", new byte[]{31})
            .bind("234111", new byte[]{32})
            .execute();

          create.batch(create.insertInto(md, md.ID, md.NAME, md.TENANT_ID, md.REGION)
                       .values((byte[])null, (String)null, (String)null, (String)null)
                       )
            .bind(new byte[]{1}, "cpu.idle_perc", "bob", "west")
            .bind(new byte[]{111}, "cpu.sys_mem", "bob", "west")
            .bind(new byte[]{112}, "cpu.idle_perc", "bob", "west")
            .execute();

          create.batch(create.insertInto(mdd,
                                         mdd.ID,
                                         mdd.METRIC_DEFINITION_ID,
                                         mdd.METRIC_DIMENSION_SET_ID)
                       .values((byte[])null, (byte[])null, (byte[])null)
                       )
            .bind(new byte[]{11}, new byte[]{1}, new byte[]{1})
            .bind(new byte[]{22}, new byte[]{1}, new byte[]{2})
            .bind(new byte[]{31}, new byte[]{111}, new byte[]{21})
            .bind(new byte[]{32}, new byte[]{112}, new byte[]{22})
            .execute();

          create.batch(create.insertInto(mdi, mdi.DIMENSION_SET_ID, mdi.NAME, mdi.VALUE)
                       .values((byte[])null, (String)null, (String)null)
                       )
            .bind(new byte[]{1}, "instance_id", "123")
            .bind(new byte[]{1}, "service", "monitoring")
            .bind(new byte[]{2}, "flavor_id", "222")
            .bind(new byte[]{21}, "service", "monitoring")
            .bind(new byte[]{22}, "service", "monitoring")
            .bind(new byte[]{21}, "hostname", "roland")
            .bind(new byte[]{22}, "hostname", "roland")
            .bind(new byte[]{21}, "region", "colorado")
            .bind(new byte[]{22}, "region", "colorado")
            .bind(new byte[]{22}, "extra", "vivi")
            .execute();
        }
      });

    alarm1 =
        new Alarm("1", "1", "90% CPU", "LOW", buildAlarmMetrics(
            buildMetricDefinition("cpu.idle_perc", "instance_id", "123", "service", "monitoring"),
            buildMetricDefinition("cpu.idle_perc", "flavor_id", "222")),
                  AlarmState.OK, "OPEN", "http://somesite.com/this-alarm-info", timestamp1, timestamp1, timestamp1);

    alarm2 =
        new Alarm("2", "1", "90% CPU", "LOW", buildAlarmMetrics(
            buildMetricDefinition("cpu.idle_perc", "instance_id", "123", "service", "monitoring")),
                  AlarmState.UNDETERMINED, "OPEN", null, timestamp2, timestamp2, timestamp2);

    alarm3 =
        new Alarm("3", "1", "90% CPU", "LOW", buildAlarmMetrics(
            buildMetricDefinition("cpu.idle_perc", "flavor_id", "222")),
                  AlarmState.ALARM, null, "http://somesite.com/this-alarm-info", timestamp3, timestamp3, timestamp3);

    compoundAlarm =
        new Alarm("234111", "234", "50% CPU", "LOW", buildAlarmMetrics(
            buildMetricDefinition("cpu.sys_mem", "service", "monitoring", "hostname", "roland",
                                  "region", "colorado"),
            buildMetricDefinition("cpu.idle_perc", "service", "monitoring", "hostname", "roland",
                                  "region", "colorado", "extra", "vivi")),
                  AlarmState.UNDETERMINED, null, null,
                  timestamp4, timestamp4, timestamp4);
  }

  private List<MetricDefinition> buildAlarmMetrics(final MetricDefinition ... metricDefinitions) {
    return Arrays.asList(metricDefinitions);
  }

  private MetricDefinition buildMetricDefinition(final String metricName,
                                                 final String ... dimensions) {
    final Builder<String, String> builder = ImmutableMap.<String, String>builder();
    for (int i = 0; i < dimensions.length;) {
      builder.put(dimensions[i], dimensions[i + 1]);
      i += 2;
    }
    return new MetricDefinition(metricName, builder.build());
  }

  @Test(groups = "jooq")
  public void shouldDelete() {
    repo.deleteById(TENANT_ID, ALARM_ID);

    List<Map<String, Object>> rows =
        handle.createQuery("select * from alarm_definition where id='234'").list();
    assertEquals(rows.size(), 1, "Alarm Definition was deleted as well");
  }

  @Test(groups = "jooq", expectedExceptions = EntityNotFoundException.class)
  public void shouldThowExceptionOnDelete() {
    repo.deleteById(TENANT_ID, "Not an alarm ID");
  }

  @Test(groups = "jooq")
  public void shouldFindAlarmSubExpressions() {
    final Map<String, AlarmSubExpression> subExpressionMap = repo.findAlarmSubExpressions(ALARM_ID);
    assertEquals(subExpressionMap.size(), 2);
    assertEquals(subExpressionMap.get("4343"),
        AlarmSubExpression.of("avg(cpu.sys_mem{service=monitoring}) > 20"));
    assertEquals(subExpressionMap.get("4242"),
        AlarmSubExpression.of("avg(cpu.idle_perc{service=monitoring}) < 10"));
  }

  @Test(groups = "jooq")
  public void shouldAlarmSubExpressionsForAlarmDefinition() {
    final Map<String, Map<String, AlarmSubExpression>> alarmSubExpressionMap =
        repo.findAlarmSubExpressionsForAlarmDefinition(alarm1.getAlarmDefinition().getId());
    assertEquals(alarmSubExpressionMap.size(), 3);
    long subAlarmId = 42;
    for (int alarmId = 1; alarmId <= 3; alarmId++) {
      final Map<String, AlarmSubExpression> subExpressionMap =
          alarmSubExpressionMap.get(String.valueOf(alarmId));
      assertEquals(subExpressionMap.get(String.valueOf(subAlarmId)),
          AlarmSubExpression.of("avg(cpu.idle_perc{flavor_id=777, image_id=888, device=1}) > 10"));
      subAlarmId++;
    }
  }

  private void checkList(List<Alarm> found, Alarm ... expected) {
    assertEquals(found.size(), expected.length);
    for (Alarm alarm : expected) {
      assertTrue(found.contains(alarm));
    }
  }

  @Test(groups = "jooq")
  public void shouldFind() {
    checkList(repo.find("Not a tenant id", null, null, null,
                        null, null, null, null, null, 1, false));

    checkList(repo.find(TENANT_ID, null, null, null,
                        null, null, null, null, null, 1, false),
              alarm1, alarm2, alarm3, compoundAlarm);

    checkList(repo.find(TENANT_ID, compoundAlarm.getAlarmDefinition().getId(), null, null,
                        null, null, null, null, null, 1, false), compoundAlarm);

    checkList(repo.find(TENANT_ID, null, "cpu.sys_mem", null, null,
                        null, null, null, null, 1, false), compoundAlarm);

    checkList(repo.find(TENANT_ID, null, "cpu.idle_perc", null, null,
                        null, null, null, null, 1, false), alarm1, alarm2, alarm3, compoundAlarm);

    checkList(
        repo.find(TENANT_ID, null, "cpu.idle_perc",
                  ImmutableMap.<String, String>builder().put("flavor_id", "222").build(),
                  null, null, null, null, null, 1, false), alarm1,
        alarm3);

    checkList(
        repo.find(TENANT_ID, null, "cpu.idle_perc",
                  ImmutableMap.<String, String>builder().put("service", "monitoring")
                  .put("hostname", "roland").build(), null, null, null,
                  null, null, 1, false), compoundAlarm);

    checkList(repo.find(TENANT_ID, null, null, null,
                        AlarmState.UNDETERMINED, null, null, null, null, 1, false),
              alarm2,
              compoundAlarm);

    checkList(
        repo.find(TENANT_ID, alarm1.getAlarmDefinition().getId(), "cpu.idle_perc", ImmutableMap
                  .<String, String>builder().put("service", "monitoring").build(), null, null, null,
                  null, null, 1, false), alarm1, alarm2);

    checkList(
        repo.find(TENANT_ID, alarm1.getAlarmDefinition().getId(), "cpu.idle_perc", null, null,
                  null, null, null, null, 1, false),
        alarm1, alarm2, alarm3);

    checkList(repo.find(TENANT_ID, compoundAlarm.getAlarmDefinition().getId(), null, null,
                        AlarmState.UNDETERMINED, null, null, null, null, 1, false), compoundAlarm);

    checkList(repo.find(TENANT_ID, null, "cpu.sys_mem", null, AlarmState.UNDETERMINED, null,
                        null, null, null, 1, false),
        compoundAlarm);

    checkList(repo.find(TENANT_ID, null, "cpu.idle_perc", ImmutableMap.<String, String>builder()
                        .put("service", "monitoring").build(), AlarmState.UNDETERMINED, null,
                        null, null, null, 1,false), alarm2, compoundAlarm);

    checkList(repo.find(TENANT_ID, alarm1.getAlarmDefinition().getId(), "cpu.idle_perc",
        ImmutableMap.<String, String>builder().put("service", "monitoring").build(),
        AlarmState.UNDETERMINED, null, null, null, null, 1, false), alarm2);

    checkList(repo.find(TENANT_ID, null, null, null,
                        null, null, null, DateTime.now(DateTimeZone.forID("UTC")), null, 0, false));

    checkList(repo.find(TENANT_ID, null, null, null, null, null, null,
                        ISO_8601_FORMATTER.parseDateTime("2015-03-15T00:00:00Z"),
                        null, 0, false), compoundAlarm);

    checkList(
        repo.find(TENANT_ID, null, null, null, null, null, null,
                  ISO_8601_FORMATTER.parseDateTime("2015-03-14T00:00:00Z"), null,
                  1, false), alarm1, alarm2, alarm3, compoundAlarm);
  }

  private DateTime getAlarmStateUpdatedDate(final String alarmId) {
    final List<Map<String, Object>> rows =
        handle.createQuery("select state_updated_at from alarm where id = :alarmId")
            .bind("alarmId", alarmId).list();
    final Object state_updated_at = rows.get(0).get("state_updated_at");
    return (new DateTime(((Timestamp)state_updated_at).getTime(), DateTimeZone.forID("UTC")));
  }

  private DateTime getAlarmUpdatedDate(final String alarmId) {
    final List<Map<String, Object>> rows =
        handle.createQuery("select updated_at from alarm where id = :alarmId")
            .bind("alarmId", alarmId).list();
    final Object state_updated_at = rows.get(0).get("updated_at");
    return (new DateTime(((Timestamp)state_updated_at).getTime(), DateTimeZone.forID("UTC")));
  }

  @Test(groups = "jooq")
  public void shouldUpdate() throws InterruptedException {
    final Alarm originalAlarm = repo.findById(TENANT_ID, ALARM_ID);
    final DateTime originalStateUpdatedAt = getAlarmStateUpdatedDate(ALARM_ID);
    final DateTime originalUpdatedAt = getAlarmUpdatedDate(ALARM_ID);
    assertEquals(originalAlarm.getState(), AlarmState.UNDETERMINED);

    Thread.sleep(1000);
    final Alarm newAlarm = repo.update(TENANT_ID, ALARM_ID, AlarmState.OK, null, null);
    final DateTime newStateUpdatedAt = getAlarmStateUpdatedDate(ALARM_ID);
    final DateTime newUpdatedAt = getAlarmUpdatedDate(ALARM_ID);
    assertNotEquals(newStateUpdatedAt.getMillis(), originalStateUpdatedAt.getMillis(),
                    "state_updated_at did not change");
    assertNotEquals(newUpdatedAt.getMillis(), originalUpdatedAt.getMillis(),
                    "updated_at did not change");

    assertEquals(newAlarm, originalAlarm);

    newAlarm.setState(AlarmState.OK);
    newAlarm.setStateUpdatedTimestamp(newStateUpdatedAt);
    newAlarm.setUpdatedTimestamp(newUpdatedAt);

    // Make sure it was updated in the DB
    assertEquals(repo.findById(TENANT_ID, ALARM_ID), newAlarm);

    Thread.sleep(1000);
    final Alarm unchangedAlarm = repo.update(TENANT_ID, ALARM_ID, AlarmState.OK, "OPEN", null);
    assertTrue(getAlarmStateUpdatedDate(ALARM_ID).equals(newStateUpdatedAt),
               "state_updated_at did change");
    assertNotEquals(getAlarmUpdatedDate(ALARM_ID).getMillis(), newStateUpdatedAt,
                    "updated_at did not change");
    assertEquals(unchangedAlarm, newAlarm);
  }

  @Test(groups = "jooq", expectedExceptions = EntityNotFoundException.class)
  public void shouldUpdateThrowException() {

    repo.update(TENANT_ID, "Not a valid alarm id", AlarmState.UNDETERMINED, null, null);
  }

  @Test(groups = "jooq")
  public void shouldFindById() {

    final Alarm alarm = repo.findById(TENANT_ID, compoundAlarm.getId());

    assertEquals(alarm, compoundAlarm);
  }

  @Test(groups = "jooq", expectedExceptions = EntityNotFoundException.class)
  public void shouldFindByIdThrowException() {

    repo.findById(TENANT_ID, "Not a valid alarm id");
  }
}
