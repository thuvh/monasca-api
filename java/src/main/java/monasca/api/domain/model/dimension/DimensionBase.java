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
import org.apache.commons.codec.binary.Hex;
import org.apache.commons.codec.digest.DigestUtils;

import monasca.common.model.domain.common.AbstractEntity;

/**
 * Base class for DimensionNames and DimensionValues.
 */
public abstract class DimensionBase extends AbstractEntity {
    @JsonInclude(JsonInclude.Include.NON_NULL)
    final private String metricName;
    final private List<String> dimensionInfo;
    final private String id;

    public DimensionBase(String metricName, List<String> dimensionInfo, String dimString) {
        this.metricName = metricName;
        this.dimensionInfo = dimensionInfo;
        this.id = generateId(dimString);
    }

    public List<String> getDimensionInfo() {
        return dimensionInfo;
    }

    public String getMetricName() {
        return metricName;
    }

    public String getId() {
        return id;
    }

    protected String generateId(String dimString) {
        byte[] sha1Hash = DigestUtils.sha(dimString);
        return Hex.encodeHexString(sha1Hash);
    }

    public boolean equals(Object obj) {
        if (this == obj)
            return true;
        if (obj == null)
            return false;
        if (getClass() != obj.getClass())
            return false;
        DimensionBase other = (DimensionBase) obj;
        if (metricName == null) {
            if (other.getMetricName() != null)
                return false;
        } else if (!metricName.equals(other.getMetricName()))
            return false;
        if (dimensionInfo == null) {
            if (other.getDimensionInfo() != null)
                return false;
        } else if (!dimensionInfo.equals(other.getDimensionInfo()))
            return false;
        return true;
    }

    public int hashCode() {
        final int prime = 31;
        int result = 1;
        result = prime * result + ((metricName == null) ? 0 : metricName.hashCode());
        result = prime * result + ((dimensionInfo == null) ? 0 : dimensionInfo.hashCode());
        return result;
    }
}
