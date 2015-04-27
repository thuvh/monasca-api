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

import org.hibernate.Query;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.inject.Inject;
import javax.inject.Named;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

import monasca.api.infrastructure.persistence.Utils;

public class HibernateUtils
    extends Utils {
  private static final Logger logger = LoggerFactory.getLogger(HibernateUtils.class);
  private static final String FIND_ALARM_IDS_SQL =
      "select distinct a.id, ad.created_at " +
      "from alarm as a " +
      "join alarm_definition as ad on a.alarm_definition_id = ad.id " +
      "%s " +
      "where ad.tenant_id = :tenantId and ad.deleted_at is NULL " +
      "order by ad.created_at";

  private final SessionFactory sessionFactory;

  @Inject
  public HibernateUtils(@Named("orm") SessionFactory sessionFactory) {
    this.sessionFactory = sessionFactory;
  }

  public List<String> findAlarmIds(String tenantId, Map<String, String> dimensions) {
    List<String> alarmIdList = new ArrayList<>();

    Session session = null;
    try {
      session = sessionFactory.openSession();

      final String sql = this.findAlarmQueryString(dimensions);
      final Query query = session.createSQLQuery(sql).setString("tenantId", tenantId);

      logger.debug("orm sql: {}", sql);

      this.bindDimensionsToQuery(query, dimensions);

      @SuppressWarnings("unchecked") List<Object[]> rows = query.list();
      for (Object[] row : rows) {
        String id = (String) row[0];
        alarmIdList.add(id);
      }

    } finally {
      if (session != null) {
        session.close();
      }
    }

    return alarmIdList;
  }

  private String findAlarmQueryString(final Map<String, String> dimensions) {
    return String.format(FIND_ALARM_IDS_SQL, this.buildJoinClauseFor(dimensions));
  }

  /*
  duplicate required
  monasca.api.infrastructure.persistence.DimensionQueries.bindDimensionsToQuery()
  has incompatible signature
   */
  private void bindDimensionsToQuery(Query query, Map<String, String> dimensions) {
    if (dimensions != null) {
      int i = 0;
      for (Iterator<Map.Entry<String, String>> it = dimensions.entrySet().iterator(); it.hasNext(); i++) {
        Map.Entry<String, String> entry = it.next();
        query.setString("dname" + i, entry.getKey());
        query.setString("dvalue" + i, entry.getValue());
      }
    }
  }
}
