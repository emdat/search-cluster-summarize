class IClusterPlugin(object):
  """ Plugins that cluster items given a distance matrix """

  def cluster_results(self, method_name, dist_matrix):
    """ Takes a distance matrix and returns clusters """
    """ Note that clusters are represented as a list in which the value at 
        each index is the cluster id of the corresponding item in the 
        distance matrix """
    return []
