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
import static org.testng.Assert.assertNull;
import static org.testng.Assert.assertTrue;
import static org.testng.Assert.fail;

import java.nio.charset.Charset;
import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import javax.sql.DataSource;

import com.google.common.collect.ImmutableMap;
import com.google.common.io.Resources;

import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import monasca.api.domain.exception.EntityNotFoundException;
import monasca.api.domain.model.alarmdefinition.AlarmDefinition;
import monasca.api.domain.model.alarmdefinition.AlarmDefinitionRepo;
import monasca.api.infrastructure.persistence.PersistUtils;
import monasca.common.jooq.Tables;
import monasca.common.model.alarm.AggregateFunction;
import monasca.common.model.alarm.AlarmOperator;
import monasca.common.model.alarm.AlarmSubExpression;
import monasca.common.model.metric.MetricDefinition;
import org.joda.time.DateTime;
import org.joda.time.DateTimeZone;
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
import org.skife.jdbi.v2.util.StringMapper;
import org.testng.annotations.AfterClass;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

@Test(groups = "jooq")
public class AlarmDefinitionJooqRepositoryImplTest {
  private DataSource ds;
  private SQLDialect dialect;
  private AlarmDefinitionRepo repo;
  private List<String> alarmActions;
  private AlarmDefinition alarmDef123;
  private AlarmDefinition alarmDef234;

  private DBI db;
  private Handle handle;

  private AlarmJooqRepoImpl.DateTimeZoneConverter timeConverter;
  private Settings settings;

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

    repo = new AlarmDefinitionJooqRepoImpl(ds, dialect, new PersistUtils());

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
    final monasca.common.jooq.tables.SubAlarmDefinitionDimension sadd =
        Tables.SUB_ALARM_DEFINITION_DIMENSION;
    final monasca.common.jooq.tables.AlarmDefinition ad = Tables.ALARM_DEFINITION;
    final monasca.common.jooq.tables.AlarmMetric am = Tables.ALARM_METRIC;
    final monasca.common.jooq.tables.MetricDefinition md =
        Tables.METRIC_DEFINITION;
    final monasca.common.jooq.tables.MetricDefinitionDimensions mdd =
        Tables.METRIC_DEFINITION_DIMENSIONS;
    final monasca.common.jooq.tables.MetricDimension mdi = Tables.METRIC_DIMENSION;

    context.transaction(new TransactionalRunnable() {
        @Override
        public void run(Configuration configuration) throws Exception {
          DSLContext create = DSL.using(configuration);

          create.delete(nm).execute();
          create.delete(a).execute();
          create.delete(sa).execute();
          create.delete(sad).execute();
          create.delete(sadd).execute();
          create.delete(aa).execute();
          create.delete(ad).execute();
          create.delete(am).execute();
          create.delete(md).execute();
          create.delete(mdd).execute();
          create.delete(mdi).execute();

          create.batch(create.insertInto(ad, ad.ID, ad.TENANT_ID, ad.NAME, ad.SEVERITY,
                                         ad.EXPRESSION, ad.MATCH_BY, ad.ACTIONS_ENABLED,
                                         ad.CREATED_AT, ad.UPDATED_AT, ad.DELETED_AT)
                       .values(null, null, null, null,
                               null, null, null,
                               DSL.currentTimestamp(),
                               DSL.currentTimestamp(),
                               (Field<Timestamp>) null))
            .bind("123", "bob", "90% CPU", "LOW",
                  "avg(hpcs.compute{flavor_id=777, image_id=888, metric_name=cpu, device=1}) > 10",
                  "flavor_id,image_id", true, null)
            .bind("234", "bob", "50% CPU", "LOW",
                  "avg(hpcs.compute{flavor_id=777, image_id=888, metric_name=mem})"
                  + " > 20 and avg(hpcs.compute) < 100",
                  "flavor_id,image_id", true, null)
            .execute();

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
            .bind("111", "123", "avg",
                  "hpcs.compute", "GT", 10,
                  60, 1,
                  nowT, nowT)
            .bind("222", "234", "avg",
                  "hpcs.compute", "GT", 20,
                  60, 1,
                  nowT, nowT)
            .bind("223", "234", "avg",
                  "hpcs.compute", "LT", 100,
                  60, 1,
                  nowT, nowT)
            .execute();

          create.batch(create.insertInto(sadd, sadd.SUB_ALARM_DEFINITION_ID,
                                         sadd.DIMENSION_NAME, sadd.VALUE)
                       .values((String)null, null, null)
                       )
            .bind("111", "flavor_id", "777")
            .bind("111", "image_id", "888")
            .bind("111", "metric_name", "cpu")
            .bind("111", "device", "1")
            .bind("222", "flavor_id", "777")
            .bind("222", "image_id", "888")
            .bind("222", "metric_name", "mem")
            .execute();

          create.batch(create.insertInto(nm, nm.ID, nm.TENANT_ID, nm.NAME, nm.TYPE, nm.ADDRESS,
                                         nm.CREATED_AT, nm.UPDATED_AT
                                         )
                       .values(null, null, null, null,
                               null, DSL.currentTimestamp(), DSL.currentTimestamp()
                               )
                       )
            .bind("29387234", "alarm-test", "MyEmail", "EMAIL", "a@b")
            .bind("77778687", "alarm-test", "OtherEmail", "EMAIL", "a@b")
            .execute();

          create.batch(create.insertInto(aa, aa.ALARM_DEFINITION_ID,
                                         aa.ALARM_STATE, aa.ACTION_ID)
                       .values((String)null, null, null)
                       )
            .bind("123", "ALARM", "29387234")
            .bind("123", "ALARM", "77778687")
            .bind("234", "ALARM", "29387234")
            .bind("234", "ALARM", "77778687")
            .execute();
        }
      });


