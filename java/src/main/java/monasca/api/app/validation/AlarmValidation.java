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
package monasca.api.app.validation;

import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import javax.ws.rs.WebApplicationException;

import monasca.common.model.alarm.AlarmExpression;
import monasca.common.model.alarm.AlarmSubExpression;
import monasca.common.model.metric.MetricDefinition;
import monasca.api.resource.exception.Exceptions;

/**
 * Utilities for validating AlarmExpressions.
 */
public final class AlarmValidation {

  private static final List<String> VALID_ALARM_SERVERITY = Arrays.asList("low", "medium", "high",
      "critical");
  private static final int MAX_NAME_LENGTH = 255;
  private static final int MAX_DESCRIPTION_LENGTH = 255;
  private static final int MAX_ACTION_LENGTH = 50;

  private AlarmValidation() {}

  /**
   * @throws WebApplicationException if validation fails
   */
  public static void validate(String name, String description, String severity,
      List<String> alarmActions, List<String> okActions, List<String> undeterminedActions) {
    if (name != null && name.getBytes(StandardCharsets.UTF_8).length > MAX_NAME_LENGTH)
      throw Exceptions.unprocessableEntity("Name %s must be %d bytes or less", name,
          MAX_NAME_LENGTH);
    if (description != null &&
        description.getBytes(StandardCharsets.UTF_8).length > MAX_DESCRIPTION_LENGTH)
      throw Exceptions.unprocessableEntity("Description %s must be %d bytes or less", description,
          MAX_DESCRIPTION_LENGTH);
    validateActionsList(alarmActions, "Alarm");
    validateActionsList(okActions, "OK");
    validateActionsList(undeterminedActions, "Undetermined");
    if (severity != null && !VALID_ALARM_SERVERITY.contains(severity.toLowerCase())) {
      throw Exceptions.unprocessableEntity("%s is not a valid severity", severity);
    }
  }

  private static void validateActionsList(List<String> actions, String actionType) {
    if (actions != null) {
      for (String action : actions)
        if (action.getBytes(StandardCharsets.UTF_8).length > MAX_ACTION_LENGTH)
          throw Exceptions.unprocessableEntity("%s action %s must be %d bytes or less", actionType,
              action, MAX_ACTION_LENGTH);
      if (checkForDuplicateNotificationMethodsInAlarmDef(actions)) {
        throw Exceptions.unprocessableEntity(
            "Alarm definition cannot have Duplicate %s notification methods", actionType);
      }
    }
  }

  /**
   * Validates, normalizes and gets an AlarmExpression for the {@code expression}.
   * 
   * @throws WebApplicationException if validation fails
   */
  public static AlarmExpression validateNormalizeAndGet(String expression) {
    AlarmExpression alarmExpression = null;

    try {
      alarmExpression = AlarmExpression.of(expression);
    } catch (IllegalArgumentException e) {
      throw Exceptions.unprocessableEntityDetails("The alarm expression is invalid",
          e.getMessage(), e);
    }

    for (AlarmSubExpression subExpression : alarmExpression.getSubExpressions()) {
      MetricDefinition metricDef = subExpression.getMetricDefinition();

      // Normalize and validate namespace
      metricDef.name = MetricNameValidation.normalize(metricDef.name);
      MetricNameValidation.validate(metricDef.name, true);

      // Normalize and validate dimensions
      if (metricDef.dimensions != null) {
        metricDef.setDimensions(DimensionValidation.normalize(metricDef.dimensions));
        DimensionValidation.validate(metricDef.dimensions);
      }

      // Validate period
      if (subExpression.getPeriod() == 0)
        throw Exceptions.unprocessableEntity("Period must not be 0");
      if (subExpression.getPeriod() % 60 != 0)
        throw Exceptions.unprocessableEntity("Period %s must be a multiple of 60",
            subExpression.getPeriod());

      // Validate periods
      if (subExpression.getPeriods() < 1)
        throw Exceptions.unprocessableEntity("Periods %s must be greater than or equal to 1",
            subExpression.getPeriods());
      if (subExpression.getPeriod() * subExpression.getPeriods() > 1209600)
        throw Exceptions.unprocessableEntity(
            "Period %s times %s must total less than 2 weeks in seconds (1209600)",
            subExpression.getPeriod(), subExpression.getPeriods());
    }

    return alarmExpression;
  }

  /**
   * Method checks for duplicate alarm actions
   */
  @SuppressWarnings("unchecked")
  private static boolean checkForDuplicateNotificationMethodsInAlarmDef(List<String> alarmActions) {
    @SuppressWarnings("rawtypes")
    Set inputSet = new HashSet(alarmActions);
    if (inputSet.size() < alarmActions.size()) {
      return true;
    }
    return false;
  }
}
