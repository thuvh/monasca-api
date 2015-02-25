package monasca.api.domain.model.metric;

import com.codahale.metrics.Metric;

import monasca.common.model.domain.common.AbstractEntity;

public class MetricName extends AbstractEntity implements Comparable {

  public String id;
  public String name;

  public MetricName(String id, String name) {
    this.id = id;
    this.name = name;
  }

  @Override
  public boolean equals(Object obj) {
    if (this == obj) {
      return true;
    }
    if (obj == null) {
      return false;
    }
    if (getClass() != obj.getClass()) {
      return false;
    }
    MetricName other = (MetricName) obj;
    if (id == null) {
      if (other.id != null) {
        return false;
      }
    } else if (!id.equals(other.id)) {
      return false;
    }
    if (name == null) {
      if (other.name != null) {
        return false;
      }
    } else if (!name.equals(other.name)) {
      return false;
    }
    return true;
  }

  public String getId() {return id;}

  public String getName() {return name;}

  @Override
  public int hashCode() {
    final int prime = 31;
    int result = 1;
    result = prime * result + ((id == null) ? 0 : id.hashCode());
    result = prime * result + ((name == null) ? 0 : name.hashCode());
    return result;
  }

  public void setId(String id) {this.id = id;}

  public void setName(String name) {this.name = name;}

  @Override
  public int compareTo(Object o) {
    MetricName other = (MetricName) o;
    if(this.equals(other))
      return 0;
    return this.name.compareTo(other.name);
  }
}
