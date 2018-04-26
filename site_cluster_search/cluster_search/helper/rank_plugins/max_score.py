import cluster_search.helper.PluginClasses as PluginClasses
from cluster_search.helper.ResultClasses import *

class max_score(PluginClasses.IRankPlugin):
  """ Rank in order of the cluster's max document score (highest to lowest) """
  def rank_clusters(self, all_clusters):
    return sorted(all_clusters, key = lambda cluster: 
      -max(result.score for result in cluster.results))
