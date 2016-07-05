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

import java.io.UnsupportedEncodingException;
import java.util.Arrays;
import java.util.List;

import javax.inject.Inject;
import javax.ws.rs.GET;
import javax.ws.rs.Path;
import javax.ws.rs.Produces;
import javax.ws.rs.core.Context;
import javax.ws.rs.core.MediaType;
import javax.ws.rs.core.Response;
import javax.ws.rs.core.UriInfo;

import com.codahale.metrics.annotation.Timed;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import monasca.api.ApiConfig;
import monasca.api.domain.model.notificationmethod.NotificationMethodTypesRepo;


/**
 * Notification Method resource implementation.
 */
@Path("/v2.0/notification-methods/types")
public class NotificationMethodTypesResource {

  private final static List<String> DEFAULT_NOTIFICATION_METHODS = Arrays.asList("Email", "PagerDuty", "WebHook");
  NotificationMethodTypesRepo repo = null;


  @Inject
  public NotificationMethodTypesResource(ApiConfig config, NotificationMethodTypesRepo repo) {
    this.repo = repo;
  }


  private List<String>  getNotificationMethodTypes()
  {
	  return repo.list_notification_method_types();
  }

  @GET
  @Timed
  @Produces(MediaType.APPLICATION_JSON)
  public Response list(@Context UriInfo uriInfo) throws UnsupportedEncodingException {

     // Since this response doesn't have id, we are directly manipulating using jackson api
     ObjectMapper mapper = new ObjectMapper();
     ObjectNode rootName = mapper.createObjectNode();
     ArrayNode arrayNode = mapper.createArrayNode();
     rootName.put("types", arrayNode);

     for (String method_type: getNotificationMethodTypes()){
        arrayNode.add(method_type.toUpperCase());
     }
     return Response.ok(rootName).build();
  }

  }
