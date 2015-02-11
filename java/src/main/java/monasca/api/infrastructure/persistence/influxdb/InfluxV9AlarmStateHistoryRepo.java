package monasca.api.infrastructure.persistence.influxdb;

import org.joda.time.DateTime;

import java.util.List;
import java.util.Map;

import javax.annotation.Nullable;

import monasca.api.domain.model.alarmstatehistory.AlarmStateHistory;
import monasca.api.domain.model.alarmstatehistory.AlarmStateHistoryRepo;

public class InfluxV9AlarmStateHistoryRepo implements AlarmStateHistoryRepo {

  @Override
  public List<AlarmStateHistory> findById(String tenantId, String alarmId, String offset)
      throws Exception {
    return null;
  }

  @Override
  public List<AlarmStateHistory> find(String tenantId, Map<String, String> dimensions,
                                      DateTime startTime, @Nullable DateTime endTime,
                                      @Nullable String offset) throws Exception {
    return null;
  }
}
