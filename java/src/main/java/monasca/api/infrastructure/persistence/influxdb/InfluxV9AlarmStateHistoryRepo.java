package monasca.api.infrastructure.persistence.influxdb;

import com.google.inject.Inject;

import org.joda.time.DateTime;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.Map;

import javax.annotation.Nullable;

import monasca.api.ApiConfig;
import monasca.api.domain.model.alarmstatehistory.AlarmStateHistory;
import monasca.api.domain.model.alarmstatehistory.AlarmStateHistoryRepo;

public class InfluxV9AlarmStateHistoryRepo implements AlarmStateHistoryRepo {

  private static final Logger logger = LoggerFactory
      .getLogger(InfluxV9AlarmStateHistoryRepo.class);

  private final InfluxV9RepoReader influxV9RepoReader;

  @Inject
  public InfluxV9AlarmStateHistoryRepo(InfluxV9RepoReader influxV9RepoReader) {

    this.influxV9RepoReader = influxV9RepoReader;

  }

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
