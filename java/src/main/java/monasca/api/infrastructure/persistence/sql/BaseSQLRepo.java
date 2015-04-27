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
 *
 */

package monasca.api.infrastructure.persistence.sql;

import org.hibernate.SessionFactory;
import org.hibernate.Transaction;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Abstract foundation for ORM repositories.
 */
abstract class BaseSQLRepo {
  private static final Logger LOG = LoggerFactory.getLogger(BaseSQLRepo.class);
  protected final SessionFactory sessionFactory;

  protected BaseSQLRepo(final SessionFactory sessionFactory) {
    this.sessionFactory = sessionFactory;
  }

  /**
   * Rollbacks passed {@code tx} transaction if such is not null.
   * Assumption is being made that {@code tx} being null means transaction
   * has been successfully comitted.
   *
   * @param tx {@link Transaction} object
   */
  protected void rollbackIfNotNull(final Transaction tx) {
    if (tx != null) {
      try {
        tx.rollback();
      } catch (RuntimeException rbe) {
        LOG.error("Couldn’t roll back transaction", rbe);
      }
    }
  }

}
