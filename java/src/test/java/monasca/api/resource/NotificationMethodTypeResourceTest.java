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

import java.io.IOException;
import java.util.Arrays;
import java.util.Iterator;
import java.util.Set;
import java.util.TreeSet;

import org.testng.annotations.Test;
import static org.testng.Assert.assertEquals;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import monasca.api.ApiConfig;

@Test
public class NotificationMethodTypeResourceTest extends AbstractMonApiResourceTest {

  private ApiConfig config;
  NotificationMethodTypesResource  resource;

  @Override
  protected void setupResources() throws Exception {
    super.setupResources();
    config = mock(ApiConfig.class);
    config.validNotificationPeriods = Arrays.asList(0, 60);
    resource =  new NotificationMethodTypesResource(config);
    addResources(resource);
  }




  private Set<String> getNotificationMethods(String jsonReponse)
  {
     Set<String>  rNotificationMethods = new TreeSet<String>();
     try{
     ObjectMapper mapper = new ObjectMapper();
     JsonNode  jsonObject = mapper.readTree(jsonReponse.getBytes());
     JsonNode notificationMethodTypesObject = jsonObject.path("types");

     Iterator<JsonNode> iterator = notificationMethodTypesObject.elements();
     while(iterator.hasNext() ){
         rNotificationMethods.add(iterator.next().asText());
          }
     }
     catch (IOException e){

     }
     return rNotificationMethods;

  }

  public void shouldListCorrectNotifcaitonTypes() throws Exception
  {
      String response =  client().resource("/v2.0/notification-methods/types").get(String.class);

      Set<String> responseGot = getNotificationMethods(response);
      Set<String>  expectedNotificationMethodTypes = new TreeSet<String>(Arrays.asList("EMAIL", "WEBHOOK", "PAGERDUTY"));
      assertEquals(responseGot, expectedNotificationMethodTypes);

      // Change the config to have one notification type
      config.validNotificationMethods = Arrays.asList("Email");
      resource.setNotificationMethods(config.validNotificationMethods);
      response =  client().resource("/v2.0/notification-methods/types").get(String.class);

      responseGot = getNotificationMethods(response);
      expectedNotificationMethodTypes = new TreeSet<String>(Arrays.asList("EMAIL"));
      assertEquals(responseGot, expectedNotificationMethodTypes);


      // Change the config to have more than one notification type
      config.validNotificationMethods = Arrays.asList("Email", "Type1", "Type2", "Type3");
      resource.setNotificationMethods(config.validNotificationMethods);
      response =  client().resource("/v2.0/notification-methods/types").get(String.class);

      responseGot = getNotificationMethods(response);
      expectedNotificationMethodTypes = new TreeSet<String>(Arrays.asList("EMAIL", "TYPE1", "TYPE2", "TYPE3"));
      assertEquals(responseGot, expectedNotificationMethodTypes);


  }

}
