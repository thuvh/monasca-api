/*
 * Copyright 2015 FUJITSU LIMITED
 * Copyright 2016 Hewlett Packard Enterprise Development Company, L.P.
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
package monasca.api.infrastructure.persistence.hibernate;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Set;

import javax.annotation.Nullable;
import javax.inject.Inject;
import javax.inject.Named;

import com.google.common.base.Function;
import com.google.common.base.Splitter;
import com.google.common.base.Strings;
import com.google.common.collect.FluentIterable;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;

import com.google.common.collect.Sets;
import com.google.common.util.concurrent.ExecutionError;
import monasca.common.hibernate.db.AlarmMetricDb;
import monasca.common.hibernate.db.AlarmMetricId;
import monasca.common.hibernate.db.MetricDefinitionDb;
import monasca.common.hibernate.db.MetricDefinitionDimensionsDb;
import monasca.common.hibernate.db.MetricDimensionDb;
import monasca.common.hibernate.db.SubAlarmDefinitionDb;
import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.collections4.MapUtils;
import org.apache.commons.lang3.StringUtils;
import org.hibernate.CacheMode;
import org.hibernate.Criteria;
import org.hibernate.FetchMode;
import org.hibernate.LockMode;
import org.hibernate.Query;
import org.hibernate.Session;
import org.hibernate.SessionFactory;
import org.hibernate.StatelessSession;
import org.hibernate.Transaction;
import org.hibernate.criterion.Conjunction;
import org.hibernate.criterion.Criterion;
import org.hibernate.criterion.DetachedCriteria;
import org.hibernate.criterion.Disjunction;
import org.hibernate.criterion.Junction;
import org.hibernate.criterion.Order;
import org.hibernate.criterion.Projections;
import org.hibernate.criterion.Property;
import org.hibernate.criterion.Restrictions;
import org.hibernate.criterion.SimpleExpression;
import org.hibernate.sql.JoinType;
import org.hibernate.transform.BasicTransformerAdapter;
import org.hibernate.transform.ResultTransformer;
import org.hibernate.transform.Transformers;
import org.joda.time.DateTime;
import org.joda.time.DateTimeZone;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import monasca.api.domain.exception.EntityNotFoundException;
import monasca.api.domain.model.alarm.Alarm;
import monasca.api.domain.model.alarm.AlarmCount;
import monasca.api.domain.model.alarm.AlarmRepo;
import monasca.api.resource.exception.Exceptions;
import monasca.common.hibernate.db.AlarmDb;
import monasca.common.hibernate.db.SubAlarmDb;
import monasca.common.hibernate.type.BinaryId;
import monasca.common.model.alarm.AlarmSeverity;
import monasca.common.model.alarm.AlarmState;
import monasca.common.model.alarm.AlarmSubExpression;
import monasca.common.model.metric.MetricDefinition;
import monasca.common.util.Conversions;

/**
 * Alarmed metric repository implementation.
 */
