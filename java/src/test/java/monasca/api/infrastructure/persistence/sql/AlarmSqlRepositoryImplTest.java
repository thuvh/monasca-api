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

import static org.testng.Assert.assertEquals;
import static org.testng.Assert.assertNotEquals;
import static org.testng.Assert.assertTrue;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

import monasca.api.domain.exception.EntityNotFoundException;
import monasca.api.domain.model.alarm.Alarm;
import monasca.api.domain.model.alarm.AlarmRepo;
import monasca.common.hibernate.db.AlarmDb;
import monasca.common.hibernate.db.AlarmDefinitionDb;
import monasca.common.hibernate.db.AlarmMetricDb;
import monasca.common.hibernate.db.MetricDefinitionDb;
import monasca.common.hibernate.db.MetricDefinitionDimensionsDb;
import monasca.common.hibernate.db.MetricDimensionDb;
import monasca.common.hibernate.db.SubAlarmDb;
import monasca.common.model.alarm.AlarmState;
import monasca.common.model.alarm.AlarmSubExpression;
import monasca.common.model.metric.MetricDefinition;

import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.joda.time.DateTime;
import org.joda.time.DateTimeZone;
import org.joda.time.format.DateTimeFormatter;
import org.joda.time.format.ISODateTimeFormat;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableMap.Builder;

@Test(groups = "orm")
public class AlarmSqlRepositoryImplTest {
  private static final String TENANT_ID = "bob";
  private static final String ALARM_ID = "234111";
  private static final DateTimeFormatter ISO_8601_FORMATTER = ISODateTimeFormat.dateOptionalTimeParser().withZoneUTC();
  private SessionFactory sessionFactory;
  private AlarmRepo repo;
  private List<String> alarmActions;
  private Alarm compoundAlarm;
  private Alarm alarm1;
  private Alarm alarm2;
  private Alarm alarm3;

  @BeforeClass
  protected void setupClass() throws Exception {

    sessionFactory = HibernateUtil.getSessionFactory();
    repo = new AlarmSqlRepoImpl(sessionFactory);

    alarmActions = new ArrayList<String>();
    alarmActions.add("29387234");
    alarmActions.add("77778687");
  }

