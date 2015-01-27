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
 * @author:Angelo Mendonca
 */

package monasca.api.infrastructure.persistence.mysql;

import monasca.api.domain.model.alarmdefinition.AlarmDefinition;

import org.skife.jdbi.v2.sqlobject.Bind;
import org.skife.jdbi.v2.sqlobject.SqlQuery;
import org.skife.jdbi.v2.sqlobject.customizers.RegisterMapper;

@RegisterMapper(AlarmDefinitionMapper.class)
public interface CustomizedAlarmDefinition {

	@SqlQuery("select alarm_definition.*, group_concat(notification_method.name)as alarmNames,"
			+ "group_concat(alarm_action.action_id) as notificationIds,group_concat(alarm_action.alarm_state) as states "
			+ "from alarm_definition, alarm_action,notification_method where alarm_definition.id=alarm_action.alarm_definition_id "
			+ "and alarm_action.action_id=notification_method.id and alarm_definition.tenant_id=:tenantId and alarm_definition.id=:alarmDefId and alarm_definition.deleted_at is NULL group by alarm_definition.id")
	public AlarmDefinition getNotificationById(
			@Bind("tenantId") String tenantId,
			@Bind("alarmDefId") String alarmDefId);
}
