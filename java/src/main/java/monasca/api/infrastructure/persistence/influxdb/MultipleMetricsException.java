package monasca.api.infrastructure.persistence.influxdb;

import java.util.HashMap;
import java.util.Map;

public class MultipleMetricsException extends Exception {



  private String metricName;
  private Map<String, String> dimensions;

  public MultipleMetricsException() {
    super();
    init(null, null);
  }

  public MultipleMetricsException(String metricName, Map<String, String> dimensions) {
    super();
    init(metricName, dimensions);
  }

  public MultipleMetricsException(String metricName, Map<String, String> dimensions,
                                  String message) {
    super(message);
    init(metricName, dimensions);
  }

  public MultipleMetricsException(String metricName, Map<String, String> dimensions,
                                  String message, Throwable cause) {
    super(message, cause);
    init(metricName, dimensions);
  }

  public MultipleMetricsException(String metricName, Map<String, String> dimensions,
                                  Throwable cause) {
    super(cause);
    init(metricName, dimensions);
  }

  public MultipleMetricsException(String metricName, Map<String, String> dimensions,
                                  String message, Throwable cause, boolean enableSuppression,
                                  boolean writableStackTrace) {
    super(message, cause, enableSuppression, writableStackTrace);
    init(metricName, dimensions);

  }

  private void init(String metricName, Map<String, String> dimensions) {
    this.metricName = metricName == null ? "" : metricName;
    this.dimensions = dimensions == null ? new HashMap<String, String>() : dimensions;
  }


  public String getMetricName() {
    return metricName;
  }

  public Map<String, String> getDimensions() {
    return dimensions;
  }
}
