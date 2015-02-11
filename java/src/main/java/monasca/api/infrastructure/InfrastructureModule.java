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
package monasca.api.infrastructure;

import com.google.inject.AbstractModule;
import com.google.inject.Provides;
import com.google.inject.ProvisionException;

import org.influxdb.InfluxDB;
import org.influxdb.InfluxDBFactory;

import javax.inject.Singleton;

import monasca.api.MonApiConfiguration;
import monasca.api.domain.model.alarm.AlarmRepository;
import monasca.api.domain.model.alarmdefinition.AlarmDefinitionRepository;
import monasca.api.domain.model.alarmstatehistory.AlarmStateHistoryRepo;
import monasca.api.domain.model.measurement.MeasurementRepo;
import monasca.api.domain.model.metric.MetricDefinitionRepo;
import monasca.api.domain.model.notificationmethod.NotificationMethodRepository;
import monasca.api.domain.model.statistic.StatisticRepo;
import monasca.api.infrastructure.persistence.influxdb.InfluxV8AlarmStateHistoryRepo;
import monasca.api.infrastructure.persistence.influxdb.InfluxV8MeasurementRepo;
import monasca.api.infrastructure.persistence.influxdb.InfluxV8MetricDefinitionRepo;
import monasca.api.infrastructure.persistence.influxdb.InfluxV8StatisticRepo;
import monasca.api.infrastructure.persistence.influxdb.InfluxV9AlarmStateHistoryRepo;
import monasca.api.infrastructure.persistence.influxdb.InfluxV9MeasurementRepo;
import monasca.api.infrastructure.persistence.influxdb.InfluxV9MetricDefinitionRepo;
import monasca.api.infrastructure.persistence.influxdb.InfluxV9StatisticRepo;
import monasca.api.infrastructure.persistence.mysql.AlarmDefinitionMySqlRepositoryImpl;
import monasca.api.infrastructure.persistence.mysql.AlarmMySqlRepositoryImpl;
import monasca.api.infrastructure.persistence.mysql.NotificationMethodMySqlRepositoryImpl;
import monasca.api.infrastructure.persistence.vertica.AlarmStateHistoryVerticaRepoImpl;
import monasca.api.infrastructure.persistence.vertica.MeasurementVerticaRepoImpl;
import monasca.api.infrastructure.persistence.vertica.MetricDefinitionVerticaRepoImpl;
import monasca.api.infrastructure.persistence.vertica.StatisticVerticaRepoImpl;

/**
 * Infrastructure layer bindings.
 */
public class InfrastructureModule extends AbstractModule {

  private MonApiConfiguration config;

  private static final String VERTICA = "vertica";
  private static final String INFLUXDB = "influxdb";
  private static final String INFLUXDB_V8 = "v8";
  private static final String INFLUXDB_V9 = "v9";


  public InfrastructureModule(MonApiConfiguration config) {
    this.config = config;
  }

  @Override
  protected void configure() {
    // Bind repositories
    bind(AlarmRepository.class).to(AlarmMySqlRepositoryImpl.class).in(Singleton.class);
    bind(AlarmDefinitionRepository.class).to(AlarmDefinitionMySqlRepositoryImpl.class)
        .in(Singleton.class);
    if (config.databaseConfiguration.getDatabaseType().trim().toLowerCase().equals(VERTICA)) {
      bind(AlarmStateHistoryRepo.class).to(AlarmStateHistoryVerticaRepoImpl.class)
          .in(Singleton.class);
      bind(MetricDefinitionRepo.class).to(MetricDefinitionVerticaRepoImpl.class)
          .in(Singleton.class);
      bind(MeasurementRepo.class).to(MeasurementVerticaRepoImpl.class).in(Singleton.class);
      bind(StatisticRepo.class).to(StatisticVerticaRepoImpl.class).in(Singleton.class);
    } else if (config.databaseConfiguration.getDatabaseType().trim().toLowerCase()
        .equals(INFLUXDB)) {

      if (config.influxDB.getVersion() == null || config.influxDB.getVersion()
          .equalsIgnoreCase(INFLUXDB_V8)) {
        bind(AlarmStateHistoryRepo.class).to(InfluxV8AlarmStateHistoryRepo.class)
            .in(Singleton.class);
        bind(MetricDefinitionRepo.class).to(InfluxV8MetricDefinitionRepo.class).in(Singleton.class);
        bind(MeasurementRepo.class).to(InfluxV8MeasurementRepo.class).in(Singleton.class);
        bind(StatisticRepo.class).to(InfluxV8StatisticRepo.class).in(Singleton.class);
      } else if (config.influxDB.getVersion().equalsIgnoreCase(INFLUXDB_V9)) {

        bind(AlarmStateHistoryRepo.class).to(InfluxV9AlarmStateHistoryRepo.class)
            .in(Singleton.class);
        bind(MetricDefinitionRepo.class).to(InfluxV9MetricDefinitionRepo.class).in(Singleton.class);
        bind(MeasurementRepo.class).to(InfluxV9MeasurementRepo.class).in(Singleton.class);
        bind(StatisticRepo.class).to(InfluxV9StatisticRepo.class).in(Singleton.class);
      } else {
        throw new ProvisionException(
            "Found unknown Influxdb version: " + config.influxDB.getVersion() + "."
            + " Supported Influxdb versions are 'v8' and 'v9'. Please check your config file");

      }
    } else {
      throw new ProvisionException("Failed to detect supported database. Supported databases are "
                                   + "'vertica' and 'influxdb'. Please check your config file.");
    }

    bind(NotificationMethodRepository.class).to(NotificationMethodMySqlRepositoryImpl.class)
        .in(Singleton.class);
  }

  @Provides
  InfluxDB provideInfluxDB() {
    InfluxDB
        influxDB =
        InfluxDBFactory.connect(this.config.influxDB.getUrl(), this.config.influxDB.getUser(),
                                this.config.influxDB.getPassword());
    return influxDB;
  }
}