  @BeforeMethod
  protected void beforeMethod() {
    Session session = null;
    try {
      session = sessionFactory.openSession();

      session.beginTransaction();
      session.createSQLQuery("truncate table alarm").executeUpdate();
      session.createSQLQuery("truncate table sub_alarm").executeUpdate();
      session.createSQLQuery("truncate table alarm_action").executeUpdate();
      session.createSQLQuery("truncate table sub_alarm_definition").executeUpdate();
      session.createSQLQuery("truncate table alarm_action").executeUpdate();
      session.createSQLQuery("truncate table sub_alarm_definition_dimension").executeUpdate();
      session.createSQLQuery("truncate table alarm_definition").executeUpdate();
      session.createSQLQuery("truncate table alarm_metric").executeUpdate();
      session.createSQLQuery("truncate table metric_definition").executeUpdate();
      session.createSQLQuery("truncate table metric_definition_dimensions").executeUpdate();
      session.createSQLQuery("truncate table metric_dimension").executeUpdate();

      DateTime timestamp1 = ISO_8601_FORMATTER.parseDateTime("2015-03-14T09:26:53");
      // .withZoneRetainFields(
      // DateTimeZone.forID("UTC"));
      DateTime timestamp2 = ISO_8601_FORMATTER.parseDateTime("2015-03-14T09:26:54").withZoneRetainFields(DateTimeZone.forID("UTC"));
      DateTime timestamp3 = ISO_8601_FORMATTER.parseDateTime("2015-03-14T09:26:55").withZoneRetainFields(DateTimeZone.forID("UTC"));

      session
          .createSQLQuery(
              "insert into alarm_definition (id, tenant_id, name, severity, expression, match_by, actions_enabled, created_at, updated_at, deleted_at) "
                  + "values ('1', 'bob', '90% CPU', 'LOW', 'avg(cpu.idle_perc{flavor_id=777, image_id=888, device=1}) > 10', 'flavor_id,image_id', 1, NOW(), NOW(), NULL)")
          .executeUpdate();

      session.save(new AlarmDb("1", "1", AlarmState.OK, "OPEN", "http://somesite.com/this-alarm-info", timestamp1, timestamp1, timestamp1));
      session.save(new AlarmDb("2", "1", AlarmState.UNDETERMINED, "OPEN", null, timestamp2, timestamp2, timestamp2));
      session.save(new AlarmDb("3", "1", AlarmState.ALARM, null, "http://somesite.com/this-alarm-info", timestamp3, timestamp3, timestamp3));

      long subAlarmId = 42;
      for (int alarmId = 1; alarmId <= 3; alarmId++) {
        SubAlarmDb subAlarmDb =
            new SubAlarmDb(String.valueOf(subAlarmId++), String.valueOf(alarmId), "",
                "avg(cpu.idle_perc{flavor_id=777, image_id=888, device=1}) > 10", new DateTime(), new DateTime());
        session.save(subAlarmDb);
      }

      session.save(new AlarmMetricDb("1", new byte[] {1, 1}));
      session.save(new AlarmMetricDb("1", new byte[] {2, 2}));
      session.save(new AlarmMetricDb("2", new byte[] {1, 1}));
      session.save(new AlarmMetricDb("3", new byte[] {2, 2}));

      session.save(new MetricDefinitionDb(new byte[] {1}, "cpu.idle_perc", "bob", "west"));

      session.save(new MetricDefinitionDimensionsDb(new byte[] {1, 1}, new byte[] {1}, new byte[] {1}));
      session.save(new MetricDefinitionDimensionsDb(new byte[] {2, 2}, new byte[] {1}, new byte[] {2}));

      session.save(new MetricDimensionDb(new byte[] {1}, "instance_id", "123"));
      session.save(new MetricDimensionDb(new byte[] {1}, "service", "monitoring"));
      session.save(new MetricDimensionDb(new byte[] {2}, "flavor_id", "222"));

      alarm1 =
          new Alarm("1", "1", "90% CPU", "LOW", buildAlarmMetrics(
              buildMetricDefinition("cpu.idle_perc", "flavor_id", "222", "instance_id", "123", "service", "monitoring"))
              , AlarmState.OK, "OPEN", "http://somesite.com/this-alarm-info", timestamp1,
              timestamp1, timestamp1);

      alarm2 =
          new Alarm("2", "1", "90% CPU", "LOW", buildAlarmMetrics(buildMetricDefinition("cpu.idle_perc", "instance_id", "123", "service",
              "monitoring")), AlarmState.UNDETERMINED, "OPEN", null, timestamp2, timestamp2, timestamp2);

      alarm3 =
          new Alarm("3", "1", "90% CPU", "LOW", buildAlarmMetrics(buildMetricDefinition("cpu.idle_perc", "flavor_id", "222")), AlarmState.ALARM,
              null, "http://somesite.com/this-alarm-info", timestamp3, timestamp3, timestamp3);

      DateTime timestamp4 = ISO_8601_FORMATTER.parseDateTime("2015-03-15T09:26:53");

      session
          .createSQLQuery(
              "insert into alarm_definition (id, tenant_id, name, severity, expression, match_by, actions_enabled, created_at, updated_at, deleted_at) "
                  + "values ('234', 'bob', '50% CPU', 'LOW', 'avg(cpu.sys_mem{service=monitoring}) > 20 and avg(cpu.idle_perc{service=monitoring}) < 10', 'hostname,region', 1, NOW(), NOW(), NULL)")
          .executeUpdate();

      session.save(new AlarmDb("234111", "234", AlarmState.UNDETERMINED, null, null, timestamp4, timestamp4, timestamp4));

      SubAlarmDb subAlarmDb1 = new SubAlarmDb("4343", "234111", "", "avg(cpu.sys_mem{service=monitoring}) > 20", new DateTime(), new DateTime());
      SubAlarmDb subAlarmDb2 = new SubAlarmDb("4242", "234111", "", "avg(cpu.idle_perc{service=monitoring}) < 10", new DateTime(), new DateTime());
      session.save(subAlarmDb1);
      session.save(subAlarmDb2);

      session.save(new AlarmMetricDb("234111", new byte[] {3, 1}));
      session.save(new AlarmMetricDb("234111", new byte[] {3, 2}));

      session.save(new MetricDefinitionDb(new byte[] {1, 1, 1}, "cpu.sys_mem", "bob", "west"));
      session.save(new MetricDefinitionDb(new byte[] {1, 1, 2}, "cpu.idle_perc", "bob", "west"));

      session.save(new MetricDefinitionDimensionsDb(new byte[] {3, 1}, new byte[] {1, 1, 1}, new byte[] {2, 1}));
      session.save(new MetricDefinitionDimensionsDb(new byte[] {3, 2}, new byte[] {1, 1, 2}, new byte[] {2, 2}));

      session.save(new MetricDimensionDb(new byte[] {2, 1}, "service", "monitoring"));
      session.save(new MetricDimensionDb(new byte[] {2, 2}, "service", "monitoring"));
      session.save(new MetricDimensionDb(new byte[] {2, 1}, "hostname", "roland"));
      session.save(new MetricDimensionDb(new byte[] {2, 2}, "hostname", "roland"));
      session.save(new MetricDimensionDb(new byte[] {2, 1}, "region", "colorado"));
      session.save(new MetricDimensionDb(new byte[] {2, 2}, "region", "colorado"));
      session.save(new MetricDimensionDb(new byte[] {2, 2}, "extra", "vivi"));

      session.getTransaction().commit();

      compoundAlarm =
          new Alarm("234111", "234", "50% CPU", "LOW", buildAlarmMetrics(
              buildMetricDefinition("cpu.idle_perc", "extra", "vivi", "hostname", "roland", "region", "colorado", "service", "monitoring"),
              buildMetricDefinition("cpu.sys_mem", "hostname", "roland", "region", "colorado", "service", "monitoring")),
              AlarmState.UNDETERMINED, null, null, timestamp4, timestamp4, timestamp4);

    } finally {
      if (session != null) {
        session.close();
      }
    }

  }

