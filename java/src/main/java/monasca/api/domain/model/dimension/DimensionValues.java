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

import java.util.List;

import com.fasterxml.jackson.annotation.JsonProperty;
import org.apache.commons.codec.binary.Hex;
import org.apache.commons.codec.digest.DigestUtils;

/**
 * Encapsulates the list of dimension values for a given dimension name
 * (and optional metric-name).
 */
public class DimensionValues extends DimensionBase {

  private String dimensionName;

  public DimensionValues(String metricName, List<String> dimensionValues, String dimensionName) {
    super(metricName, dimensionValues);
    this.dimensionName = dimensionName;
    this.id = generateId();
  }

  @Override
  @JsonProperty("values")
  public List<String> getDimensionInfo() {
    return super.getDimensionInfo();
  }

  public String getDimensionName() {
    return dimensionName;
  }

  private String generateId() {
    String hashstr = "metricName=" + getMetricName() + "dimensionName=" + getDimensionName();
    byte[] sha1Hash = DigestUtils.sha(hashstr);
    return Hex.encodeHexString(sha1Hash);
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
                         getMetricName(), getDimensionName(), getDimensionInfo());
  }
}
