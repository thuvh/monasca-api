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

import java.util.List;
import java.util.Map;
import java.util.UUID;

import javax.inject.Inject;
import javax.inject.Named;
import javax.sql.DataSource;

import monasca.api.domain.exception.EntityExistsException;
import monasca.api.domain.exception.EntityNotFoundException;
import monasca.api.domain.model.notificationmethod.NotificationMethod;
import monasca.api.domain.model.notificationmethod.NotificationMethodRepo;
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

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;


/**
 * Notification method repository implementation.
 */
public class NotificationMethodJooqRepoImpl implements NotificationMethodRepo {
  private static final Logger LOG = LoggerFactory
      .getLogger(NotificationMethodJooqRepoImpl.class);

  private final DataSource ds;
  private final SQLDialect dialect;
  private final PersistUtils persistUtils;
  private final Settings settings;

  /**
   * Constructor.
   * @param ds - datasource
   * @param dialect - database dialect
   * @param persistUtils - helper
   */
  @Inject
  public NotificationMethodJooqRepoImpl(@Named("datasource") DataSource ds,
                                        @Named("dialect") SQLDialect dialect,
                                        PersistUtils persistUtils) {
    this.dialect = dialect;
    this.ds = ds;
    this.persistUtils = persistUtils;
    this.settings = new Settings().withRenderSchema(false);
  }

  @Override
  public NotificationMethod create(final String tenantId,
                                   final String name,
                                   final NotificationMethodType type,
                                   final String address) {

    DSLContext context = DSL.using(this.ds, this.dialect, this.settings);

    final NotificationMethod[] res = new NotificationMethod[1];

    context.transaction(new TransactionalRunnable() {
        @Override
        public void run(Configuration configuration) throws Exception {
          DSLContext create = DSL.using(configuration);
          if (getNotificationIdForTenantIdAndName(create, tenantId, name) != null) {
            throw new EntityExistsException("Notification method %s \"%s\" already exists.",
                                            tenantId,
                                            name);
          }

          String id = UUID.randomUUID().toString();

          monasca.common.jooq.tables.NotificationMethod nm = Tables.NOTIFICATION_METHOD;
          create.batch(create.insertInto(nm, nm.ID, nm.TENANT_ID, nm.NAME, nm.TYPE, nm.ADDRESS,
                                         nm.CREATED_AT, nm.UPDATED_AT
                                         )
                       .values(null, null, null, null,
                               null, DSL.currentTimestamp(), DSL.currentTimestamp()
                               )
                       ).bind(id, tenantId, name, type.toString(), address).execute();
          LOG.debug("Creating notification method {} for {}", name, tenantId);
          res[0] = new NotificationMethod(id, name, type, address);
        }
      });

    return res[0];
  }

  @Override
  public void deleteById(String tenantId, String notificationMethodId) {

    DSLContext context = DSL.using(this.ds, this.dialect, this.settings);

    monasca.common.jooq.tables.NotificationMethod nm = Tables.NOTIFICATION_METHOD.as("nm");

    int deletedRowCount = context.delete(nm)
        .where(nm.TENANT_ID.equal((Field<String>)null))
        .and(nm.ID.equal((Field<String>)null))
        .bind(1, tenantId)
        .bind(2, notificationMethodId).execute();

    if (deletedRowCount == 0) {
      throw new EntityNotFoundException("No notification method exists for %s",
                                        notificationMethodId);
    }
  }

  @Override
  public boolean exists(String tenantId, String notificationMethodId) {

    DSLContext context = DSL.using(this.ds, this.dialect, this.settings);

    monasca.common.jooq.tables.NotificationMethod nm = Tables.NOTIFICATION_METHOD.as("nm");

    return context.selectOne().whereExists(
                                           context.selectOne().from(nm)
                                           .where(nm.TENANT_ID.equal((Field<String>)null))
                                           .and(nm.ID.equal((Field<String>)null))
                                           )
      .bind(1, 1)
      .bind(2, 1)
      .bind(3, tenantId)
      .bind(4, notificationMethodId)
      .fetchOne() != null;
  }

  private String getNotificationIdForTenantIdAndName(DSLContext context,
                                                     String tenantId,
                                                     String name) {

    monasca.common.jooq.tables.NotificationMethod nm = Tables.NOTIFICATION_METHOD.as("nm");

    Record rec = context.select(nm.ID)
        .from(nm)
        .where(nm.TENANT_ID.equal((Field<String>)null))
        .and(nm.NAME.equal((Field<String>)null))
        .bind(1, tenantId)
        .bind(2, name)
        .fetchAny();

    if (rec != null) {
      return (String) rec.getValue("id");
    } else {
      return null;
    }
  }