  private List<MetricDefinition> buildAlarmMetrics(final MetricDefinition... metricDefinitions) {
    return Arrays.asList(metricDefinitions);
  }

  private MetricDefinition buildMetricDefinition(final String metricName, final String... dimensions) {
    final Builder<String, String> builder = ImmutableMap.<String, String>builder();
    for (int i = 0; i < dimensions.length;) {
      builder.put(dimensions[i], dimensions[i + 1]);
      i += 2;
    }
    return new MetricDefinition(metricName, builder.build());
  }

  @Test(groups = "orm")
  public void shouldDelete() {
    Session session = null;
    repo.deleteById(TENANT_ID, ALARM_ID);
    try {

      session = sessionFactory.openSession();

      List<AlarmDefinitionDb> rows = session.createQuery("from AlarmDefinitionDb ad where ad.id='234'").list();
      assertEquals(rows.size(), 1, "Alarm Definition was deleted as well");

    } finally {
      if (session != null) {
        session.close();
      }
    }
  }

  @Test(groups = "orm", expectedExceptions = EntityNotFoundException.class)
  public void shouldThowExceptionOnDelete() {
    repo.deleteById(TENANT_ID, "Not an alarm ID");
  }

  @Test(groups = "orm")
  public void shouldFindAlarmSubExpressions() {
    final Map<String, AlarmSubExpression> subExpressionMap = repo.findAlarmSubExpressions(ALARM_ID);
    assertEquals(subExpressionMap.size(), 2);
    assertEquals(subExpressionMap.get("4343"), AlarmSubExpression.of("avg(cpu.sys_mem{service=monitoring}) > 20"));
    assertEquals(subExpressionMap.get("4242"), AlarmSubExpression.of("avg(cpu.idle_perc{service=monitoring}) < 10"));
  }

