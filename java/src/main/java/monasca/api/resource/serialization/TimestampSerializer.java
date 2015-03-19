package monasca.api.resource.serialization;

import com.fasterxml.jackson.core.JsonGenerator;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonSerializer;
import com.fasterxml.jackson.databind.SerializerProvider;

import java.io.IOException;
import java.sql.Timestamp;
import java.text.SimpleDateFormat;
import java.util.TimeZone;

/**
 * Created by ryan on 3/19/15.
 */
public class TimestampSerializer extends JsonSerializer<Timestamp> {

  @Override
  public void serialize(Timestamp value, JsonGenerator gen, SerializerProvider arg2) throws
                                                                                     IOException,
                                                                                     JsonProcessingException {

    SimpleDateFormat formatter = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'");
    formatter.setTimeZone(TimeZone.getTimeZone("UTC"));
    String formattedDate = formatter.format(value);

    gen.writeString(formattedDate);

  }

  @Override
  public Class<Timestamp> handledType() { return Timestamp.class;}

}
