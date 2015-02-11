package monasca.api.infrastructure.persistence.influxdb;

import org.joda.time.DateTime;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.Map;

import javax.annotation.Nullable;

import monasca.api.domain.model.measurement.MeasurementRepo;
import monasca.api.domain.model.measurement.Measurements;

public class InfluxV9MeasurementRepo implements MeasurementRepo {


  private static final Logger logger = LoggerFactory
      .getLogger(InfluxV9MeasurementRepo.class);

  @Override
  public List<Measurements> find(String tenantId, String name, Map<String, String> dimensions,
                                 DateTime startTime, @Nullable DateTime endTime,
                                 @Nullable String offset) throws Exception {
    return null;
  }
}
