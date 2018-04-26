import cluster_search.helper.PluginClasses as PluginClasses
from sklearn.cluster import AffinityPropagation
import numpy as np

class affinity_propagation(PluginClasses.IClusterPlugin):
  af = AffinityPropagation(affinity='precomputed')
  def cluster_results(self, method_name, dist_matrix):
    affinity_matrix = np.add(dist_matrix * -1, 1)
    return self.af.fit_predict(affinity_matrix)
