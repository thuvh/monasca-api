package monasca.api.infrastructure.persistence.influxdb;

import org.joda.time.DateTime;

import java.util.List;
import java.util.Map;

import javax.annotation.Nullable;

import monasca.api.domain.model.statistic.StatisticRepo;
import monasca.api.domain.model.statistic.Statistics;

public class InfluxV9StatisticRepo implements StatisticRepo{

  @Override
  public List<Statistics> find(String tenantId, String name, Map<String, String> dimensions,
                               DateTime startTime, @Nullable DateTime endTime,
                               List<String> statistics, int period) throws Exception {
    return null;
  }
}
