package monasca.api.infrastructure.persistence.influxdb;

import org.joda.time.DateTime;

import java.util.List;
import java.util.Map;

import javax.annotation.Nullable;

import monasca.api.domain.model.measurement.MeasurementRepo;
import monasca.api.domain.model.measurement.Measurements;

public class InfluxV9MeasurementRepo implements MeasurementRepo {

  @Override
  public List<Measurements> find(String tenantId, String name, Map<String, String> dimensions,
                                 DateTime startTime, @Nullable DateTime endTime,
                                 @Nullable String offset) throws Exception {
    return null;
  }
}
