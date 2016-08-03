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

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import monasca.common.model.domain.common.AbstractEntity;
import org.apache.commons.codec.binary.Hex;
import org.apache.commons.codec.digest.DigestUtils;

/**
 * Encapsulates the list of dimension names for an optional metric name.
 */
public class DimensionNames extends AbstractEntity {
    private String id;
    @JsonInclude(JsonInclude.Include.NON_NULL)
    private String metricName;
    private List<String> dimensionInfo;

    public DimensionNames(String metricName, List<String> dimensionInfo) {
        this.metricName = metricName;
        this.dimensionInfo = dimensionInfo;
        setId();
    }

    @JsonProperty("dimensionNames")
    public List<String> getDimensionInfo() {
        return dimensionInfo;
    }

    public String getMetricName() {
        return metricName;
    }

    public String getId() {
        return id;
    }

    protected String generateId() {
        String hashstr = "metricName=" + getMetricName();
        byte[] sha1Hash = DigestUtils.sha(hashstr);
        return Hex.encodeHexString(sha1Hash);
    }

    public void setId() {
        this.id = generateId();
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
        if (dimensionInfo == null) {
            if (other.dimensionInfo != null)
                return false;
        } else if (!dimensionInfo.equals(other.dimensionInfo))
            return false;
        return true;
    }

    @Override
    public int hashCode() {
        final int prime = 31;
        int result = 1;
        result = prime * result + ((metricName == null) ? 0 : metricName.hashCode());
        result = prime * result + ((dimensionInfo == null) ? 0 : dimensionInfo.hashCode());
        return result;
    }

    @Override
    public String toString() {
        return String.format("DimensionNames: MetricName=%s DimensionNames [names=%s]",
                metricName, dimensionInfo);
    }
}