    alarmDef123 = new AlarmDefinition("123", "90% CPU", null, "LOW",
        "avg(hpcs.compute{flavor_id=777, image_id=888, metric_name=cpu, device=1}) > 10",
        Arrays.asList("flavor_id", "image_id"), true, Arrays.asList("29387234", "77778687"),
        Collections.<String>emptyList(), Collections.<String>emptyList());
    alarmDef234 = new AlarmDefinition("234","50% CPU", null, "LOW",
        "avg(hpcs.compute{flavor_id=777, image_id=888, metric_name=mem}) > 20 and"
        + " avg(hpcs.compute) < 100",
        Arrays.asList("flavor_id", "image_id"), true, Arrays.asList("29387234", "77778687"),
        Collections.<String>emptyList(), Collections.<String>emptyList());

  }

  @Test(groups = "jooq")
  public void shouldCreate() {
    Map<String, AlarmSubExpression> subExpressions =
        ImmutableMap
            .<String, AlarmSubExpression>builder()
            .put(
                "4433",
                AlarmSubExpression
                    .of("avg(hpcs.compute{flavor_id=777, image_id=888, metric_name=cpu}) > 10"))
            .build();

    AlarmDefinition alarmA =
        repo.create("555", "2345", "90% CPU", null, "LOW",
            "avg(hpcs.compute{flavor_id=777, image_id=888, metric_name=cpu}) > 10", subExpressions,
            Arrays.asList("flavor_id", "image_id"), alarmActions, null, null);
    AlarmDefinition alarmB = repo.findById("555", alarmA.getId());

    assertEquals(alarmA, alarmB);

    final monasca.common.jooq.tables.SubAlarmDefinitionDimension sadd =
        Tables.SUB_ALARM_DEFINITION_DIMENSION;
    final monasca.common.jooq.tables.SubAlarmDefinition sad = Tables.SUB_ALARM_DEFINITION;
    DSLContext create = DSL.using(this.ds, this.dialect, this.settings);

    // Assert that sub-alarm and sub-alarm-dimensions made it to the db
    assertEquals(create.select(DSL.count())
                 .from(sad)
                 .where(sad.ID.equal("4433"))
                 .fetchOne(0, String.class), "1");
    assertEquals(create.select(DSL.count())
                 .from(sadd)
                 .where(sadd.SUB_ALARM_DEFINITION_ID.equal("4433"))
                 .fetchOne(0, String.class), "3");
  }

  @Test(groups = "jooq")
  public void shouldUpdate() {
    beforeMethod();

    List<String> oldSubAlarmIds = Arrays.asList("222");
    AlarmSubExpression changedSubExpression = AlarmSubExpression.of("avg(hpcs.compute) <= 200");
    Map<String, AlarmSubExpression> changedSubExpressions =
        ImmutableMap.<String, AlarmSubExpression>builder().put("223", changedSubExpression).build();
    AlarmSubExpression newSubExpression = AlarmSubExpression.of("avg(foo{flavor_id=777}) > 333");
    Map<String, AlarmSubExpression> newSubExpressions =
        ImmutableMap.<String, AlarmSubExpression>builder().put("555", newSubExpression).build();

    repo.update("bob", "234", false, "90% CPU", null,
        "avg(foo{flavor_id=777}) > 333 and avg(hpcs.compute) <= 200",
        Arrays.asList("flavor_id", "image_id"), "LOW", false, oldSubAlarmIds,
        changedSubExpressions, newSubExpressions, alarmActions, null, null);

    AlarmDefinition alarm = repo.findById("bob", "234");
    AlarmDefinition expected =
        new AlarmDefinition("234", "90% CPU", null, "LOW",
            "avg(foo{flavor_id=777}) > 333 and avg(hpcs.compute) <= 200", Arrays.asList(
                "flavor_id", "image_id"), false, alarmActions, Collections.<String>emptyList(),
            Collections.<String>emptyList());
    assertEquals(expected, alarm);

    Map<String, AlarmSubExpression> subExpressions = repo.findSubExpressions("234");
    assertEquals(subExpressions.get("223"), changedSubExpression);
    assertEquals(subExpressions.get("555"), newSubExpression);
  }

  @Test(groups = "jooq")
  public void shouldFindById() {
    assertEquals(alarmDef123, repo.findById("bob", "123"));

    // Make sure it still finds AlarmDefinitions with no notifications
    final monasca.common.jooq.tables.AlarmAction aa = Tables.ALARM_ACTION;
    DSLContext create = DSL.using(this.ds, this.dialect, this.settings);
    create.delete(aa).execute();
    alarmDef123.setAlarmActions(new ArrayList<String>(0));
    assertEquals(alarmDef123, repo.findById("bob", "123"));
  }

  @Test(groups = "jooq")
  public void shouldFindSubAlarmMetricDefinitions() {
    beforeMethod();

    assertEquals(
        repo.findSubAlarmMetricDefinitions("123").get("111"),
        new MetricDefinition("hpcs.compute", ImmutableMap.<String, String>builder()
            .put("flavor_id", "777").put("image_id", "888").put("metric_name", "cpu")
            .put("device", "1").build()));

    assertEquals(
        repo.findSubAlarmMetricDefinitions("234").get("222"),
        new MetricDefinition("hpcs.compute", ImmutableMap.<String, String>builder()
            .put("flavor_id", "777").put("image_id", "888").put("metric_name", "mem").build()));

    assertTrue(repo.findSubAlarmMetricDefinitions("asdfasdf").isEmpty());
  }

  @Test(groups = "jooq")
  public void shouldFindSubExpressions() {
    beforeMethod();

    assertEquals(
        repo.findSubExpressions("123").get("111"),
        new AlarmSubExpression(AggregateFunction.AVG, new MetricDefinition("hpcs.compute",
            ImmutableMap.<String, String>builder().put("flavor_id", "777").put("image_id", "888")
                .put("metric_name", "cpu").put("device", "1").build()),
                               AlarmOperator.GT, 10, 60, 1));

    assertEquals(repo.findSubExpressions("234").get("223"), new AlarmSubExpression(
        AggregateFunction.AVG,
        new MetricDefinition("hpcs.compute",
                             new HashMap<String, String>()),
        AlarmOperator.LT,
        100,
        60, 1));

    assertTrue(repo.findSubAlarmMetricDefinitions("asdfasdf").isEmpty());
  }

  @Test(groups = "jooq")
  public void testExists() {
    assertEquals(repo.exists("bob", "90% CPU"),"123");

    // Negative
    assertNull(repo.exists("bob", "999% CPU"));
  }

  @Test(groups = "jooq")
  public void shouldFind() {
    assertEquals(Arrays.asList(alarmDef123, alarmDef234), repo.find("bob", null, null, null, 1));

    // Make sure it still finds AlarmDefinitions with no notifications
    final monasca.common.jooq.tables.AlarmAction aa = Tables.ALARM_ACTION;
    DSLContext create = DSL.using(this.ds, this.dialect, this.settings);
    create.delete(aa).execute();

    alarmDef123.setAlarmActions(new ArrayList<String>(0));
    alarmDef234.setAlarmActions(new ArrayList<String>(0));
    assertEquals(Arrays.asList(alarmDef123, alarmDef234), repo.find("bob", null, null, null, 1));

    assertEquals(0, repo.find("bill", null, null, null, 1).size());
  }

  @Test(groups = "jooq")
  public void shouldFindByDimension() {
    final Map<String, String> dimensions = new HashMap<>();
    dimensions.put("image_id", "888");
    assertEquals(Arrays.asList(alarmDef123, alarmDef234),
        repo.find("bob", null, dimensions, null, 1));

    dimensions.clear();
    dimensions.put("device", "1");
    assertEquals(Arrays.asList(alarmDef123), repo.find("bob", null, dimensions, null, 1));

    dimensions.clear();
    dimensions.put("Not real", "AA");
    assertEquals(0, repo.find("bob", null, dimensions, null, 1).size());
  }

  @Test(groups = "jooq")
  public void shouldFindByName() {
    assertEquals(Arrays.asList(alarmDef123), repo.find("bob", "90% CPU", null, null, 1));

    assertEquals(0, repo.find("bob", "Does not exist", null, null, 1).size());
  }

  @Test(groups = "jooq")
  public void shouldDeleteById() {
    repo.deleteById("bob", "123");

    try {
      assertNull(repo.findById("bob", "123"));
      fail();
    } catch (EntityNotFoundException expected) {
    }
    assertEquals(Arrays.asList(alarmDef234), repo.find("bob", null, null, null, 1));
  }
}
