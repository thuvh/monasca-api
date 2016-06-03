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
package monasca.api.app.command;

import javax.validation.constraints.NotNull;
import javax.validation.constraints.Size;

import org.apache.commons.validator.routines.EmailValidator;
import org.apache.commons.validator.routines.RegexValidator;
import org.apache.commons.validator.routines.UrlValidator;
import org.hibernate.validator.constraints.NotEmpty;

import monasca.api.domain.model.notificationmethod.NotificationMethodType;
import monasca.api.resource.exception.Exceptions;

public class CreateNotificationMethodCommand {
  private static final String[] SCHEMES = {"http","https"};
  // Allow QA to use the TLD .test. This is valid according to RFC-2606
  private static final RegexValidator TEST_TLD_VALIDATOR = new RegexValidator(".+\\.test$");
  private static final UrlValidator URL_VALIDATOR =
            new UrlValidator(SCHEMES,
                             TEST_TLD_VALIDATOR,
                             UrlValidator.ALLOW_LOCAL_URLS | UrlValidator.ALLOW_2_SLASHES);
  @NotEmpty
  @Size(min = 1, max = 250)
  public String name;
  @NotNull
  public NotificationMethodType type;
  @NotEmpty
  @Size(min = 1, max = 512)
  public String address;

  public CreateNotificationMethodCommand() {}

  public CreateNotificationMethodCommand(String name, NotificationMethodType type, String address) {
    this.name = name;
    this.type = type;
    this.address = address;
  }

  @Override
  public boolean equals(Object obj) {
    if (this == obj)
      return true;
    if (obj == null)
      return false;
    if (getClass() != obj.getClass())
      return false;
    CreateNotificationMethodCommand other = (CreateNotificationMethodCommand) obj;
    if (address == null) {
      if (other.address != null)
        return false;
    } else if (!address.equals(other.address))
      return false;
    if (name == null) {
      if (other.name != null)
        return false;
    } else if (!name.equals(other.name))
      return false;
    if (type != other.type)
      return false;
    return true;
  }

  public void validate() {
    switch (type) {
      case EMAIL : {
        if (!EmailValidator.getInstance(true).isValid(address))
          throw Exceptions.unprocessableEntity("Address %s is not of correct format", address);
      }; break;
      case WEBHOOK : {
        if (!URL_VALIDATOR.isValid(address))
          throw Exceptions.unprocessableEntity("Address %s is not of correct format", address);
      }; break;
      case PAGERDUTY : {
        // No known validation for PAGERDUTY type at this time
      }; break;
    }
  }
}
