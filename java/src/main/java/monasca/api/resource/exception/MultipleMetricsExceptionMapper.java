package monasca.api.resource.exception;

import javax.ws.rs.core.MediaType;
import javax.ws.rs.core.Response;
import javax.ws.rs.ext.ExceptionMapper;
import javax.ws.rs.ext.Provider;

import monasca.api.infrastructure.persistence.influxdb.MultipleMetricsException;

@Provider
public class MultipleMetricsExceptionMapper implements ExceptionMapper<MultipleMetricsException> {

  private static final String
      MULTIPLE_METRICS_ERROR_MSG =
      "Found multiple metrics matching metric name and dimensions. "
      + "Please refine your search criteria using a unique metric name or additional dimensions. "
      + "Alternatively, you may specify 'merge_metrics=true' as a query param to combine "
      + "all metrics matching search criteria into a single series.";


  @Override
  public Response toResponse(MultipleMetricsException exception) {

    String details = String.format("search criteria: {metric name: %s, dimensions: %s}",
                                   exception.getMetricName(),  exception.getDimensions());

    return Response.status(Response.Status.CONFLICT).type(MediaType.APPLICATION_JSON).entity(
        Exceptions
            .buildLoggedErrorMessage(Exceptions.FaultType.CONFLICT, MULTIPLE_METRICS_ERROR_MSG,
                                     details, null)).build();

  }
}
