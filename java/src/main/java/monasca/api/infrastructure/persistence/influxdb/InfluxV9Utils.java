package monasca.api.infrastructure.persistence.influxdb;

import java.util.HashMap;
import java.util.Map;

public class InfluxV9Utils {

  public static String namePart(String name) {

    if (name != null && !name.isEmpty()) {
      return String.format("from \"%1$s\"", name);
    } else {
      return "";
    }
  }

  public static String tenantIdPart(String tenantId) {
    String s = "";

    if (tenantId != null && !tenantId.isEmpty()) {
      s += "tenant_id=" + "'" + tenantId + "'";
    }

    return s;
  }

  public static String regionPart(String region) {
    String s = "";

    s += " and region=" + "'" + region + "'";

    return s;
  }

  public static String dimPart(Map<String, String> dims) {

    StringBuilder sb = new StringBuilder();

    if (dims != null && !dims.isEmpty()) {
      for (String k : dims.keySet()) {
        String v = dims.get(k);
        sb.append(" and " + k + "=" + "'" + v + "'");
      }
    }

    return sb.toString();
  }

}
