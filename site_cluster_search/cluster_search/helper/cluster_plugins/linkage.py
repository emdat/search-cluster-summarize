import cluster_search.helper.PluginClasses as PluginClasses
from scipy.cluster.hierarchy import linkage as scipy_linkage, fcluster
from scipy.spatial.distance import squareform

class linkage(PluginClasses.IClusterPlugin):
  epsilon = 0.4
  def cluster_results(self, method_name, dist_matrix):
    if method_name is None or method_name == "":
      method_name = "ward"
    cond_dist_matrix = squareform(dist_matrix)
    linkage_inf = scipy_linkage(cond_dist_matrix, method=method_name)
    clusters = fcluster(linkage_inf, t=self.epsilon, depth=5)
    return clusters
