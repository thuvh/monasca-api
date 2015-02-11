package monasca.api.infrastructure.persistence.influxdb;

import com.google.inject.Inject;

import com.fasterxml.jackson.databind.ObjectMapper;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import monasca.api.domain.model.metric.MetricDefinitionRepo;
import monasca.common.model.metric.MetricDefinition;

public class InfluxV9MetricDefinitionRepo implements MetricDefinitionRepo{

  private static final Logger
      logger =
      LoggerFactory.getLogger(InfluxV9MetricDefinitionRepo.class);

  private final InfluxV9RepoReader influxV9RepoReader;

  @Inject
  public InfluxV9MetricDefinitionRepo(InfluxV9RepoReader influxV9RepoReader) {

    this.influxV9RepoReader = influxV9RepoReader;

  }

  @Override
  public List<MetricDefinition> find(String tenantId, String name, Map<String, String> dimensions,
                                     String offset) throws Exception {

    String namePart = buildNamePart(name);
    String dimPart = buildDimPart(dimensions);
    String tenantIdPart = buildTenantIdPart(tenantId);

    String q = String.format("show series %1$s where %2$s%3$s", namePart, tenantIdPart, dimPart);

    String r = this.influxV9RepoReader.read(q);

    ObjectMapper objectMapper = new ObjectMapper();

    Series series = objectMapper.readValue(r, Series.class);

    List<MetricDefinition> metricDefList = new ArrayList<>();

    if (series.results[0].rows != null) {

      for (Row row : series.results[0].rows) {

        for (String[] valuesArry : row.values) {

          Map<String, String> dimMap = new HashMap<>();
          for (int i = 0; i < row.columns.length; ++i) {
            dimMap.put(row.columns[i], valuesArry[i]);
          }

          MetricDefinition metricDefinition = new MetricDefinition(row.name, dimMap);
          metricDefList.add(metricDefinition);
        }
      }

    }
    return metricDefList;
  }

  private String buildTenantIdPart(String tenantId) {
    String s = "";

    if (tenantId != null && !tenantId.isEmpty()) {
      s += "tenant_id=" + "'" + tenantId + "'";
    }

    return s;
  }

  private String buildDimPart(Map<String, String> dims) {

    String s = "";

    if (dims != null && !dims.isEmpty()) {
      for (String k : dims.keySet()) {
        String v = dims.get(k);
        s += " and " + k + "=" + "'" + v + "'";
      }
    }
    return s;
  }

  private String buildNamePart(String name) {

    if (name != null && !name.isEmpty()) {
      return String.format("from \"%1$s\"", name);
    } else {
      return "";
    }
  }
}
