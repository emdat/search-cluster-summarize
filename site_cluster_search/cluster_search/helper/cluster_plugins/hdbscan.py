import cluster_search.helper.PluginClasses as PluginClasses
import hdbscan

class hdbscan(PluginClasses.IClusterPlugin):
  clusterer = hdbscan.HDBSCAN(metric='precomputed');
  def cluster_results(self, method_name, dist_matrix):
    self.clusterer.fit(dist_matrix)
    return self.clusterer.labels_
