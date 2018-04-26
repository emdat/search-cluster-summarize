from yapsy.IPlugin import IPlugin

class IRankPlugin(IPlugin):
  """ Plugins that rank clusters based on some metric """
  
  def rank_clusters(self, all_clusters):
    """ Returns a list of the clusters in order of highest rank (most relevant)
        to lowest """
    return []

class ISummaryPlugin(IPlugin):
  """ Plugins that summarize clusters given a filepaths to the original
      documents and a list of SearchResults for each cluster"""

  def summarize_clusters(self, url_to_text_file, clusters_of_search_results, domain):
    """ Returns a dict of cluster id (str) : summary (str) """
    return {}

class IClusterPlugin(IPlugin):
  """ Plugins that cluster items given a distance matrix """

  def cluster_results(self, method_name, dist_matrix):
    """ Takes a distance matrix and returns clusters """
    """ Note that clusters are represented as a list in which the value at 
        each index is the cluster id of the corresponding item in the 
        distance matrix """
    return []

