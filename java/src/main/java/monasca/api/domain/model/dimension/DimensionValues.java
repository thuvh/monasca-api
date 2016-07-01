/*
 * Copyright (c) 2016 Hewlett-Packard Development Company, L.P.
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
package monasca.api.domain.model.dimension;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import monasca.api.domain.model.common.Link;
import monasca.common.model.domain.common.AbstractEntity;

/**
 * Encapsulates the list of dimension values for a given dimension name.
 */
public class DimensionValues extends AbstractEntity {

  private List<Link> links;
  protected String name;
  protected List<String> values;
  protected Map<String, List<String>> dimensionValues;

  public DimensionValues() {
    this.values = new ArrayList<String>();
    this.dimensionValues = new HashMap<String, List<String>>();
  }

  public DimensionValues(String name, List<String> values) {
    this.name = name;
    this.values = values;
    this.dimensionValues = new HashMap<String, List<String>>();
    this.dimensionValues.put(name, values);
  }

  public void setLinks(List<Link> links) {
    this.links = links;
  }

  public List<Link> getLinks() {
    return this.links;
  }

  public List<String> getValues() {
    return values;
  }

  @Override
  public boolean equals(Object obj) {
    if (this == obj)
      return true;
    if (obj == null)
      return false;
    if (getClass() != obj.getClass())
      return false;
    DimensionValues other = (DimensionValues) obj;
    if (name == null) {
      if (other.name != null)
        return false;
    } else if (!name.equals(other.name))
      return false;
    if (values == null) {
      if (other.values != null)
        return false;
    } else if (!values.equals(other.values))
      return false;
    return true;
  }

  @Override
  public int hashCode() {
    final int prime = 31;
    int result = 1;
    result = prime * result + ((name == null) ? 0 : name.hashCode());
    result = prime * result + ((values == null) ? 0 : values.hashCode());
    return result;
  }

  @Override
  public String toString() {
    return String.format("DimensionValues [name=%s, values=%s]", name, values);
  }
}
