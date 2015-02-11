package monasca.api.infrastructure.persistence.influxdb;

import java.util.List;
import java.util.Map;

import monasca.api.domain.model.metric.MetricDefinitionRepo;
import monasca.common.model.metric.MetricDefinition;

public class InfluxV9MetricDefinitionRepo implements MetricDefinitionRepo{

  @Override
  public List<MetricDefinition> find(String tenantId, String name, Map<String, String> dimensions,
                                     String offset) throws Exception {
    return null;
  }
}
