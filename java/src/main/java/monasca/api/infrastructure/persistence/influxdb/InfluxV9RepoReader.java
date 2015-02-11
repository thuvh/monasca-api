package monasca.api.infrastructure.persistence.influxdb;

import com.google.inject.Inject;

import org.apache.commons.codec.binary.Base64;
import org.apache.http.HttpEntity;
import org.apache.http.HttpResponse;
import org.apache.http.HttpStatus;
import org.apache.http.client.HttpClient;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.client.methods.HttpPost;
import org.apache.http.entity.StringEntity;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClientBuilder;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.util.EntityUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.URLEncoder;
import java.util.HashMap;

import monasca.api.ApiConfig;

public class InfluxV9RepoReader {

  private static final Logger logger = LoggerFactory.getLogger(InfluxV9RepoReader.class);

  private final ApiConfig config;

  private final String influxName;
  private final String influxUrl;
  private final String influxCreds;
  private final String influxUser;
  private final String influxPass;
  private final String influxRetentionPolicy;
  private final String baseAuthHeader;

  @Inject
  public InfluxV9RepoReader(final ApiConfig config) {
    this.config = config;

    this.influxName = config.influxDB.getName();
    this.influxUrl = config.influxDB.getUrl() + "/query";
    this.influxUser = config.influxDB.getUser();
    this.influxPass = config.influxDB.getPassword();
    this.influxCreds = this.influxUser + ":" + this.influxPass;
    this.influxRetentionPolicy = config.influxDB.getRetentionPolicy();

    this.baseAuthHeader = "Basic " + new String(Base64.encodeBase64(this.influxCreds.getBytes()));

  }

  protected String read(final String query) throws Exception {

    HttpGet request = new HttpGet(this.influxUrl + "?q=" + URLEncoder.encode(query, "UTF-8")
                                  + "&db=" + URLEncoder.encode(this.influxName, "UTF-8"));

    request.addHeader("content-type", "application/json");
    request.addHeader("Authorization", this.baseAuthHeader);

    CloseableHttpClient httpClient = HttpClients.createDefault();

    try {

      logger.debug("Sending query {} to influxdb database {} at {}", query, this.influxName,
                   this.influxUrl);

      HttpResponse response = httpClient.execute(request);

      int rc = response.getStatusLine().getStatusCode();

      if (rc != HttpStatus.SC_OK) {

        HttpEntity entity = response.getEntity();
        String responseString = EntityUtils.toString(entity, "UTF-8");
        logger.error("Failed to query Influxdb: {}", String.valueOf(rc));
        logger.error("Http response: {}", responseString);

        throw new Exception(responseString);
      }

      logger.debug("Successfully queried {} influxdb database {} at {}", this.influxName,
                   this.influxUrl);

      HttpEntity entity = response.getEntity();
      return entity != null ? EntityUtils.toString(entity) : null;

    } finally {

      request.releaseConnection();
      httpClient.close();

    }
  }

}
