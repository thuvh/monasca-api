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

import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;

import javax.annotation.Nullable;

import monasca.api.ApiConfig;
import monasca.api.domain.model.measurement.MeasurementRepo;
import monasca.api.domain.model.measurement.Measurements;

public class InfluxV9MeasurementRepo implements MeasurementRepo {


  private static final Logger logger = LoggerFactory
      .getLogger(InfluxV9MeasurementRepo.class);


  private final ApiConfig config;
  private final String region;
  private final InfluxV9RepoReader influxV9RepoReader;
  private final InfluxV9Utils influxV9Utils;
  private final ObjectMapper objectMapper = new ObjectMapper();

  @Inject
  public InfluxV9MeasurementRepo(ApiConfig config,
                                 InfluxV9RepoReader influxV9RepoReader,
                                 InfluxV9Utils influxV9Utils) {
    this.config = config;
    this.region = config.region;
    this.influxV9RepoReader = influxV9RepoReader;
    this.influxV9Utils = influxV9Utils;

  }

  @Override
  public List<Measurements> find(String tenantId, String name, Map<String, String> dimensions,
                                 DateTime startTime, @Nullable DateTime endTime,
                                 @Nullable String offset, int limit) throws Exception {

    // Todo. Need Influxdb 9 to support limit on points.

    String q = String.format("select value %1$s where %2$s %3$s %4$s %5$s %6$s %7$s %8$s %9$s",
                             this.influxV9Utils.namePart(name, true),
                             this.influxV9Utils.tenantIdPart(tenantId),
                             this.influxV9Utils.regionPart(this.region),
                             this.influxV9Utils.startTimePart(startTime),
                             this.influxV9Utils.dimPart(dimensions),
                             this.influxV9Utils.endTimePart(endTime),
                             this.influxV9Utils.groupByPart(),
                             this.influxV9Utils.timeOffsetPart(offset),
                             this.influxV9Utils.limitPart(limit));

    logger.debug("Measurements query: {}", q);

    String r = this.influxV9RepoReader.read(q);

    Series series = this.objectMapper.readValue(r, Series.class);

    if (series.getSeriesLength() > 1) {

      throw new IllegalArgumentException ("Found multiple metrics matching search criteria. "
                                          + "Please refine your search criteria using additional dimensions.");
    }

    List<Measurements> measurementsList = measurementsList(series);

    logger.debug("Found {} metrics matching query", measurementsList.size());

    return measurementsList;
  }


  private List<Measurements> measurementsList(Series series) {

    List<Measurements> measurementsList = new LinkedList<>();

    if (!series.isEmpty()) {

      for (Serie serie : series.getSeries()) {

        Measurements measurements = new Measurements(serie.getName(), serie.getTags());

        for (String[] values : serie.getValues()) {

          measurements.addMeasurement(new Object[]{values[0], Double.parseDouble(values[1])});
        }

        measurementsList.add(measurements);
      }
    }

    return measurementsList;

  }
}
