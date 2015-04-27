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
import static org.testng.Assert.assertNull;
import static org.testng.Assert.assertTrue;
import static org.testng.Assert.fail;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import monasca.api.domain.exception.EntityNotFoundException;
import monasca.api.domain.model.alarmdefinition.AlarmDefinition;
import monasca.api.domain.model.alarmdefinition.AlarmDefinitionRepo;
import monasca.common.model.alarm.AggregateFunction;
import monasca.common.model.alarm.AlarmOperator;
import monasca.common.model.alarm.AlarmSubExpression;
import monasca.common.model.metric.MetricDefinition;

import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import com.google.common.collect.ImmutableMap;

@Test(groups = "orm")
public class AlarmDefinitionSqlRepositoryImplTest {

  private SessionFactory sessionFactory;
  private AlarmDefinitionRepo repo;
  private AlarmDefinition alarmDef_123;
  private AlarmDefinition alarmDef_234;
  private List<String> alarmActions;

  @BeforeClass
  protected void setupClass() throws Exception {
    sessionFactory = HibernateUtil.getSessionFactory();
    repo = new AlarmDefinitionSqlRepoImpl(sessionFactory);
    alarmActions = new ArrayList<String>();
    alarmActions.add("29387234");
    alarmActions.add("77778687");
  }

  @BeforeMethod
  protected void beforeMethod() {

    Session session = sessionFactory.openSession();

    session.beginTransaction();
    session.createSQLQuery("truncate table sub_alarm").executeUpdate();
    session.createSQLQuery("truncate table sub_alarm_definition").executeUpdate();
    session.createSQLQuery("truncate table alarm_action").executeUpdate();
    session.createSQLQuery("truncate table sub_alarm_definition_dimension").executeUpdate();
    session.createSQLQuery("truncate table alarm_definition").executeUpdate();

    session
        .createSQLQuery(
            "insert into alarm_definition (id, tenant_id, name, severity, expression, match_by, actions_enabled, created_at, updated_at, deleted_at) "
                + "values ('123', 'bob', '90% CPU', 'LOW', 'avg(hpcs.compute{flavor_id=777, image_id=888, metric_name=cpu, device=1}) > 10', 'flavor_id,image_id', 1, NOW(), NOW(), NULL)")
        .executeUpdate();

    session.createSQLQuery(
        "insert into sub_alarm_definition (id, alarm_definition_id, function, metric_name, operator, threshold, period, periods, created_at, updated_at) "
            + "values ('111', '123', 'avg', 'hpcs.compute', 'GT', 10, 60, 1, NOW(), NOW())").executeUpdate();
    session.createSQLQuery(
        "insert into sub_alarm_definition_dimension (sub_alarm_definition_id, dimension_name, value) values ('111', 'flavor_id', '777')")
        .executeUpdate();
    session.createSQLQuery(
        "insert into sub_alarm_definition_dimension (sub_alarm_definition_id, dimension_name, value) values ('111', 'image_id', '888')")
        .executeUpdate();
    session.createSQLQuery(
        "insert into sub_alarm_definition_dimension (sub_alarm_definition_id, dimension_name, value) values ('111', 'metric_name', 'cpu')")
        .executeUpdate();
    session.createSQLQuery(
        "insert into sub_alarm_definition_dimension (sub_alarm_definition_id, dimension_name, value) values ('111', 'device', '1')").executeUpdate();
    session.createSQLQuery("insert into alarm_action (alarm_definition_id, alarm_state, action_id) values ('123', 'ALARM', '29387234')")
        .executeUpdate();
    session.createSQLQuery("insert into alarm_action (alarm_definition_id, alarm_state, action_id) values ('123', 'ALARM', '77778687')")
        .executeUpdate();

    session
        .createSQLQuery(
            "insert into alarm_definition (id, tenant_id, name, severity, expression, match_by, actions_enabled, created_at, updated_at, deleted_at) "
                + "values ('234', 'bob', '50% CPU', 'LOW', 'avg(hpcs.compute{flavor_id=777, image_id=888, metric_name=mem}) > 20 and avg(hpcs.compute) < 100', 'flavor_id,image_id', 1, NOW(), NOW(), NULL)")
        .executeUpdate();
    session.createSQLQuery(
        "insert into sub_alarm_definition (id, alarm_definition_id, function, metric_name, operator, threshold, period, periods, created_at, updated_at) "
            + "values ('222', '234', 'avg', 'hpcs.compute', 'GT', 20, 60, 1, NOW(), NOW())").executeUpdate();
    session.createSQLQuery(
        "insert into sub_alarm_definition (id, alarm_definition_id, function, metric_name, operator, threshold, period, periods, created_at, updated_at) "
            + "values ('223', '234', 'avg', 'hpcs.compute', 'LT', 100, 60, 1, NOW(), NOW())").executeUpdate();
    session.createSQLQuery(
        "insert into sub_alarm_definition_dimension (sub_alarm_definition_id, dimension_name, value) values ('222', 'flavor_id', '777')")
        .executeUpdate();
    session.createSQLQuery(
        "insert into sub_alarm_definition_dimension (sub_alarm_definition_id, dimension_name, value) values ('222', 'image_id', '888')")
        .executeUpdate();
    session.createSQLQuery(
        "insert into sub_alarm_definition_dimension (sub_alarm_definition_id, dimension_name, value) values ('222', 'metric_name', 'mem')")
        .executeUpdate();
    session.createSQLQuery("insert into alarm_action (alarm_definition_id, alarm_state, action_id) values ('234', 'ALARM', '29387234')")
        .executeUpdate();
    session.createSQLQuery("insert into alarm_action (alarm_definition_id, alarm_state, action_id) values ('234', 'ALARM', '77778687')")
        .executeUpdate();

    session.getTransaction().commit();
    session.close();

    alarmDef_123 =
        new AlarmDefinition("123", "90% CPU", null, "LOW", "avg(hpcs.compute{flavor_id=777, image_id=888, metric_name=cpu, device=1}) > 10",
            Arrays.asList("flavor_id", "image_id"), true, Arrays.asList("29387234", "77778687"), Collections.<String>emptyList(),
            Collections.<String>emptyList());
    alarmDef_234 =
        new AlarmDefinition("234", "50% CPU", null, "LOW",
            "avg(hpcs.compute{flavor_id=777, image_id=888, metric_name=mem}) > 20 and avg(hpcs.compute) < 100",
            Arrays.asList("flavor_id", "image_id"), true, Arrays.asList("29387234", "77778687"), Collections.<String>emptyList(),
            Collections.<String>emptyList());

  }

