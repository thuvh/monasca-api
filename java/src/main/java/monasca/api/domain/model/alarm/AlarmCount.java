package monasca.api.domain.model.alarm;

import java.util.ArrayList;
import java.util.List;

import monasca.api.domain.model.common.Link;
import monasca.api.domain.model.common.Linked;
import monasca.common.model.domain.common.AbstractEntity;

/**
 * Created by ryan on 1/6/16.
 */
public class AlarmCount extends AbstractEntity implements Linked {
  private List<Link> links;
  private List<String> columns;
  private List<List<Object>> counts;

  public AlarmCount() {}

  public AlarmCount(List<String> columns, List<List<Object>> counts) {
    this.columns = new ArrayList<>();
    this.columns.add("count");
    if (columns != null) {
      this.columns.addAll(columns);
    }
    this.counts = new ArrayList<>();
    this.counts.addAll(counts);
  }

  public void setColumns(List<String> columns) {
    this.columns = columns;
  }

  public List<String> getColumns() {
    return this.columns;
  }

  public void setCounts(List<List<Object>> counts) {
    this.counts = counts;
  }

  public List<List<Object>> getCounts() {
    return this.counts;
  }

  public void setLinks(List<Link> links) {
    this.links = links;
  }

  public List<Link> getLinks() {
    return this.links;
  }
}
