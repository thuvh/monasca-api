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

import org.joda.time.DateTime;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import javax.annotation.Nullable;

import monasca.api.ApiConfig;
import monasca.api.domain.model.alarmstatehistory.AlarmStateHistory;
import monasca.api.domain.model.alarmstatehistory.AlarmStateHistoryRepo;

public class InfluxV9AlarmStateHistoryRepo implements AlarmStateHistoryRepo {

  private static final Logger logger = LoggerFactory
      .getLogger(InfluxV9AlarmStateHistoryRepo.class);

  private final ApiConfig config;
  private final String region;
  private final InfluxV9RepoReader influxV9RepoReader;

  @Inject
  public InfluxV9AlarmStateHistoryRepo(ApiConfig config,
                                       InfluxV9RepoReader influxV9RepoReader) {

    this.config = config;
    this.region = config.region;
    this.influxV9RepoReader = influxV9RepoReader;

  }

  @Override
  public List<AlarmStateHistory> findById(String tenantId, String alarmId, String offset)
      throws Exception {
    return null;
  }

  @Override
  public List<AlarmStateHistory> find(String tenantId, Map<String, String> dimensions,
                                      DateTime startTime, @Nullable DateTime endTime,
                                      @Nullable String offset) throws Exception {

    String q = String.format("select value from %1$s where %2$s %3$s %4$s");

    List<AlarmStateHistory> alarmStates = new ArrayList<>();



    return alarmStates;
  }
}
