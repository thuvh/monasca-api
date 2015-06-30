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

import monasca.api.domain.exception.EntityExistsException;
import monasca.api.domain.exception.EntityNotFoundException;
import monasca.api.domain.model.notificationmethod.NotificationMethod;
import monasca.api.domain.model.notificationmethod.NotificationMethodRepo;
import monasca.api.domain.model.notificationmethod.NotificationMethodType;
import monasca.common.hibernate.db.NotificationMethodDb;
import monasca.common.model.alarm.AlarmNotificationMethodType;
import org.hibernate.Query;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.joda.time.DateTime;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.inject.Inject;
import javax.inject.Named;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * Notification method repository implementation.
 */
public class NotificationMethodSqlRepoImpl implements NotificationMethodRepo {
  private static final Logger LOG = LoggerFactory.getLogger(NotificationMethodSqlRepoImpl.class);
  private final SessionFactory sessionFactory;

  @Inject
  public NotificationMethodSqlRepoImpl(@Named("orm")SessionFactory sessionFactory) {
    this.sessionFactory = sessionFactory;
  }

  @Override
  public NotificationMethod create(String tenantId, String name, NotificationMethodType type,
      String address) {
    Transaction tx = null;
    Session session = null;
    try {
      session = sessionFactory.openSession();
      tx = session.beginTransaction();

      if (getNotificationIdForTenantIdAndName(session, tenantId, name) != null) {
        throw new EntityExistsException("Notification method %s \"%s\" already exists.", tenantId,
            name);
      }

      final String id = UUID.randomUUID().toString();
      final DateTime now = DateTime.now();
      final NotificationMethodDb db = new NotificationMethodDb(
          id,
          tenantId,
          name,
          AlarmNotificationMethodType.valueOf(type.name()),
          address,
          now,
          now
      );
      session.save(db);

      LOG.debug("Creating notification method {} for {}", name, tenantId);
      tx.commit();
      tx = null;

      return this.convertToNotificationMethod(db);
    } finally {
      this.rollbackIfNotNull(tx);
      if (session != null) {
        session.close();
      }
    }
  }

  @Override
  public void deleteById(String tenantId, String notificationMethodId) {
    Session session = null;
    Transaction tx = null;
    try {
      if (!exists(tenantId, notificationMethodId)) {
        throw new EntityNotFoundException("No notification exists for %s", notificationMethodId);
      }
      session = sessionFactory.openSession();
      tx = session.beginTransaction();

      // delete notification
      session.createQuery("delete from NotificationMethodDb where id = :id")
          .setString("id", notificationMethodId)
          .executeUpdate();

      tx.commit();
      tx = null;
    } finally {
      this.rollbackIfNotNull(tx);
      if (session != null) {
        session.close();
      }
    }
  }

  @Override
  public boolean exists(String tenantId, String notificationMethodId) {
    Session session = null;
    try {
      session = sessionFactory.openSession();

      NotificationMethodDb result =
          (NotificationMethodDb) session
              .createQuery(
                  "from NotificationMethodDb where tenant_id = :tenantId and id = :notificationMethodId")
              .setString("tenantId", tenantId)
              .setString("notificationMethodId", notificationMethodId)
              .uniqueResult();

      return result != null;
    } finally {
      if (session != null) {
        session.close();
      }
    }
  }

  @Override
  public NotificationMethod findById(String tenantId, String notificationMethodId) {
    Session session = null;
    try {
      session = sessionFactory.openSession();

      NotificationMethodDb result =
          (NotificationMethodDb) session
              .createQuery(
                  "from NotificationMethodDb where tenant_id = :tenantId and id = :notificationMethodId")
              .setString("tenantId", tenantId)
              .setString("notificationMethodId", notificationMethodId)
              .uniqueResult();

      if (result == null) {
        throw new EntityNotFoundException("No notification method exists for %s",
            notificationMethodId);
      }

      return this.convertToNotificationMethod(result);
    } finally {
      if (session != null) {
        session.close();
      }
    }
  }

  @Override
  public NotificationMethod update(String tenantId, String notificationMethodId, String name,
      NotificationMethodType type, String address) {
    Session session = null;
    Transaction tx = null;
    try {
      session = sessionFactory.openSession();
      NotificationMethodDb result =
          (NotificationMethodDb) session
              .createQuery("from NotificationMethodDb where tenant_id = :tenantId and name = :name")
              .setString("tenantId", tenantId).setString("name", name).uniqueResult();

      if (result != null && !result.getId().equalsIgnoreCase(notificationMethodId)) {
        throw new EntityExistsException("Notification method %s \"%s\" already exists.", tenantId,
            name);
      }

      tx = session.beginTransaction();

      NotificationMethodDb db;
      if ((db = (NotificationMethodDb) session.get(NotificationMethodDb.class, notificationMethodId)) == null) {
        throw new EntityNotFoundException("No notification method exists for %s",
            notificationMethodId);
      }
      db.setName(name);
      db.setType(AlarmNotificationMethodType.valueOf(type.name()));
      db.setAddress(address);

      session.save(db);
      tx.commit();
      tx = null;

      return this.convertToNotificationMethod(db);

    } finally {
      this.rollbackIfNotNull(tx);
      if (session != null) {
        session.close();
      }
    }
  }

  @Override
  @SuppressWarnings("unchecked")
  public List<NotificationMethod> find(String tenantId, String offset, int limit) {
    Session session = null;
    List<NotificationMethodDb> resultList;
    List<NotificationMethod> notificationList = new ArrayList<>();
    final String rawQuery =
        "from NotificationMethodDb where tenant_id = :tenantId %1$s order by id";
    try {
      session = sessionFactory.openSession();

      String offsetPart = "";
      if (offset != null) {
        offsetPart = "and id > '" + offset + "'";
      }
      String queryHql = String.format(rawQuery, offsetPart);

      Query query = session.createQuery(queryHql).setString("tenantId", tenantId);

      if (limit > 0) {
        query.setMaxResults(limit + 1);
      }

      resultList = query.list();

      if (resultList == null || resultList.isEmpty()) {
        return notificationList;
      }

      for (NotificationMethodDb item : resultList) {
        notificationList.add(this.convertToNotificationMethod(item));
      }

      return notificationList;

    } finally {
      if (session != null) {
        session.close();
      }
    }
  }

  protected NotificationMethodDb getNotificationIdForTenantIdAndName(final Session session,
                                                                     final String tenantId,
                                                                     final String name) {
    return (NotificationMethodDb) session
        .createQuery("from NotificationMethodDb where tenant_id = :tenantId and name = :name")
        .setString("tenantId", tenantId)
        .setString("name", name)
        .uniqueResult();
  }

  protected void rollbackIfNotNull(final Transaction tx) {
    if (tx != null) {
      try {
        tx.rollback();
      } catch (RuntimeException rbe) {
        LOG.error("Couldn’t roll back transaction", rbe);
      }
    }
  }

  protected NotificationMethod convertToNotificationMethod(final NotificationMethodDb db) {
    if (db == null) {
      return null;
    }
    return new NotificationMethod(
        db.getId(),
        db.getName(),
        NotificationMethodType.valueOf(db.getType().name()),
        db.getAddress()
    );
  }
}