public class AlarmSqlRepoImpl
    extends BaseSqlRepo
    implements AlarmRepo {

  private static final Logger logger = LoggerFactory.getLogger(AlarmSqlRepoImpl.class);

  private static final String FIND_ALARM_BY_ID_SQL =
      "select distinct ad.id as alarm_definition_id, ad.severity, ad.name as alarm_definition_name, "
          + "a.id, a.state, a.updatedAt, a.createdAt as created_timestamp, "
          + "md.name as metric_name, mdg.id.name, mdg.value, a.lifecycleState, a.link, a.stateUpdatedAt, "
          + "mdg.id.dimensionSetId from AlarmDb as a "
          + ", AlarmDefinitionDb as ad "
          + ", AlarmMetricDb as am "
          + ", MetricDefinitionDimensionsDb as mdd "
          + ", MetricDefinitionDb as md "
          + ", MetricDimensionDb as mdg "
          + "where "
          + " ad.id = a.alarmDefinition.id "
          + " and am.alarmMetricId.alarm.id = a.id "
          + " and mdd.id = am.alarmMetricId.metricDefinitionDimensions.id "
          + " and md.id = mdd.metricDefinition.id "
          + " and mdg.id.dimensionSetId = mdd.metricDimensionSetId "
          + " and ad.tenantId = :tenantId "
          + " %s "
          + " and ad.deletedAt is null order by a.id, mdg.id.dimensionSetId %s";

  private static final String FIND_ALARMS_SQL =
      "select ad.id as alarm_definition_id, ad.severity, ad.name as alarm_definition_name, "
          + "a.id, a.state, a.updated_at as updated_timestamp, a.created_at as created_timestamp, "
          + "md.name as metric_name, mdg.name, mdg.value, a.lifecycle_state, a.link, a.state_updated_at as state_updated_timestamp, "
          + "mdg.dimension_set_id "
          + "from alarm as a "
          + "inner join %s as alarm_id_list on alarm_id_list.id = a.id "
          + "inner join alarm_definition ad on ad.id = a.alarm_definition_id "
          + "inner join alarm_metric as am on am.alarm_id = a.id "
          + "inner join metric_definition_dimensions as mdd on mdd.id = am.metric_definition_dimensions_id "
          + "inner join metric_definition as md on md.id = mdd.metric_definition_id "
          + "left outer join (select dimension_set_id, name, value "
          + "from metric_dimension group by dimension_set_id, name, value) as mdg on mdg.dimension_set_id = mdd.metric_dimension_set_id "
          + "order by a.id ASC";

  @Inject
  public AlarmSqlRepoImpl(@Named("orm") SessionFactory sessionFactory) {
    super(sessionFactory);
  }

  @Override
  public void deleteById(String tenantId, String id) {
    logger.trace(ORM_LOG_MARKER, "deleteById(...) entering");

    Transaction tx = null;
    Session session = null;
    try {
      session = sessionFactory.openSession();
      tx = session.beginTransaction();

      final long result = (Long) session
          .createCriteria(AlarmDb.class, "a")
          .createAlias("alarmDefinition", "ad")
          .add(Restrictions.conjunction(
              Restrictions.eq("a.id", id),
              Restrictions.eq("ad.tenantId", tenantId),
              Restrictions.eqProperty("a.alarmDefinition.id", "ad.id"),
              Restrictions.isNull("ad.deletedAt")
          ))
          .setProjection(Projections.count("a.id"))
          .setReadOnly(true)
          .uniqueResult();

      // This will throw an EntityNotFoundException if Alarm doesn't exist or has a different tenant
      // id
      if (result < 1) {
        throw new EntityNotFoundException("No alarm exists for %s", id);
      }

      // delete alarm
      session
          .getNamedQuery(AlarmDb.Queries.DELETE_BY_ID)
          .setString("id", id)
          .executeUpdate();

      tx.commit();
      tx = null;
    } catch (Exception e) {
      this.rollbackIfNotNull(tx);
      throw e;
    } finally {
      if (session != null) {
        session.close();
      }
    }

  }

  @Override
  public List<Alarm> find(final String tenantId,
                          final String alarmDefId,
                          final String metricName,
                          final Map<String, String> metricDimensions,
                          final AlarmState state,
                          final AlarmSeverity severity,
                          final String lifecycleState,
                          final String link,
                          final DateTime stateUpdatedStart,
                          final List<String> sortBy,
                          final String offset,
                          final int limit,
                          final boolean enforceLimit) {
    logger.trace(ORM_LOG_MARKER, "find(...) entering");
    if (sortBy != null && !sortBy.isEmpty()) {
      throw Exceptions.unprocessableEntity(
          "Sort_by is not implemented for the hibernate database type");
    }

    List<Alarm> alarms = new Function<String, List<Alarm>>() {

      @Nullable
      @Override
      public List<Alarm> apply(@Nullable final String input) {
        Session session = null;
        final Map<AlarmDb, Alarm> alarms;

        try {
          session = sessionFactory.openSession();

          final Criteria criteria = session
              .createCriteria(AlarmDb.class, "a")
              .createAlias("a.alarmDefinition", "ad", JoinType.INNER_JOIN)
              .createAlias("a.alarmMetrics", "am", JoinType.INNER_JOIN)
              .add(Restrictions.isNull("ad.deletedAt"))
              .addOrder(Order.asc("a.id"))
              .setCacheable(true)
              .setCacheMode(CacheMode.GET)
              .setReadOnly(true)
              .setLockMode(LockMode.READ)
              .setResultTransformer(Criteria.DISTINCT_ROOT_ENTITY);

          if (enforceLimit && limit > 0) {
            criteria.setMaxResults(limit);
          }
          if (StringUtils.isNotEmpty(offset)) {
            final int intOffset = Integer.parseInt(offset);
            criteria.setFirstResult(intOffset);
          }

          if (StringUtils.isNotEmpty(alarmDefId)) {
            criteria.add(Restrictions.eq("ad.id", alarmDefId));
          }
          if (StringUtils.isNotEmpty(tenantId)) {
            criteria.add(Restrictions.eq("ad.tenantId", tenantId));
          }
          if (StringUtils.isNotEmpty(lifecycleState)) {
            criteria.add(Restrictions.eq("a.lifecycleState", lifecycleState));
          }
          if (StringUtils.isNotEmpty(link)) {
            criteria.add(Restrictions.eq("a.link", link));
          }
          if (StringUtils.isNotEmpty(metricName)) {
            final DetachedCriteria mdd = DetachedCriteria
                .forClass(MetricDefinitionDimensionsDb.class, "mdd")
                .createAlias("mdd.metricDefinition", "md", JoinType.INNER_JOIN)
                .add(Restrictions.eq("md.name", metricName))
                .add(Restrictions.eq("md.tenantId", tenantId))
                .add(Restrictions.eqProperty("mdd.metricDefinition.id", "md.id"))
                .addOrder(Order.asc("mdd.id"))
                .setProjection(Projections.alias(Projections.distinct(Projections.id()), "md"));

            if (MapUtils.isNotEmpty(metricDimensions)) {
              mdd.add(
                  Property
                      .forName("mdd.metricDimensionSetId")
                      .in(getDimensionSubCriteria(metricDimensions))
              );
            }

            // TODO(trebskit) check if it possible to reference upper criteria from here
            final DetachedCriteria subAlarms = DetachedCriteria
                .forClass(AlarmMetricDb.class, "sub_am")
                .add(Property.forName("sub_am.alarmMetricId.metricDefinitionDimensions.id").in(mdd))
                .setProjection(Projections.distinct(Projections.property("sub_am.alarmMetricId.alarm.id")));

            criteria
                .add(Property.forName("a.id").in(subAlarms))
                .add(Restrictions.eqProperty("a.id", "am.alarmMetricId.alarm.id"));

          } else if (MapUtils.isNotEmpty(metricDimensions)) {
            criteria.add(
                Property
                    .forName("a.id")
                    .in(
                        DetachedCriteria
                            .forClass(AlarmMetricDb.class, "sub_am")
                            .add(Property.forName("mdd.metricDimensionSetId").in(getDimensionSubCriteria(metricDimensions)))
                            .setProjection(Projections.distinct(Projections.property("sub_am.alarmMetricId.alarm.id")))
                    )
            );
          }
          if (state != null) {
            criteria.add(Restrictions.eq("a.state", severity));
          }
          if (severity != null) {
            criteria.add(Restrictions.eq("a.severity", severity));
          }
          if (stateUpdatedStart != null) {
            criteria.add(Restrictions.ge("a.stateUpdatedAt", stateUpdatedStart));
          }

          final List<?> rows = criteria.list();
          if (rows.isEmpty()) {
            return Collections.emptyList();
          }

          alarms = Maps.newLinkedHashMap();

          for (final Object row : rows) {
            final AlarmDb alarmDb = (AlarmDb) row;

            alarms.put(alarmDb, new Function<AlarmDb, Alarm>() {

              @Nullable
              @Override
              public Alarm apply(@Nullable final AlarmDb input) {
                assert input != null;

                final Alarm alarm = new Alarm();

                alarm.setId(input.getId());
                alarm.setCreatedTimestamp(input.getCreatedAt());
                alarm.setUpdatedTimestamp(input.getUpdatedAt());
                alarm.setLifecycleState(input.getLifecycleState());
                alarm.setLink(input.getLink());
                alarm.setState(input.getState());
                alarm.setStateUpdatedTimestamp(input.getStateUpdatedAt());
                alarm.setAlarmDefinition(
                    new Alarm.AlarmDefinitionShort(
                        input.getAlarmDefinition().getId(),
                        input.getAlarmDefinition().getName(),
                        input.getAlarmDefinition().getSeverity().name()
                    )
                );

                return alarm;
              }

            }.apply(alarmDb));

          }

          // finish collecting dimensions
          // has to be done using yet another query, however it optimized
          // to get all dimensions at once for all alarms found
          final Criteria dimCriteria = session
              .createCriteria(MetricDimensionDb.class, "md")
              .setProjection(
                  Projections.projectionList()
                      .add(Projections.property("md.id.name"))
                      .add(Projections.property("md.value"))
                      .add(Projections.property("md.id.dimensionSetId"))
              )
              .addOrder(Order.asc("md.id.name"))
              .setReadOnly(true)
              .setCacheable(true)
              .add(Property.forName("md.id.dimensionSetId").in(
                  FluentIterable
                      .from(rows)
                      .transformAndConcat(new Function<Object, Collection<BinaryId>>() {
                        @Nullable
                        @Override
                        public Collection<BinaryId> apply(@Nullable final Object input) {
                          assert input != null;
                          final AlarmDb alarmDb = (AlarmDb) input;
                          final Collection<AlarmMetricDb> metrics = alarmDb.getAlarmMetrics();
                          final Collection<BinaryId> ids = Sets.newHashSetWithExpectedSize(metrics.size());
                          for (final AlarmMetricDb amDB : metrics) {
                            final AlarmMetricId am = amDB.getAlarmMetricId();
                            final MetricDefinitionDimensionsDb mdd = am.getMetricDefinitionDimensions();
                            final BinaryId metricDimensionSetId = mdd.getMetricDimensionSetId();
                            ids.add(metricDimensionSetId);
                          }
                          return ids;
                        }
                      })
                      .toList()
              ));

          // transform to map using dimensionSetId as key
          final List<Object[]> dimensionDbList = dimCriteria.list();
          final Map<BinaryId, Map<String, String>> dimensions = Maps.newHashMapWithExpectedSize(dimensionDbList.size());
          for (final Object[] item : dimensionDbList) {
            final String name = String.valueOf(item[0]);
            final String value = String.valueOf(item[1]);
            final BinaryId dimensionSetId = (BinaryId) item[2];

            Map<String, String> dims = dimensions.get(dimensionSetId);
            if (dims == null) {
              dims = Maps.newHashMapWithExpectedSize(10);
              dimensions.put(dimensionSetId, dims);
            }

            dims.put(name, value);
          }

          // put dimensions into alarms using dimensionSetId as key
          for (final AlarmDb alarmDb : alarms.keySet()) {
            final Alarm alarm = alarms.get(alarmDb);
            alarm.setMetrics(
                FluentIterable
                    .from(alarmDb.getAlarmMetrics())
                    .transform(new Function<AlarmMetricDb, MetricDefinition>() {
                      @Nullable
                      @Override
                      public MetricDefinition apply(@Nullable final AlarmMetricDb input) {
                        assert input != null;

                        final AlarmMetricId am = input.getAlarmMetricId();
                        final MetricDefinitionDimensionsDb mdd = am.getMetricDefinitionDimensions();
                        final MetricDefinitionDb md = mdd.getMetricDefinition();
                        final BinaryId metricDimensionSetId = mdd.getMetricDimensionSetId();

                        final Map<String, String> localDims = dimensions.get(metricDimensionSetId);

                        return new MetricDefinition(md.getName(), localDims);
                      }
                    })
                    .toList()
            );
          }

          session.close();
          session = null;

          return Lists.newArrayList(alarms.values());
        } catch (Exception e) {
          logger.error(ORM_LOG_MARKER, "lol", e);
        } finally {
          if (session != null) {
            session.close();
          }
        }

        return Collections.emptyList();

      }


    }.apply(tenantId);

    if (limit == 0 || !enforceLimit) {
      return alarms;
    } else if (alarms.size() > limit) {
      for (int i = alarms.size() - 1; i > limit; i--) {
        alarms.remove(i);
      }
    }

    return alarms;
  }

  private DetachedCriteria getDimensionSubCriteria(final Map<String, String> metricDimensions) {
    final Junction perDimKeyOr = Restrictions.or();
    final DetachedCriteria mDims = DetachedCriteria
        .forClass(MetricDimensionDb.class, "m_dims")
        .add(perDimKeyOr)
        .setProjection(Projections.distinct(Projections.property("m_dims.id.dimensionSetId")));

    for (final String dimKey : metricDimensions.keySet()) {
      final Junction dimKeyToValues = Restrictions.and(Restrictions.eq("m_dims.id.name", dimKey));
      final String dimValue = metricDimensions.get(dimKey);

      if (StringUtils.isNotEmpty(dimValue)) {
        final Disjunction or = Restrictions.or();
        final List<String> values = Splitter.on('|').splitToList(dimValue);
        for (final String value : values) {
          or.add(Restrictions.eq("m_dims.value", value));
        }
        dimKeyToValues.add(or);
      }

      perDimKeyOr.add(dimKeyToValues);
    }

    return mDims;
  }

  private List<Alarm> findInternal(String tenantId, String alarmDefId, String metricName,
                                   Map<String, String> metricDimensions, AlarmState state,
                                   String lifecycleState, String link, DateTime stateUpdatedStart,
                                   String offset, int limit, boolean enforceLimit) {
    Session session = null;

    List<Alarm> alarms = new LinkedList<>();

    try {
      Query query;
      session = sessionFactory.openSession();


      StringBuilder
          sbWhere =
          new StringBuilder("(select a.id "
              + "from alarm as a, alarm_definition as ad "
              + "where ad.id = a.alarm_definition_id "
              + "  and ad.deleted_at is null "
              + "  and ad.tenant_id = :tenantId ");

      if (alarmDefId != null) {
        sbWhere.append(" and ad.id = :alarmDefId ");
      }

      if (metricName != null) {

        sbWhere.append(" and a.id in (select distinct a.id from alarm as a "
            + "inner join alarm_metric as am on am.alarm_id = a.id "
            + "inner join metric_definition_dimensions as mdd "
            + "  on mdd.id = am.metric_definition_dimensions_id "
            + "inner join (select distinct id from metric_definition "
            + "            where name = :metricName) as md "
            + "  on md.id = mdd.metric_definition_id ");

        buildJoinClauseFor(metricDimensions, sbWhere);

        sbWhere.append(")");

      } else if (metricDimensions != null) {

        sbWhere.append(" and a.id in (select distinct a.id from alarm as a "
            + "inner join alarm_metric as am on am.alarm_id = a.id "
            + "inner join metric_definition_dimensions as mdd "
            + "  on mdd.id = am.metric_definition_dimensions_id ");

        buildJoinClauseFor(metricDimensions, sbWhere);

        sbWhere.append(")");

      }

      if (state != null) {
        sbWhere.append(" and a.state = :state");
      }

      if (lifecycleState != null) {
        sbWhere.append(" and a.lifecycle_state = :lifecycleState");
      }

      if (link != null) {
        sbWhere.append(" and a.link = :link");
      }

      if (stateUpdatedStart != null) {
        sbWhere.append(" and a.state_updated_at >= :stateUpdatedStart");
      }

      sbWhere.append(" order by a.id ASC ");
      sbWhere.append(")");

      final String sql = String.format(FIND_ALARMS_SQL, sbWhere);

      try {
        query = session.createSQLQuery(sql);
        this.bindParameters(
            tenantId,
            alarmDefId,
            metricName,
            metricDimensions,
            state,
            lifecycleState,
            link,
            stateUpdatedStart,
            offset,
            limit,
            enforceLimit,
            query);
      } catch (Exception e) {
        logger.error("Failed to bind query {}, error is {}", sql, e.getMessage());
        throw new RuntimeException("Failed to bind query", e);
      }

      List<Object[]> alarmList = (List<Object[]>) query.list();
      alarms = this.createAlarms(alarmList);

    } finally {
      if (session != null) {
        session.close();
      }
    }
    return alarms;
  }

  private void bindParameters(final String tenantId,
                              final String alarmDefId,
                              final String metricName,
                              final Map<String, String> metricDimensions,
                              final AlarmState state,
                              final String lifecycleState,
                              final String link,
                              final DateTime stateUpdatedStart,
                              final String offset,
                              final int limit,
                              final boolean enforceLimit,
                              final Query query) {
    query.setString("tenantId", tenantId);
    if (alarmDefId != null) {
      query.setString("alarmDefId", alarmDefId);
    }
    if (metricName != null) {
      query.setString("metricName", metricName);
    }
    if (state != null) {
      query.setString("state", state.name());
    }
    if (link != null) {
      query.setString("link", link);
    }
    if (lifecycleState != null) {
      query.setString("lifecycleState", lifecycleState);
    }
    if (stateUpdatedStart != null) {
      query.setDate("stateUpdatedStart", stateUpdatedStart.toDateTime(DateTimeZone.UTC).toDate());
    }
    if (offset != null) {
      final int offsetInt = Integer.parseInt(offset);
      logger.debug(ORM_LOG_MARKER, "Offset for alarm query is {}", offsetInt);
      query.setFirstResult(offsetInt);
    }
    if (enforceLimit && limit > 0) {
      logger.debug(ORM_LOG_MARKER, "Limit for alarm query is {}", limit);
      query.setMaxResults(limit + 1);
    }
    this.bindDimensionsToQuery(query, metricDimensions);
  }

  private List<Alarm> createAlarms(List<Object[]> alarmList) {
    List<Alarm> alarms = Lists.newLinkedList();

    String previousAlarmId = null;
    BinaryId previousDimensionSetId = null;
    List<MetricDefinition> alarmedMetrics = null;
    Map<String, String> dimensionMap = new HashMap<>();

    for (Object[] alarmRow : alarmList) {
      String alarmDefinitionId = (String) alarmRow[0];
      AlarmSeverity severity = Conversions.variantToEnum(alarmRow[1], AlarmSeverity.class);
      AlarmState alarmState = Conversions.variantToEnum(alarmRow[4], AlarmState.class);
      DateTime updatedTimestamp = Conversions.variantToDateTime(alarmRow[5]);
      DateTime createdTimestamp = Conversions.variantToDateTime(alarmRow[6]);
      BinaryId dimensionSetId = this.convertBinaryId(alarmRow[13]);
      DateTime stateUpdatedTimestamp = Conversions.variantToDateTime(alarmRow[12]);

      String alarm_definition_name = (String) alarmRow[2];
      String id = (String) alarmRow[3];

      String lifecycle_state = (String) alarmRow[10];
      String link = (String) alarmRow[11];

      String metric_name = (String) alarmRow[7];
      String dimension_name = (String) alarmRow[8];
      String dimension_value = (String) alarmRow[9];

      if (!id.equals(previousAlarmId)) {
        alarmedMetrics = new ArrayList<>();
        dimensionMap = Maps.newHashMap();
        alarmedMetrics.add(new MetricDefinition(metric_name, dimensionMap));

        alarms.add(new Alarm(id, alarmDefinitionId, alarm_definition_name, severity.name(),
            alarmedMetrics, alarmState, lifecycle_state, link,
            stateUpdatedTimestamp, updatedTimestamp, createdTimestamp
        ));

        previousDimensionSetId = dimensionSetId;
      }

      if (!dimensionSetId.equals(previousDimensionSetId)) {
        dimensionMap = Maps.newHashMap();
        alarmedMetrics.add(new MetricDefinition(metric_name, dimensionMap));
      }

      dimensionMap.put(dimension_name, dimension_value);

      previousDimensionSetId = dimensionSetId;
      previousAlarmId = id;
    }
    return alarms;
  }

  private BinaryId convertBinaryId(final Object o) {
    final BinaryId dimensionSetId;
    if (o instanceof BinaryId) {
      dimensionSetId = (BinaryId) o;
    } else {
      dimensionSetId = new BinaryId((byte[]) o);
    }
    return dimensionSetId;
  }

  private void bindDimensionsToQuery(
      Query query,
      Map<String, String> dimensions) {

    if (dimensions != null) {
      int i = 0;
      for (Iterator<Map.Entry<String, String>> it = dimensions.entrySet().iterator(); it.hasNext(); i++) {
        Map.Entry<String, String> entry = it.next();
        query.setString("dname" + i, entry.getKey());
        query.setString("dvalue" + i, entry.getValue());
      }
    }
  }

  private void buildJoinClauseFor(Map<String, String> dimensions, StringBuilder sbJoin) {
    if (dimensions == null) {
      return;
    }
    for (int i = 0; i < dimensions.size(); i++) {
      final String indexStr = String.valueOf(i);
      sbJoin.append(" inner join metric_dimension md").append(indexStr).append(" on md")
          .append(indexStr)
          .append(".name = :dname").append(indexStr).append(" and md").append(indexStr)
          .append(".value = :dvalue").append(indexStr)
          .append(" and mdd.metric_dimension_set_id = md")
          .append(indexStr).append(".dimension_set_id");
    }
  }

  @Override
  @SuppressWarnings("unchecked")
  public Alarm findById(String tenantId, String id) {
    logger.trace(ORM_LOG_MARKER, "findById(...) entering");

    Session session = null;

    final String sql = String.format(FIND_ALARM_BY_ID_SQL, " and a.id = :id", "");
    List<Alarm> alarms = new LinkedList<>();
    try {
      session = sessionFactory.openSession();
      Query qAlarmDefinition =
          session.createQuery(sql).setString("tenantId", tenantId)
              .setString("id", id);
      List<Object[]> alarmList = (List<Object[]>) qAlarmDefinition.list();

      if (alarmList.isEmpty()) {
        throw new EntityNotFoundException("No alarm exists for %s", id);
      }

      alarms = this.createAlarms(alarmList);

    } finally {
      if (session != null) {
        session.close();
      }
    }
    return alarms.get(0);
  }

  @Override
  public Alarm update(String tenantId, String id, AlarmState state, String lifecycleState, String link) {
    Session session = null;
    Alarm originalAlarm = null;
    Transaction tx = null;
    try {
      session = sessionFactory.openSession();
      tx = session.beginTransaction();
      originalAlarm = findById(tenantId, id);

      AlarmDb result = (AlarmDb) session
          .getNamedQuery(AlarmDb.Queries.FIND_BY_ID)
          .setString("id", id)
          .uniqueResult();

      if (!originalAlarm.getState().equals(state)) {
        result.setStateUpdatedAt(this.getUTCNow());
        result.setState(state);
      }

      result.setUpdatedAt(this.getUTCNow());
      result.setLink(link);
      result.setLifecycleState(lifecycleState);
      session.update(result);

      tx.commit();
      tx = null;
    } catch (Exception e) {
      this.rollbackIfNotNull(tx);
      throw e;
    } finally {
      if (session != null) {
        session.close();
      }
    }
    return originalAlarm;
  }

  @Override
  @SuppressWarnings("unchecked")
  public Map<String, AlarmSubExpression> findAlarmSubExpressions(String alarmId) {
    Session session = null;
    final Map<String, AlarmSubExpression> subAlarms = Maps.newHashMap();
    logger.debug("AlarmSqlRepoImpl[findAlarmSubExpressions] called");
    try {

      session = sessionFactory.openSession();
      final List<SubAlarmDb> result = session
          .getNamedQuery(SubAlarmDb.Queries.BY_ALARM_ID)
          .setString("id", alarmId)
          .list();

      if (result != null) {
        for (SubAlarmDb row : result) {
          subAlarms.put(row.getId(), AlarmSubExpression.of(row.getExpression()));
        }
      }
    } finally {
      if (session != null) {
        session.close();
      }
    }
    return subAlarms;
  }

  @Override
  @SuppressWarnings("unchecked")
  public Map<String, Map<String, AlarmSubExpression>> findAlarmSubExpressionsForAlarmDefinition(
      String alarmDefinitionId) {
    logger.trace(ORM_LOG_MARKER, "findAlarmSubExpressionsForAlarmDefinition(...) entering");

    Session session = null;
    Transaction tx = null;
    Map<String, Map<String, AlarmSubExpression>> subAlarms = Maps.newHashMap();

    try {
      session = sessionFactory.openSession();
      tx = session.beginTransaction();

      final Iterator<SubAlarmDb> rows = session
          .getNamedQuery(SubAlarmDb.Queries.BY_ALARMDEFINITION_ID)
          .setString("id", alarmDefinitionId)
          .setReadOnly(true)
          .iterate();

      while (rows.hasNext()) {

        final SubAlarmDb row = rows.next();
        final String alarmId = (String) session.getIdentifier(row.getAlarm());

        Map<String, AlarmSubExpression> alarmMap = subAlarms.get(alarmId);
        if (alarmMap == null) {
          alarmMap = Maps.newHashMap();
          subAlarms.put(alarmId, alarmMap);
        }

        final String id = row.getId();
        final String expression = row.getExpression();
        alarmMap.put(id, AlarmSubExpression.of(expression));
      }

      tx.commit();
      tx = null;

    } catch (Exception exp) {
      this.rollbackIfNotNull(tx);
      throw exp;
    } finally {
      if (session != null) {
        session.close();
      }
    }

    return subAlarms;
  }

  @Override
  public AlarmCount getAlarmsCount(String tenantId, String alarmDefId, String metricName,
                                   Map<String, String> metricDimensions, AlarmState state,
                                   AlarmSeverity severity, String lifecycleState, String link,
                                   DateTime stateUpdatedStart, List<String> groupBy,
                                   String offset, int limit) {
    // Not Implemented
    return null;
  }
}
