import cluster_search.helper.PluginClasses as PluginClasses
from cluster_search.helper.ResultClasses import *
from statistics import median 

class median_score(PluginClasses.IRankPlugin):
  """ Rank in order of the cluster's median document score (highest to lowest) """
  def rank_clusters(self, all_clusters):
    return sorted(all_clusters, key = lambda cluster: 
      -median(result.score for result in cluster.results))
