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

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.annotation.JsonInclude;

import monasca.common.model.domain.common.AbstractEntity;

/**
 * Encapsulates the list of dimension values for a given dimension name
 * (and optional metric-name).
 */
public class DimensionNames extends AbstractEntity {
    @JsonInclude(JsonInclude.Include.NON_NULL)
    protected String metricName;
    protected List<String> names;
    protected Map<String, List<String>> dimensionNames;

    public DimensionNames(String metricName, List<String> names) {
        this.metricName = metricName;
        this.names = names;
        this.dimensionNames = new HashMap<String, List<String>>();
        this.dimensionNames.put(metricName, names);
    }

    public List<String> getDimensionNames() { return names; }

    public String getMetricName() {
        return metricName;
    }

    @Override
    public boolean equals(Object obj) {
        if (this == obj)
            return true;
        if (obj == null)
            return false;
        if (getClass() != obj.getClass())
            return false;
        DimensionNames other = (DimensionNames) obj;
        if (metricName == null) {
            if (other.metricName != null)
                return false;
        } else if (!metricName.equals(other.metricName))
            return false;
        if (names == null) {
            if (other.names != null)
                return false;
        } else if (!names.equals(other.names))
            return false;
        return true;
    }

    @Override
    public int hashCode() {
        final int prime = 31;
        int result = 1;
        result = prime * result + ((metricName == null) ? 0 : metricName.hashCode());
        result = prime * result + ((names == null) ? 0 : names.hashCode());
        return result;
    }

    @Override
    public String toString() {
        return String.format("MetricName=%s DimensionNames [names=%s]",
                metricName, names);
    }
}