  @Override
  public List<NotificationMethod> find(String tenantId, String offset, int limit) {

    DSLContext context = DSL.using(this.ds, this.dialect, this.settings);

    monasca.common.jooq.tables.NotificationMethod nm = Tables.NOTIFICATION_METHOD.as("nm");

    Select qq = context.select(nm.ID,
                               nm.TENANT_ID,
                               nm.NAME,
                               nm.TYPE,
                               nm.ADDRESS,
                               nm.CREATED_AT,
                               nm.UPDATED_AT)
        .from(nm)
        .where(nm.TENANT_ID.equal(DSL.param("tenantId", String.class)));

    if (offset != null) {
      qq = ((SelectConditionStep)qq).and(nm.ID.greaterThan(DSL.param("offset", String.class)));
    }

    qq = ((SelectOrderByStep)qq).orderBy(nm.ID.asc());

    if (limit > 0) {
      qq = ((SelectLimitStep)qq).limit(DSL.param("limit", Integer.class));
    }
    
    qq.bind("tenantId", tenantId);

    if (offset != null) {
      qq.bind("offset", offset);
    }

    if (limit > 0) {
      qq.bind("limit", limit + 1);
    }

    return qq.fetch().map(new NotificationMethodMapper());
  }

  @Override
  public NotificationMethod findById(String tenantId, String notificationMethodId) {

    DSLContext context = DSL.using(this.ds, this.dialect, this.settings);

    monasca.common.jooq.tables.NotificationMethod nm = Tables.NOTIFICATION_METHOD.as("nm");

    Record notificationMethodRec = context.select(nm.fields())
        .from(nm)
        .where(nm.TENANT_ID.equal((Field<String>)null))
        .and(nm.ID.equal((Field<String>)null))
        .bind(1, tenantId)
        .bind(2, notificationMethodId)
        .fetchAny();

    if (notificationMethodRec == null) {
      throw new EntityNotFoundException("No notification method exists for %s",
                                        notificationMethodId);
    }

    NotificationMethod notificationMethod =
        (NotificationMethod) notificationMethodRec.map(new NotificationMethodMapper());

    return notificationMethod;
  }

  @Override
  public NotificationMethod update(final String tenantId,
                                   final String notificationMethodId,
                                   final String name,
                                   final NotificationMethodType type,
                                   final String address) {


    DSLContext context = DSL.using(this.ds, this.dialect, this.settings);

    final NotificationMethod[] res = new NotificationMethod[1];

    context.transaction(new TransactionalRunnable() {
        @Override
        public void run(Configuration configuration) throws Exception {
          DSLContext create = DSL.using(configuration);
          String notificationId = getNotificationIdForTenantIdAndName(create, tenantId, name);

          if (notificationId != null && !notificationId.equalsIgnoreCase(notificationMethodId)) {
            throw new EntityExistsException("Notification method %s \"%s\" already exists.",
                                            tenantId, name);
          }

          monasca.common.jooq.tables.NotificationMethod nm = Tables.NOTIFICATION_METHOD.as("nm");
          int updatedRowCount = create.update(nm)
              .set(nm.NAME, DSL.param("name", String.class))
              .set(nm.TYPE, DSL.param("type", String.class))
              .set(nm.ADDRESS, DSL.param("address", String.class))
              .where(nm.TENANT_ID.equal(DSL.param("tenant_id", String.class)))
              .and(nm.ID.equal(DSL.param("id", String.class)))
              .bind("name", name)
              .bind("type", type.name())
              .bind("address", address)
              .bind("tenant_id", tenantId)
              .bind("id", notificationMethodId)
              .execute();

          if (updatedRowCount == 0) {
            throw new EntityNotFoundException("No notification method exists for %s",
                                              notificationMethodId);
          }

          res[0] = new NotificationMethod(notificationMethodId, name, type, address);
        }
      });

    return res[0];
  }

  private static class NotificationMethodMapper
      implements RecordMapper<Record, NotificationMethod> {

    @Override
    public NotificationMethod map(Record rec) {
      return new NotificationMethod((String)rec.getValue("id"), (String)rec.getValue("name"),
                                    NotificationMethodType.valueOf((String)rec.getValue("type")),
                                    (String)rec.getValue("address"));
    }
  }
}
