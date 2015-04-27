/*
 * Copyright 2015 FUJITSU LIMITED
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
package monasca.api.infrastructure.persistence.sql;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.sql.Clob;
import java.sql.SQLException;
import java.util.HashMap;
import java.util.Map;

import org.apache.commons.io.IOUtils;
import org.hibernate.transform.BasicTransformerAdapter;


public class ResultTransformer extends BasicTransformerAdapter {

  public final static ResultTransformer INSTANCE;
  static {
    INSTANCE = new ResultTransformer();
  }

  private ResultTransformer() {

  }

  private static final long serialVersionUID = 1L;

  @Override
  public Object transformTuple(Object[] tuple, String[] aliases) {
    Map<String, Object> map = new HashMap<String, Object>();
    for (int i = 0; i < aliases.length; i++) {
      Object t = tuple[i];
      if (t != null && t instanceof Clob) {
        Clob c = (Clob) tuple[i];
        try {
          ByteArrayOutputStream bos = new ByteArrayOutputStream();
          IOUtils.copy(c.getAsciiStream(), bos);
          t = new String(bos.toByteArray());
        } catch (SQLException e) {
          e.printStackTrace();
        } catch (IOException e) {
          e.printStackTrace();
        }
      }
      map.put(aliases[i].toUpperCase(), t);
    }
    return map;
  }
}
