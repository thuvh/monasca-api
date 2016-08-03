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
 * Encapsulates the list of dimension names for an optional metric name.
 */
public class DimensionNames extends DimensionBase {

    public DimensionNames(String metricName, String dimensionNames) {
        super(metricName, dimensionNames);
    }

    @JsonProperty("dimensionNames")
    public String getDimensionInfo() {
        return super.getDimensionInfo();
    }

    @Override
    public String toString() {
        return String.format("DimensionNames: MetricName=%s DimensionNames [names=%s]",
                getMetricName(), getDimensionInfo());
    }
}
