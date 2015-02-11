package monasca.api.infrastructure.persistence.influxdb;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.Map;

import monasca.api.domain.model.metric.MetricDefinitionRepo;
import monasca.common.model.metric.MetricDefinition;

public class InfluxV9MetricDefinitionRepo implements MetricDefinitionRepo {

  private static final Logger
      logger = LoggerFactory.getLogger(InfluxV9MetricDefinitionRepo.class);

  @Override
  public List<MetricDefinition> find(String tenantId, String name, Map<String, String> dimensions,
                                     String offset) throws Exception {
    return null;
  }
}
