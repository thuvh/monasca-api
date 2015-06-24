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

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

import javax.inject.Inject;
import javax.inject.Named;

import org.hibernate.Query;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class HibernateUtils {
  private static final Logger logger = LoggerFactory.getLogger(HibernateUtils.class);
  private final SessionFactory sessionFactory;

  @Inject
  public HibernateUtils(@Named("orm") SessionFactory sessionFactory) {
    this.sessionFactory = sessionFactory;
  }

  public List<String> findAlarmIds(String tenantId, Map<String, String> dimensions) {

    final String FIND_ALARM_IDS_SQL =
        "select distinct a.id, ad.created_at " + "from alarm as a " + "join alarm_definition as ad on a.alarm_definition_id = ad.id " + "%s "
            + "where ad.tenant_id = :tenantId and ad.deleted_at is NULL " + "order by ad.created_at";

    List<String> alarmIdList = new ArrayList<String>();

    Session session = null;
    try {
      session = sessionFactory.openSession();

      final String sql = String.format(FIND_ALARM_IDS_SQL, buildJoinClauseFor(dimensions));

      Query query = session.createSQLQuery(sql).setString("tenantId", tenantId);

      logger.debug("mysql sql: {}", sql);

      bindDimensionsToQuery(query, dimensions);

      List<Object[]> rows = query.list();
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

  private String buildJoinClauseFor(Map<String, String> dimensions) {

    if ((dimensions == null) || dimensions.isEmpty()) {
      return "";
    }

    final StringBuilder sb =
        new StringBuilder("join alarm_metric as am on a.id=am.alarm_id "
            + "join metric_definition_dimensions as mdd on am.metric_definition_dimensions_id=mdd.id ");

    for (int i = 0; i < dimensions.size(); i++) {

      final String tableAlias = "md" + i;

      sb.append(" inner join metric_dimension ").append(tableAlias).append(" on ").append(tableAlias).append(".name = :dname").append(i)
          .append(" and ").append(tableAlias).append(".value = :dvalue").append(i).append(" and mdd.metric_dimension_set_id = ").append(tableAlias)
          .append(".dimension_set_id");
    }

    logger.debug("mysql dimension join clause: {}", sb.toString());

    return sb.toString();
  }

  private static void bindDimensionsToQuery(Query query, Map<String, String> dimensions) {
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
