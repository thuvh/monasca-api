/*
 * (C) Copyright 2016 Hewlett Packard Enterprise Development Company LP
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

package monasca.api.resource;

import static org.mockito.Mockito.mock;
import static org.testng.Assert.assertEquals;

import java.util.Arrays;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;

import org.testng.annotations.Test;

import monasca.api.ApiConfig;

@Test
public class NotificationMethodTypeResourceTest extends AbstractMonApiResourceTest {

  private ApiConfig config;

  @Override
  protected void setupResources() throws Exception {
    super.setupResources();
    config = mock(ApiConfig.class);
    config.validNotificationPeriods = Arrays.asList(0, 60);
    addResources(new NotificationMethodTypesResource(config));
  }


  public void shouldList() {

    List<String> ls= (List) client().resource("/v2.0/notification-methods/types").get(List.class);

    Set<String>  expectedNotificationMethodTypes = new TreeSet<String>(Arrays.asList("EMAIL", "WEBHOOK", "PAGERDUTY"));
    assertEquals( new TreeSet<String>(ls), expectedNotificationMethodTypes);
  }

}