  @Test(groups = "orm")
  public void shouldAlarmSubExpressionsForAlarmDefinition() {
    final Map<String, Map<String, AlarmSubExpression>> alarmSubExpressionMap =
        repo.findAlarmSubExpressionsForAlarmDefinition(alarm1.getAlarmDefinition().getId());
    assertEquals(alarmSubExpressionMap.size(), 3);
    long subAlarmId = 42;
    for (int alarmId = 1; alarmId <= 3; alarmId++) {
      final Map<String, AlarmSubExpression> subExpressionMap = alarmSubExpressionMap.get(String.valueOf(alarmId));
      assertEquals(subExpressionMap.get(String.valueOf(subAlarmId)),
          AlarmSubExpression.of("avg(cpu.idle_perc{flavor_id=777, image_id=888, device=1}) > 10"));
      subAlarmId++;
    }
  }

  @Test(groups = "orm")
  public void shouldFind() {

    checkList(repo.find("Not a tenant id", null, null, null, null, null, null, null, null, 1, false));

    checkList(repo.find(TENANT_ID, null, null, null, null, null, null, null, null, 1, false), alarm1, alarm2, alarm3, compoundAlarm);

    checkList(repo.find(TENANT_ID, compoundAlarm.getAlarmDefinition().getId(), null, null, null, null, null, null, null, 1, false), compoundAlarm);

    checkList(repo.find(TENANT_ID, null, "cpu.sys_mem", null, null, null, null, null, null, 1, false), compoundAlarm);

    checkList(repo.find(TENANT_ID, null, "cpu.idle_perc", null, null, null, null, null, null, 1, false), alarm1, alarm2, alarm3, compoundAlarm);

    checkList(repo.find(TENANT_ID, null, "cpu.idle_perc", ImmutableMap.<String, String>builder().put("flavor_id", "222").build(), null, null, null,
        null, null, 1, false), alarm1, alarm3);

    checkList(
        repo.find(TENANT_ID, null, "cpu.idle_perc", ImmutableMap.<String, String>builder().put("service", "monitoring").put("hostname", "roland")
            .build(), null, null, null, null, null, 1, false), compoundAlarm);

    checkList(repo.find(TENANT_ID, null, null, null, AlarmState.UNDETERMINED, null, null, null, null, 1, false), alarm2, compoundAlarm);

    checkList(
        repo.find(TENANT_ID, alarm1.getAlarmDefinition().getId(), "cpu.idle_perc", ImmutableMap.<String, String>builder()
            .put("service", "monitoring").build(), null, null, null, null, null, 1, false), alarm1, alarm2);

    checkList(repo.find(TENANT_ID, alarm1.getAlarmDefinition().getId(), "cpu.idle_perc", null, null, null, null, null, null, 1, false), alarm1,
        alarm2, alarm3);

    checkList(
        repo.find(TENANT_ID, compoundAlarm.getAlarmDefinition().getId(), null, null, AlarmState.UNDETERMINED, null, null, null, null, 1, false),
        compoundAlarm);

    checkList(repo.find(TENANT_ID, null, "cpu.sys_mem", null, AlarmState.UNDETERMINED, null, null, null, null, 1, false), compoundAlarm);

    checkList(repo.find(TENANT_ID, null, "cpu.idle_perc", ImmutableMap.<String, String>builder().put("service", "monitoring").build(),
        AlarmState.UNDETERMINED, null, null, null, null, 1, false), alarm2, compoundAlarm);

    checkList(
        repo.find(TENANT_ID, alarm1.getAlarmDefinition().getId(), "cpu.idle_perc", ImmutableMap.<String, String>builder()
            .put("service", "monitoring").build(), AlarmState.UNDETERMINED, null, null, null, null, 1, false), alarm2);

    checkList(repo.find(TENANT_ID, null, null, null, null, null, null, DateTime.now(DateTimeZone.forID("UTC")), null, 0, false));

    checkList(repo.find(TENANT_ID, null, null, null, null, null, null, ISO_8601_FORMATTER.parseDateTime("2015-03-15T00:00:00Z"), null, 0, false),
        compoundAlarm);

    checkList(repo.find(TENANT_ID, null, null, null, null, null, null, ISO_8601_FORMATTER.parseDateTime("2015-03-14T00:00:00Z"), null, 1, false),
        alarm1, alarm2, alarm3, compoundAlarm);

  }

