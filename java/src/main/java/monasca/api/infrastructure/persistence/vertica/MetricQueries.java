/*
 * Copyright (c) 2014,2016 Hewlett Packard Enterprise Development Company, L.P.
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

package monasca.api.infrastructure.persistence.vertica;

import com.google.common.base.Splitter;
import com.google.common.base.Strings;

import java.sql.Timestamp;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.joda.time.DateTime;
import org.skife.jdbi.v2.Query;

/**
 * Vertica utilities for building metric queries.
 */
final class MetricQueries {
  static final Splitter BAR_SPLITTER = Splitter.on('|').omitEmptyStrings().trimResults();
  static final char OFFSET_SEPARATOR = '_';
  static final Splitter offsetSplitter = Splitter.on(OFFSET_SEPARATOR).omitEmptyStrings().trimResults();

  private MetricQueries() {}

  static String buildDimensionAndClause(Map<String, String> dimensions,
                                        String tableToJoinName) {

    StringBuilder sb = null;

    if (dimensions != null && dimensions.size() > 0) {

      sb = new StringBuilder();
      sb.append(" and ( ");

      int i = 0;
      for (Iterator<Map.Entry<String, String>> it = dimensions.entrySet().iterator(); it.hasNext(); i++) {
        Map.Entry<String, String> entry = it.next();

        sb.append("(");
        sb.append(tableToJoinName).append(".name = :dname").append(i);

        String dim_value = entry.getValue();
        if (!Strings.isNullOrEmpty(dim_value)) {
          List<String> values = BAR_SPLITTER.splitToList(dim_value);

          if (values.size() > 1) {
            sb.append(" and ( ");

            for (int j = 0; j < values.size(); j++) {
              sb.append(tableToJoinName).append(".value = :dvalue").append(i).append('_').append(j);

              if (j < values.size() - 1) {
                sb.append(" or ");
              }
            }
            sb.append(")");

          } else {
            sb.append(" and ").append(tableToJoinName).append(".value = :dvalue").append(i);
          }
        }
        sb.append(")");

        if (it.hasNext()) {
          sb.append(" or ");
        }
      }

      sb.append(")");
    }

    return sb == null ? "" : sb.toString();
  }

  static String buildDimensionsSizeClause(Map<String, String> dimensions) {
    if (dimensions == null || dimensions.size() == 0) {
      return "";
    } else {
      return "HAVING COUNT(*) = " + dimensions.size();
    }
  }

  static void bindDimensionsToQuery(Query<?> query, Map<String, String> dimensions) {
    if (dimensions != null) {
      int i = 0;
      for (Iterator<Map.Entry<String, String>> it = dimensions.entrySet().iterator(); it.hasNext(); i++) {
        Map.Entry<String, String> entry = it.next();
        query.bind("dname" + i, entry.getKey());
        if (!Strings.isNullOrEmpty(entry.getValue())) {
          List<String> values = BAR_SPLITTER.splitToList(entry.getValue());
          if (values.size() > 1) {
            for (int j = 0; j < values.size(); j++) {
              query.bind("dvalue" + i + '_' + j, values.get(j));
            }
          }
          else {
            query.bind("dvalue" + i, entry.getValue());
          }
        }
      }
    }
  }

  static String createDefDimIdInClause(Set<String> defDimIdSet) {

    StringBuilder sb = new StringBuilder("IN ");

    sb.append("(");

    boolean first = true;
    for (String defDimId : defDimIdSet) {

      if (first) {
        first = false;
      } else {
        sb.append(",");
      }

      sb.append("'" + defDimId + "'");
    }

    sb.append(") ");

    return sb.toString();
  }

  static void bindOffsetToQuery(Query<Map<String, Object>> query, String offset) {
    List<String> offsets =  offsetSplitter.splitToList(offset);
    if (offsets.size() > 1) {
      query.bind("offset_id", offsets.get(0));
      query.bind("offset_timestamp",
                 new Timestamp(DateTime.parse(offsets.get(1)).getMillis()));
    } else {
      query.bind("offset_timestamp",
                 new Timestamp(DateTime.parse(offsets.get(0)).getMillis()));
    }
  }
}
