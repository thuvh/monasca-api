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
import static org.testng.Assert.assertFalse;
import static org.testng.Assert.assertTrue;
import static org.testng.Assert.fail;

import java.nio.charset.Charset;
import java.util.Arrays;
import java.util.List;
import javax.sql.DataSource;

import com.google.common.io.Resources;

import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import monasca.api.domain.exception.EntityExistsException;
import monasca.api.domain.exception.EntityNotFoundException;
import monasca.api.domain.model.notificationmethod.NotificationMethod;
import monasca.api.domain.model.notificationmethod.NotificationMethodType;
import monasca.api.infrastructure.persistence.PersistUtils;
import monasca.common.jooq.Tables;

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
public class NotificationMethodJooqRepositoryImplTest {
  private DBI db;
  private Handle handle;
  private NotificationMethodJooqRepoImpl repo;
  private DataSource ds;
  private SQLDialect dialect;
  private Settings settings;

  @BeforeClass
  protected void beforeClass() throws Exception {

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

    repo = new NotificationMethodJooqRepoImpl(ds, dialect, new PersistUtils());
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


    context.transaction(new TransactionalRunnable() {
        @Override
        public void run(Configuration configuration) throws Exception {
          DSLContext create = DSL.using(configuration);

          //          create.delete(aa).execute();
          create.delete(nm).execute();

          create.batch(create.insertInto(nm, nm.ID, nm.TENANT_ID, nm.NAME, nm.TYPE, nm.ADDRESS,
                                         nm.CREATED_AT, nm.UPDATED_AT
                                         )
                       .values(null, null, null, null,
                               null, DSL.currentTimestamp(), DSL.currentTimestamp()
                               )
                       )
            .bind("123", "444", "MyEmail", "EMAIL", "a@b")
            .bind("124", "444", "OtherEmail", "EMAIL", "a@b")
            .execute();
        }
      });
  }

  @Test(groups = "jooq")
  public void shouldCreate() {
    NotificationMethod nmA = repo.create("555", "MyEmail", NotificationMethodType.EMAIL, "a@b");
    NotificationMethod nmB = repo.findById("555", nmA.getId());

    assertEquals(nmA, nmB);
  }

  @Test(groups = "jooq")
  public void shouldExistForTenantAndNotificationMethod() {
    assertTrue(repo.exists("444", "123"));
    assertFalse(repo.exists("444", "1234"));
    assertFalse(repo.exists("333", "123"));
  }

  @Test(groups = "jooq")
  public void shouldFindById() {
    NotificationMethod nm = repo.findById("444", "123");

    assertEquals(nm.getId(), "123");
    assertEquals(nm.getType(), NotificationMethodType.EMAIL);
    assertEquals(nm.getAddress(), "a@b");
  }

  @Test(groups = "jooq")
  public void shouldFind() {
    List<NotificationMethod> nms = repo.find("444", null, 1);

    assertEquals(nms, Arrays.asList(new NotificationMethod("123",
                                                           "MyEmail",
                                                           NotificationMethodType.EMAIL,
                                                           "a@b"),
                                    new NotificationMethod("124",
                                                           "OtherEmail",
                                                           NotificationMethodType.EMAIL,
                                                           "a@b"
                                                           )
                                    )
                 );
  }

  @Test(groups = "jooq")
  public void shouldUpdate() {
    repo.update("444", "123", "Foo", NotificationMethodType.EMAIL, "abc");
    NotificationMethod nm = repo.findById("444", "123");

    assertEquals(nm, new NotificationMethod("123", "Foo", NotificationMethodType.EMAIL, "abc"));
  }

  @Test(groups = "jooq")
  public void shouldDeleteById() {
    repo.deleteById("444", "123");

    try {
      repo.findById("444", "123");
      fail();
    } catch (EntityNotFoundException expected) {
    }
  }

  @Test(groups = "jooq")
  public void shouldUpdateDuplicateWithSameValues() {
    repo.update("444", "123", "Foo", NotificationMethodType.EMAIL, "abc");
    NotificationMethod nm = repo.findById("444", "123");

    assertEquals(nm, new NotificationMethod("123", "Foo", NotificationMethodType.EMAIL, "abc"));
  }

  @Test(groups = "jooq", expectedExceptions = EntityExistsException.class)
  public void shouldNotUpdateDuplicateWithSameName() {

    repo.update("444", "124", "MyEmail", NotificationMethodType.EMAIL, "abc");
  }

}