  @Test(groups = "orm")
  public void shouldCreate() {
    Session session = null;
    int subAlarmDimensionSize;
    int subAlarmSize;
    Map<String, AlarmSubExpression> subExpressions =
        ImmutableMap.<String, AlarmSubExpression>builder()
            .put("4433", AlarmSubExpression.of("avg(hpcs.compute{flavor_id=777, image_id=888, metric_name=cpu}) > 10")).build();

    AlarmDefinition alarmA =
        repo.create("555", "2345", "90% CPU", null, "LOW", "avg(hpcs.compute{flavor_id=777, image_id=888, metric_name=cpu}) > 10", subExpressions,
            Arrays.asList("flavor_id", "image_id"), alarmActions, null, null);
    AlarmDefinition alarmB = repo.findById("555", alarmA.getId());

    assertEquals(alarmA.getId(), alarmB.getId());
    assertEquals(alarmA.getName(), alarmB.getName());
    assertEquals(alarmA.getAlarmActions().size(), alarmB.getAlarmActions().size());
    for (String alarmAction : alarmA.getAlarmActions()) {
      assertTrue(alarmB.getAlarmActions().contains(alarmAction));
    }

    // Assert that sub-alarm and sub-alarm-dimensions made it to the db
    try {
      session = sessionFactory.openSession();

      subAlarmSize = session.createQuery("from SubAlarmDefinitionDb sub where sub.id = '4433'").list().size();

      subAlarmDimensionSize =
          session.createQuery("from SubAlarmDefinitionDimensionDb sub where sub.subAlarmDefinitionDimensionId.sub_alarm_definition_id = '4433'")
              .list().size();

    } finally {
      if (session != null) {
        session.close();
      }
    }
    assertEquals(subAlarmSize, 1);
    assertEquals(subAlarmDimensionSize, 3);
  }

  @Test(groups = "orm")
  public void shouldUpdate() {

    List<String> oldSubAlarmIds = Arrays.asList("222");
    AlarmSubExpression changedSubExpression = AlarmSubExpression.of("avg(hpcs.compute) <= 200");
    Map<String, AlarmSubExpression> changedSubExpressions =
        ImmutableMap.<String, AlarmSubExpression>builder().put("223", changedSubExpression).build();
    AlarmSubExpression newSubExpression = AlarmSubExpression.of("avg(foo{flavor_id=777}) > 333");
    Map<String, AlarmSubExpression> newSubExpressions = ImmutableMap.<String, AlarmSubExpression>builder().put("555", newSubExpression).build();

    repo.update("bob", "234", false, "90% CPU", null, "avg(foo{flavor_id=777}) > 333 and avg(hpcs.compute) <= 200",
        Arrays.asList("flavor_id", "image_id"), "LOW", false, oldSubAlarmIds, changedSubExpressions, newSubExpressions, alarmActions, null, null);

    AlarmDefinition alarm = repo.findById("bob", "234");
    AlarmDefinition expected =
        new AlarmDefinition("234", "90% CPU", null, "LOW", "avg(foo{flavor_id=777}) > 333 and avg(hpcs.compute) <= 200", Arrays.asList("flavor_id",
            "image_id"), false, alarmActions, Collections.<String>emptyList(), Collections.<String>emptyList());

    assertEquals(expected.getId(), alarm.getId());
    assertEquals(expected.getName(), alarm.getName());
    assertEquals(expected.getExpressionData(), alarm.getExpressionData());
    assertEquals(expected.getAlarmActions().size(), alarm.getAlarmActions().size());
    for (String alarmAction : expected.getAlarmActions()) {
      assertTrue(alarm.getAlarmActions().contains(alarmAction));
    }

    Map<String, AlarmSubExpression> subExpressions = repo.findSubExpressions("234");
    assertEquals(subExpressions.get("223"), changedSubExpression);
    assertEquals(subExpressions.get("555"), newSubExpression);
  }

