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

import java.util.HashMap;
import java.util.List;

import monasca.common.hibernate.db.AlarmDb;
import monasca.common.hibernate.db.AlarmMetricDb;
import monasca.common.hibernate.db.MetricDefinitionDimensionsDb;
import monasca.common.hibernate.db.MetricDimensionDb;
import monasca.common.model.alarm.AlarmState;

import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.joda.time.DateTime;
import org.joda.time.format.DateTimeFormatter;
import org.joda.time.format.ISODateTimeFormat;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

@Test(groups = "orm")
public class HibernateUtilsTest {

  private static final DateTimeFormatter ISO_8601_FORMATTER = ISODateTimeFormat.dateOptionalTimeParser().withZoneUTC();
  private SessionFactory sessionFactory;
  private HibernateUtils repo;

  @BeforeClass
  protected void setupClass() throws Exception {
    sessionFactory = HibernateUtil.getSessionFactory();
    repo = new HibernateUtils(sessionFactory);
  }

  @BeforeMethod
  protected void beforeMethod() {

    Session session = sessionFactory.openSession();

    session.beginTransaction();
    session.createSQLQuery("truncate table alarm").executeUpdate();
    session.createSQLQuery("truncate table alarm_definition").executeUpdate();
    session.createSQLQuery("truncate table alarm_metric").executeUpdate();
    session.createSQLQuery("truncate table metric_definition_dimensions").executeUpdate();
    session.createSQLQuery("truncate table metric_dimension").executeUpdate();

    DateTime timestamp1 = ISO_8601_FORMATTER.parseDateTime("2015-03-14T09:26:53");

    session
        .createSQLQuery(
            "insert into alarm_definition (id, tenant_id, name, severity, expression, match_by, actions_enabled, created_at, updated_at, deleted_at) "
                + "values ('1', 'bob', '90% CPU', 'LOW', 'avg(cpu.idle_perc{flavor_id=777, image_id=888, device=1}) > 10', 'flavor_id,image_id', 1, NOW(), NOW(), NULL)")
        .executeUpdate();
    session
        .createSQLQuery(
            "insert into alarm_definition (id, tenant_id, name, severity, expression, match_by, actions_enabled, created_at, updated_at, deleted_at) "
                + "values ('2', 'luk', '90% CPU', 'LOW', 'avg(cpu.idle_perc{flavor_id=777, image_id=888, device=1}) > 10', 'flavor_id,image_id', 1, NOW(), NOW(), NULL)")
        .executeUpdate();

    session.save(new AlarmDb("1", "1", AlarmState.OK, "OPEN", "http://somesite.com/this-alarm-info", timestamp1, timestamp1, timestamp1));
    session.save(new AlarmDb("2", "2", AlarmState.OK, "OPEN", "http://somesite.com/this-alarm-info", timestamp1, timestamp1, timestamp1));

    session.save(new AlarmMetricDb("1", new byte[] {1, 1}));
    session.save(new AlarmMetricDb("1", new byte[] {2, 2}));
    session.save(new AlarmMetricDb("2", new byte[] {1, 1}));
    session.save(new AlarmMetricDb("3", new byte[] {2, 2}));

    session.save(new MetricDefinitionDimensionsDb(new byte[] {1, 1}, new byte[] {1}, new byte[] {1}));
    session.save(new MetricDefinitionDimensionsDb(new byte[] {2, 2}, new byte[] {1}, new byte[] {2}));

    session.save(new MetricDimensionDb(new byte[] {1}, "instance_id", "123"));
    session.save(new MetricDimensionDb(new byte[] {1}, "service", "monitoring"));
    session.save(new MetricDimensionDb(new byte[] {2}, "flavor_id", "222"));

    session.getTransaction().commit();
    session.close();
  }

  public void testNullArguments() {

    List<String> result = repo.findAlarmIds(null, null);

    assertEquals(result.size(), 0, "No alarms");
  }

  public void testWithTenantIdNoExist() {

    List<String> result = repo.findAlarmIds("fake_id", null);

    assertEquals(result.size(), 0, "No alarms");
  }

  public void testWithTenantId() {

    List<String> result = repo.findAlarmIds("bob", new HashMap<String, String>());

    assertEquals(result.size(), 1, "Alarm found");
    assertEquals(result.get(0), "1", "Alarm with id 1 found");

    result = repo.findAlarmIds("luk", new HashMap<String, String>());
    assertEquals(result.size(), 1, "Alarm found");
    assertEquals(result.get(0), "2", "Alarm with id 2 found");
  }

  public void testWithDimensions() {

    HashMap<String, String> dimensions = new HashMap<String, String>();
    dimensions.put("flavor_id", "222");

    List<String> result = repo.findAlarmIds("bob", dimensions);

    assertEquals(result.size(), 1, "Alarm found");
    assertEquals(result.get(0), "1", "Alarm with id 1 found");
  }


  public void testWithNotExixtingDimensions() {

    HashMap<String, String> dimensions = new HashMap<String, String>();
    dimensions.put("a", "b");

    List<String> result = repo.findAlarmIds("bob", dimensions);

    assertEquals(result.size(), 0, "Alarm not found");
  }
}
