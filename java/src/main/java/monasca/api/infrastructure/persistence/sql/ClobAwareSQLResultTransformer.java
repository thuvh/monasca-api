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
import java.util.List;
import java.util.Map;

import com.google.common.collect.Maps;
import org.apache.commons.io.IOUtils;
import org.apache.log4j.Logger;
import org.hibernate.transform.ResultTransformer;

/**
 * Thread-safe (in context of construction) implementation of {@link ResultTransformer}
 */
enum ClobAwareSQLResultTransformer
    implements ResultTransformer {
  INSTANCE;

  private static final Logger LOGGER = Logger.getLogger(ClobAwareSQLResultTransformer.class);

  @Override
  public Object transformTuple(final Object[] tuple, final String[] aliases) {
    final Map<String, Object> map = Maps.newHashMapWithExpectedSize(aliases.length);

    for (int i = 0, size = aliases.length; i < size; i++) {
      Object t = tuple[i];
      if (t != null && t instanceof Clob) {
        Clob c = (Clob) tuple[i];
        try {
          t = this.convertFromClob(c);
        } catch (SQLException | IOException e) {
          LOGGER.error("transformTuple(...) error occured", e);
        }
      }
      map.put(aliases[i].toUpperCase(), t);
    }

    return map;
  }

  private Object convertFromClob(final Clob c) throws IOException, SQLException {
    final ByteArrayOutputStream bos = new ByteArrayOutputStream();
    IOUtils.copy(c.getAsciiStream(), bos);
    return new String(bos.toByteArray());
  }

  @Override
  public List transformList(final List collection) {
    return collection; // nothing to be done here
  }

}
