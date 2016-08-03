/*
 * (C) Copyright 2016 Hewlett Packard Enterprise Development LP
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

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Encapsulates the list of dimension values for a given dimension name
 * (and optional metric-name).
 */
public class DimensionValues extends DimensionBase {

  final private String dimensionName;

  public DimensionValues(String metricName, String dimensionName, String dimensionValues) {
    super(metricName, dimensionValues);
    this.dimensionName = dimensionName;
  }

  @Override
  @JsonProperty("dimensionValue")
  public String getDimensionInfo() {
    return super.getDimensionInfo();
  }

  @Override
  public boolean equals(Object obj) {
    DimensionValues other = (DimensionValues) obj;
    if (dimensionName == null) {
      if (other.dimensionName != null)
        return false;
    } else if (!dimensionName.equals(other.dimensionName))
      return false;
    return super.equals(obj);
  }

  @Override
  public int hashCode() {
    final int prime = 31;
    int result = super.hashCode();
    result = prime * result + ((getDimensionInfo() == null) ? 0 : getDimensionInfo().hashCode());
    return result;
  }

  @Override
  public String toString() {
    return String.format("DimensionValues: MetricName=%s DimensionValues [name=%s, values=%s]",
                         getMetricName(), dimensionName, getDimensionInfo());
  }
}