  @Test(groups = "orm")
  public void shouldFindById() {

    final Alarm alarm = repo.findById(TENANT_ID, compoundAlarm.getId());

    assertEquals(alarm.getId(), compoundAlarm.getId());
    assertEquals(alarm.getAlarmDefinition(), compoundAlarm.getAlarmDefinition());
    assertEquals(alarm.getCreatedTimestamp(), compoundAlarm.getCreatedTimestamp());
    assertEquals(alarm.getStateUpdatedTimestamp(), compoundAlarm.getStateUpdatedTimestamp());
    assertEquals(alarm.getState(), compoundAlarm.getState());
    assertEquals(alarm.getMetrics().size(), compoundAlarm.getMetrics().size());
    for (MetricDefinition metrics : alarm.getMetrics()) {
      compoundAlarm.getMetrics().contains(metrics);
    }

  }

  @Test(groups = "orm", expectedExceptions = EntityNotFoundException.class)
  public void shouldFindByIdThrowException() {

    repo.findById(TENANT_ID, "Not a valid alarm id");
  }

  @Test(groups = "orm")
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
    assertTrue(getAlarmStateUpdatedDate(ALARM_ID).equals(newStateUpdatedAt), "state_updated_at did change");
    assertNotEquals(getAlarmUpdatedDate(ALARM_ID).getMillis(), newStateUpdatedAt, "updated_at did not change");
    assertEquals(unchangedAlarm, newAlarm);
  }

  @Test(groups = "orm", expectedExceptions = EntityNotFoundException.class)
  public void shouldUpdateThrowException() {

    repo.update(TENANT_ID, "Not a valid alarm id", AlarmState.UNDETERMINED, null, null);
  }

  private void checkList(List<Alarm> found, Alarm... expected) {
    assertEquals(found.size(), expected.length);
    for (Alarm alarm : expected) {
      assertTrue(found.contains(alarm));
    }
  }

  private DateTime getAlarmUpdatedDate(final String alarmId) {
    Session session = null;
    DateTime updated_at = null;
    try {
      session = sessionFactory.openSession();
      final List<DateTime> rows = session.createQuery("select updated_at from AlarmDb where id = :alarmId").setString("alarmId", alarmId).list();
      updated_at = rows.get(0);
    } finally {
      if (session != null) {
        session.close();
      }
    }
    return (new DateTime(((DateTime) updated_at).getMillis(), DateTimeZone.forID("UTC")));
  }

  private DateTime getAlarmStateUpdatedDate(final String alarmId) {
    Session session = null;
    DateTime state_updated_at = null;

    try {
      session = sessionFactory.openSession();
      final List<DateTime> rows =
          session.createQuery("select state_updated_at from AlarmDb where id = :alarmId").setString("alarmId", alarmId).list();
      state_updated_at = rows.get(0);
    } finally {
      if (session != null) {
        session.close();
      }
    }
    return (new DateTime(((DateTime) state_updated_at).getMillis(), DateTimeZone.forID("UTC")));
  }
}
