import cluster_search.helper.PluginClasses as PluginClasses
from cluster_search.helper.ResultClasses import *

class sum_score(PluginClasses.IRankPlugin):
  """ Rank in order of the cluster's summed document score (highest to lowest) """
  def rank_clusters(self, all_clusters):
    return sorted(all_clusters, key = lambda cluster: 
      -sum(result.score for result in cluster.results))