  @Test(groups = "orm")
  public void shouldFindById() {
    Session session = null;
    AlarmDefinition alarmDef_123_repo = repo.findById("bob", "123");
    assertEquals(alarmDef_123.getDescription(), alarmDef_123_repo.getDescription());
    assertEquals(alarmDef_123.getExpression(), alarmDef_123_repo.getExpression());
    assertEquals(alarmDef_123.getExpressionData(), alarmDef_123_repo.getExpressionData());
    assertEquals(alarmDef_123.getName(), alarmDef_123_repo.getName());
    // Make sure it still finds AlarmDefinitions with no notifications
    try {
      session = sessionFactory.openSession();

      session.createQuery("delete from AlarmActionDb").executeUpdate();

    } finally {
      if (session != null) {
        session.close();
      }
    }
    alarmDef_123.setAlarmActions(new ArrayList<String>(0));
    assertEquals(alarmDef_123, repo.findById("bob", "123"));
  }

  @Test(groups = "orm")
  public void shouldFindSubAlarmMetricDefinitions() {

    assertEquals(repo.findSubAlarmMetricDefinitions("123").get("111"), new MetricDefinition("hpcs.compute", ImmutableMap.<String, String>builder()
        .put("flavor_id", "777").put("image_id", "888").put("metric_name", "cpu").put("device", "1").build()));

    assertEquals(repo.findSubAlarmMetricDefinitions("234").get("222"), new MetricDefinition("hpcs.compute", ImmutableMap.<String, String>builder()
        .put("flavor_id", "777").put("image_id", "888").put("metric_name", "mem").build()));

    assertTrue(repo.findSubAlarmMetricDefinitions("asdfasdf").isEmpty());
  }

  @Test(groups = "orm")
  public void shouldFindSubExpressions() {

    assertEquals(repo.findSubExpressions("123").get("111"), new AlarmSubExpression(AggregateFunction.AVG, new MetricDefinition("hpcs.compute",
        ImmutableMap.<String, String>builder().put("flavor_id", "777").put("image_id", "888").put("metric_name", "cpu").put("device", "1").build()),
        AlarmOperator.GT, 10, 60, 1));

    assertEquals(repo.findSubExpressions("234").get("223"), new AlarmSubExpression(AggregateFunction.AVG, new MetricDefinition("hpcs.compute",
        new HashMap<String, String>()), AlarmOperator.LT, 100, 60, 1));

    assertTrue(repo.findSubAlarmMetricDefinitions("asdfasdf").isEmpty());
  }

  @Test(groups = "orm")
  public void testExists() {
    assertEquals(repo.exists("bob", "90% CPU"), "123");

    // Negative
    assertNull(repo.exists("bob", "999% CPU"));
  }

  @Test(groups = "orm")
  public void shouldDeleteById() {
    repo.deleteById("bob", "123");

    try {
      assertNull(repo.findById("bob", "123"));
      fail();
    } catch (EntityNotFoundException expected) {
    }
    assertEquals(Arrays.asList(alarmDef_234), repo.find("bob", null, null, null, 1));
  }

  public void shouldFindByDimension() {
    final Map<String, String> dimensions = new HashMap<>();
    dimensions.put("image_id", "888");

    List<AlarmDefinition> result = repo.find("bob", null, dimensions, null, 1);

    assertEquals(Arrays.asList(alarmDef_123, alarmDef_234), result);

    dimensions.clear();
    dimensions.put("device", "1");
    assertEquals(Arrays.asList(alarmDef_123), repo.find("bob", null, dimensions, null, 1));

    dimensions.clear();
    dimensions.put("Not real", "AA");
    assertEquals(0, repo.find("bob", null, dimensions, null, 1).size());
  }

  public void shouldFindByName() {
    final Map<String, String> dimensions = new HashMap<>();
    dimensions.put("image_id", "888");

    List<AlarmDefinition> result = repo.find("bob", "90% CPU", dimensions, null, 1);

    assertEquals(Arrays.asList(alarmDef_123), result);

  }
}
