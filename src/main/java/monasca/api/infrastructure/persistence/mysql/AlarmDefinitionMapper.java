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
   @author:Angelo Mendonca
 */
package monasca.api.infrastructure.persistence.mysql;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

import monasca.api.domain.model.alarmdefinition.AlarmDefinition;
import monasca.common.model.alarm.AlarmState;

import org.skife.jdbi.v2.StatementContext;
import org.skife.jdbi.v2.tweak.ResultSetMapper;

import com.google.common.base.Splitter;
import com.google.common.collect.Lists;

public class AlarmDefinitionMapper implements ResultSetMapper<AlarmDefinition> {
	private static final Splitter COMMA_SPLITTER = Splitter.on(',')
			.omitEmptyStrings().trimResults();

	public AlarmDefinition map(int index, ResultSet r, StatementContext ctx)
			throws SQLException {
		String notificationIds = r.getString("notificationIds");
		String states = r.getString("states");
		String matchBy = r.getString("match_by");

		List<String> notifications = splitStringIntoList(notificationIds);
		List<String> state = splitStringIntoList(states);
		List<String> match = splitStringIntoList(matchBy);

		List<String> okActionIds = new ArrayList<String>();
		List<String> alarmActionIds = new ArrayList<String>();
		List<String> undeterminedActionIds = new ArrayList<String>();

		int stateAndActionIndex = 0;
		for (String singleState : state) {
			if (singleState.equals(AlarmState.UNDETERMINED.name()))
				undeterminedActionIds.add(notifications
						.get(stateAndActionIndex));
			if (singleState.equals(AlarmState.OK.name()))
				okActionIds.add(notifications.get(stateAndActionIndex));
			if (singleState.equals(AlarmState.ALARM.name()))
				alarmActionIds.add(notifications.get(stateAndActionIndex));

			stateAndActionIndex++;
		}

		return new AlarmDefinition(r.getString("id"), r.getString("name"),
				r.getString("description"), r.getString("severity"),
				r.getString("expression"), match,
				r.getBoolean("actions_enabled"), alarmActionIds, okActionIds,
				undeterminedActionIds);
	}

	private List<String> splitStringIntoList(String commaDelimitedString) {
		Iterable<String> split = COMMA_SPLITTER.split(commaDelimitedString);
		return Lists.newArrayList(split);
	}

}