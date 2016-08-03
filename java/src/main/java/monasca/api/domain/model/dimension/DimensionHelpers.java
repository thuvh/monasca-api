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

import org.apache.commons.codec.binary.Hex;
import org.apache.commons.codec.digest.DigestUtils;

public class DimensionHelpers {

    public static String generateDimensionId(String metricName, String dimensionName) {
        String hashstr;
        if (dimensionName == null) {
            hashstr = "metricName=" + metricName;
        } else {
            hashstr = "metricName=" + metricName + "dimensionName=" + dimensionName;
        }
        byte[] sha1Hash = DigestUtils.sha(hashstr);
        return Hex.encodeHexString(sha1Hash);
    }

    public static String getId(String id, String metricName, String dimensionName) {
        if (null == id) {
            id = generateDimensionId(metricName, dimensionName);
        }
        return id;
    }
}
