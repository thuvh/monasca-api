package monasca.api.infrastructure.persistence.influxdb;

public class Series {

  public RowsObject[] results;

}

class RowsObject {

  public Row[] rows;

}
class Row {

  public String name;
  public String[] columns;
  public String[][] values;

}
