/*
 * Copyright (c) 2015 Hewlett-Packard Development Company, L.P.
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


import java.util.Iterator;
import java.util.List;
import java.util.Map;
import javax.inject.Named;
import javax.sql.DataSource;

import com.google.inject.Inject;

import monasca.api.infrastructure.persistence.DimensionQueries;
import monasca.api.infrastructure.persistence.Utils;
import monasca.common.jooq.Tables;

import org.jooq.Batch;
import org.jooq.BatchBindStep;
import org.jooq.Configuration;
import org.jooq.DSLContext;
import org.jooq.Field;
import org.jooq.Record;
import org.jooq.Record2;
import org.jooq.Record3;
import org.jooq.RecordMapper;
import org.jooq.Result;
import org.jooq.SQLDialect;
import org.jooq.Select;
import org.jooq.SelectConditionStep;
import org.jooq.SelectJoinStep;
import org.jooq.SelectLimitStep;
import org.jooq.SelectOnConditionStep;
import org.jooq.SelectOrderByStep;
import org.jooq.SelectWhereStep;
import org.jooq.Table;
import org.jooq.TransactionalRunnable;
import org.jooq.Update;
import org.jooq.UpdateSetFirstStep;
import org.jooq.UpdateWhereStep;
import org.jooq.impl.DSL;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;



public class JooqUtils extends Utils {

  private static final Logger logger =
      LoggerFactory.getLogger(JooqUtils.class);

  private final DataSource ds;
  private final SQLDialect dialect;

  @Inject
  public JooqUtils(@Named("datasource") DataSource ds, @Named("dialect") SQLDialect dialect) {
    this.dialect = dialect;
    this.ds = ds;
  }

  /**
   * Function for get all alarm ids for tenant and dimension.
   * @param tenantId - tenant
   * @param dimensions - dimensions
   * @return List - list of alarm id
   */
  public List<String> findAlarmIds(String tenantId,
                                   Map<String, String> dimensions) {

    DSLContext context = DSL.using(this.ds, this.dialect);

    monasca.common.jooq.tables.AlarmDefinition ad =
        Tables.ALARM_DEFINITION.as("ad");
    monasca.common.jooq.tables.Alarm at = Tables.ALARM.as("a");

    Select query = context.selectDistinct(at.ID)
        .from(at)
        .join(ad).on(at.ALARM_DEFINITION_ID.equal(ad.ID));

    query = buildJoinClauseFor(query, dimensions);

    query = ((SelectWhereStep)query)
      .where(ad.TENANT_ID.equal(DSL.param("tenantId", (Field<String>)null)))
      .and(ad.DELETED_AT.isNull())
      .orderBy(ad.CREATED_AT.asc());



    query.bind("tenantId", tenantId);

    logger.debug("jooq sql: {}", query);

    if (dimensions != null && !dimensions.isEmpty()) {
      int ind = 0;
      for (Iterator<Map.Entry<String, String>> it =
               dimensions.entrySet().iterator();
           it.hasNext();
           ind++) {
        Map.Entry<String, String> entry = it.next();
        query.bind("dname" + ind, entry.getKey());
        query.bind("dvalue" + ind, entry.getValue());
      }
    }

    return query.fetch().map(new StringRecordMapper());
  }

  private static class StringRecordMapper implements RecordMapper<Record, String> {
    @Override
    public String map(Record rec) {
      return (String)rec.getValue("id");
    }
  }

  private Select buildJoinClauseFor(Select query, Map<String, String> dimensions) {

    if ((dimensions == null) || dimensions.isEmpty()) {
      return query;
    }

    monasca.common.jooq.tables.Alarm at = Tables.ALARM.as("a");
    monasca.common.jooq.tables.AlarmMetric am = Tables.ALARM_METRIC.as("am");
    monasca.common.jooq.tables.MetricDefinitionDimensions mdd =
        Tables.METRIC_DEFINITION_DIMENSIONS.as("mdd");

    query = ((SelectJoinStep)query)
      .join(am).on(at.ID.equal(am.ALARM_ID))
      .join(mdd).on(am.METRIC_DEFINITION_DIMENSIONS_ID.equal(mdd.ID));

    for (int i = 0; i < dimensions.size(); i++) {
      final String tableAlias = "md" + i;
      monasca.common.jooq.tables.MetricDimension md = Tables.METRIC_DIMENSION.as(tableAlias);

      query = ((SelectJoinStep)query)
        .join(md).on(md.NAME.equal(DSL.param("dname", (Field<String>)null)))
        .and(md.VALUE.equal(DSL.param("dvalue", (Field<String>)null)))
        .and(mdd.METRIC_DIMENSION_SET_ID.equal(md.DIMENSION_SET_ID));
    }

    logger.debug("mysql dimension join clause: {}", query);

    return query;
  }
}
