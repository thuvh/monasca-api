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
package monasca.api;

import io.dropwizard.db.DataSourceFactory;
import io.dropwizard.jdbi.DBIFactory;
import io.dropwizard.setup.Environment;

import java.util.Properties;

import javax.inject.Named;
import javax.inject.Singleton;

import kafka.javaapi.producer.Producer;
import kafka.producer.ProducerConfig;
import monasca.api.app.ApplicationModule;
import monasca.api.domain.DomainModule;
import monasca.api.infrastructure.InfrastructureModule;
import monasca.common.hibernate.db.AlarmActionDb;
import monasca.common.hibernate.db.AlarmDb;
import monasca.common.hibernate.db.AlarmDefinitionDb;
import monasca.common.hibernate.db.AlarmMetricDb;
import monasca.common.hibernate.db.MetricDefinitionDb;
import monasca.common.hibernate.db.MetricDefinitionDimensionsDb;
import monasca.common.hibernate.db.MetricDimensionDb;
import monasca.common.hibernate.db.NotificationMethodDb;
import monasca.common.hibernate.db.SubAlarmDb;
import monasca.common.hibernate.db.SubAlarmDefinitionDb;
import monasca.common.hibernate.db.SubAlarmDefinitionDimensionDb;

import org.hibernate.SessionFactory;
import org.hibernate.boot.registry.StandardServiceRegistryBuilder;
import org.hibernate.cfg.Configuration;
import org.hibernate.service.ServiceRegistry;
import org.skife.jdbi.v2.DBI;

import com.codahale.metrics.MetricRegistry;
import com.google.common.base.Joiner;
import com.google.inject.AbstractModule;
import com.google.inject.Provides;
import com.google.inject.ProvisionException;
import com.google.inject.name.Names;

/**
 * Monitoring API server bindings.
 */
public class MonApiModule extends AbstractModule {
  private final ApiConfig config;
  private final Environment environment;

  public MonApiModule(Environment environment, ApiConfig config) {
    this.environment = environment;
    this.config = config;
  }

  @Override
  protected void configure() {
    bind(ApiConfig.class).toInstance(config);
    bind(MetricRegistry.class).toInstance(environment.metrics());
    if(!config.hibernate.getSupportEnabled()) {
      bind(DataSourceFactory.class).annotatedWith(Names.named("mysql")).toInstance(config.mysql);
    }
    bind(DataSourceFactory.class).annotatedWith(Names.named("vertica")).toInstance(config.vertica);

    install(new ApplicationModule());
    install(new DomainModule());
    install(new InfrastructureModule(this.config));
  }

  @Provides
  @Singleton
  @Named("orm")
  public SessionFactory getSessionFactory() {
    try {
      Configuration configuration = new Configuration();

      configuration.addAnnotatedClass(AlarmDb.class);
      configuration.addAnnotatedClass(AlarmDefinitionDb.class);
      configuration.addAnnotatedClass(AlarmMetricDb.class);
      configuration.addAnnotatedClass(MetricDefinitionDb.class);
      configuration.addAnnotatedClass(MetricDefinitionDimensionsDb.class);
      configuration.addAnnotatedClass(MetricDimensionDb.class);
      configuration.addAnnotatedClass(SubAlarmDefinitionDb.class);
      configuration.addAnnotatedClass(SubAlarmDefinitionDimensionDb.class);
      configuration.addAnnotatedClass(SubAlarmDb.class);
      configuration.addAnnotatedClass(AlarmActionDb.class);
      configuration.addAnnotatedClass(NotificationMethodDb.class);

      configuration.setProperties(this.getHikariProperties());
      ServiceRegistry serviceRegistry = new StandardServiceRegistryBuilder().applySettings(configuration.getProperties()).build();

      // builds a session factory from the service registry
      return configuration.buildSessionFactory(serviceRegistry);
    } catch (Throwable ex) {
      throw new ProvisionException("Failed to provision ORM DBI", ex);
    }
  }

  @Provides
  @Singleton
  @Named("mysql")
  public DBI getMySqlDBI() {
    try {
      return new DBIFactory().build(environment, config.mysql, "mysql");
    } catch (ClassNotFoundException e) {
      throw new ProvisionException("Failed to provision MySQL DBI", e);
    }
  }

  @Provides
  @Singleton
  @Named("vertica")
  public DBI getVerticaDBI() {
    try {
      return new DBIFactory().build(environment, config.vertica, "vertica");
    } catch (ClassNotFoundException e) {
      throw new ProvisionException("Failed to provision Vertica DBI", e);
    }
  }

  @Provides
  @Singleton
  public Producer<String, String> getProducer() {
    Properties props = new Properties();
    props.put("metadata.broker.list", Joiner.on(',').join(config.kafka.brokerUris));
    props.put("serializer.class", "kafka.serializer.StringEncoder");
    props.put("request.required.acks", "1");
    ProducerConfig config = new ProducerConfig(props);
    return new Producer<String, String>(config);
  }

  private Properties getHikariProperties() {
    Properties properties = new Properties();
    properties.put("hibernate.connection.provider_class", config.hibernate.getProviderClass());
    properties.put("hibernate.hbm2ddl.auto", config.hibernate.getAutoConfig());
    properties.put("show_sql", false);
    properties.put("hibernate.hikari.dataSourceClassName", config.hibernate.getDataSourceClassName());
    properties.put("hibernate.hikari.dataSource.serverName", config.hibernate.getServerName());
    properties.put("hibernate.hikari.dataSource.portNumber", config.hibernate.getPortNumber());
    properties.put("hibernate.hikari.dataSource.databaseName", config.hibernate.getDatabaseName());
    properties.put("hibernate.hikari.dataSource.user", config.hibernate.getUser());
    properties.put("hibernate.hikari.dataSource.password", config.hibernate.getPassword());
    properties.put("hibernate.hikari.dataSource.initialConnections", config.hibernate.getInitialConnections());
    properties.put("hibernate.hikari.dataSource.maxConnections", config.hibernate.getMaxConnections());
    properties.put("hibernate.hikari.connectionTestQuery", "SELECT 1");
    return properties;
  }
}
