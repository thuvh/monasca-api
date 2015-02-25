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
package monasca.api.infrastructure.persistence.influxdb;

import com.google.inject.Inject;

import com.fasterxml.jackson.databind.ObjectMapper;

import org.joda.time.DateTime;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Arrays;
import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;

import javax.annotation.Nullable;

import monasca.api.ApiConfig;
import monasca.api.domain.model.statistic.StatisticRepo;
import monasca.api.domain.model.statistic.Statistics;


public class InfluxV9StatisticRepo implements StatisticRepo{


  private static final Logger logger = LoggerFactory.getLogger(InfluxV9StatisticRepo.class);

  private final ApiConfig config;
  private final String region;
  private final InfluxV9RepoReader influxV9RepoReader;
  private final InfluxV9Utils influxV9Utils;

  private final ObjectMapper objectMapper = new ObjectMapper();


  @Inject
  public InfluxV9StatisticRepo(ApiConfig config,
                               InfluxV9RepoReader influxV9RepoReader,
                               InfluxV9Utils influxV9Utils) {
    this.config = config;
    this.region = config.region;
    this.influxV9RepoReader = influxV9RepoReader;
    this.influxV9Utils = influxV9Utils;
  }

  @Override
  public List<Statistics> find(String tenantId, String name, Map<String, String> dimensions,
                               DateTime startTime, @Nullable DateTime endTime,
                               List<String> statistics, int period, String offset, int limit) throws Exception {

    String q = String.format("select %1$s %2$s "
                             + "where %3$s %4$s %5$s %6$s %7$s %8$s %9$s %10$s",
                             funcPart(statistics),
                             this.influxV9Utils.namePart(name, true),
                             this.influxV9Utils.tenantIdPart(tenantId),
                             this.influxV9Utils.regionPart(this.region),
                             this.influxV9Utils.startTimePart(startTime),
                             this.influxV9Utils.dimPart(dimensions),
                             this.influxV9Utils.endTimePart(endTime),
                             this.influxV9Utils.periodPart(period),
                             this.influxV9Utils.timeOffsetPart(offset),
                             this.influxV9Utils.limitPart(limit));

    // Todo. Need Influxdb 9 to support limit on points.

    logger.debug("Measurements query: {}", q);

    String r = this.influxV9RepoReader.read(q);

    Series series = this.objectMapper.readValue(r, Series.class);

    if (series.getSeriesLength() > 1) {

      throw new IllegalArgumentException ("Found multiple metrics matching search criteria. "
                                          + "Please refine your search criteria using additional dimensions.");
    }

    List<Statistics> statisticsList = statisticslist(series);

    logger.debug("Found {} metric definitions matching query", statisticsList.size());

    return statisticsList;

  }


  private List<Statistics> statisticslist(Series series) {

    List<Statistics> statisticsList = new LinkedList<>();

    if (!series.isEmpty()) {

      for (Serie serie : series.getSeries()) {

        Statistics statistics = new Statistics(serie.getName(), new HashMap<String, String>(),
                                               Arrays.asList(translateNames(serie.getColumns())));

        for (Object[] values : serie.getValues()) {
          statistics.addStatistics(Arrays.asList(values));
          statistics.setId((String) values[0]);
        }

        statisticsList.add(statistics);

      }

    }

    return statisticsList;
  }

  private String[] translateNames(String[] columnNamesArry) {

    for (int i = 0; i < columnNamesArry.length; i++) {

      columnNamesArry[i] = columnNamesArry[i].replaceAll("^time$", "timestamp");
      columnNamesArry[i] = columnNamesArry[i].replaceAll("^mean$", "avg");

    }

    return columnNamesArry;
  }

  private String funcPart(List<String> statistics) {

    StringBuilder sb = new StringBuilder();

    for (String stat : statistics) {
      if (sb.length() != 0) {
        sb.append(",");
      }

      if (stat.trim().toLowerCase().equals("avg")) {
        sb.append("mean(value)");
      } else {
        sb.append(String.format("%1$s(value)", stat));
      }
    }

    return sb.toString();
  }
}
