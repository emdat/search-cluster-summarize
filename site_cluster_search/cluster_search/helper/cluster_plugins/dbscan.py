import cluster_search.helper.PluginClasses as PluginClasses
from sklearn.cluster import DBSCAN

class dbscan(PluginClasses.IClusterPlugin):
  epsilon = 0.4
  dbs = DBSCAN(min_samples=2,eps=epsilon, metric="precomputed")
  def cluster_results(self, method_name, dist_matrix):
    return self.dbs.fit_predict(dist_matrix)
