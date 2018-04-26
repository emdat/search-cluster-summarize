import os
import string
import MySQLdb
import json
import requests
import numpy as np
from sys import argv
from math import acos, pi
import nltk
from .ClusterProcessAlgorithmsClass import *
from .ConnectionClasses import MySQLDBConnectionOpts, SOLRCollection
from yapsy.PluginManager import PluginManager
from .PluginClasses import *
from .ResultClasses import *
from .compute_similarity import similarity_columns

# Url, Title, Fulltext, Plaintext
sim_weights = [0.05, 0.25, 0.2, 0.5]

# Initialize plugin manager and plugins
plugin_manager = PluginManager()
cur_dir = os.path.dirname(os.path.abspath(__file__))
plugin_manager.setPluginPlaces([os.path.join(cur_dir, "cluster_plugins"),
                                os.path.join(cur_dir, "summary_plugins"),
                                os.path.join(cur_dir, "rank_plugins")])
plugin_manager.setCategoriesFilter({
  "cluster" : IClusterPlugin,
  "summary" : ISummaryPlugin,
  "rank" : IRankPlugin,
  })
plugin_manager.collectPlugins()

# Cosine similarity to cosine distance
def cos_sim_to_dist(sim_score):
	return 1.0 - sim_score

def get_url_extracted_text_dict(filepath_of_urlmaps):
  url_to_file = {}                                                              
  try:                                                                          
    urls = set()                                                                
    with open(filepath_of_urlmaps, 'r') as f:                                     
      while True:                                                               
        # In each pair of 2 lines, first is url and second is                   
        # the name of the html file downloaded from that url                    
        cur_url = f.readline().strip()                                          
        if not cur_url:                                                         
          break                                                                 
        cur_file = f.readline().strip()                                         
        if cur_url in urls:                                                     
          continue                                                              
        urls.add(cur_url)                                                       
        url_to_file[cur_url] = cur_file + "_extracted.txt"
  except Exception as e:                                                        
    print("Error:  " + repr(e))                                                 
    raise e                                  
  
  return url_to_file

def get_solr_query_response(solr_collection, search_terms, highlight_field="_plaintext_"): 
  search_url = solr_collection.base_url + "/" + solr_collection.collection_name + "/select/"
  payload = {'q':search_terms,
             'defType':'dismax',
             'qf':'attr_titles^3.0 _plaintext_^2 _text_^0.5',
             'fl':"id,attr_titles,crawled_url,highlighting,score",
             'hl':"true",
             'hl.method':'unified',
             'hl.tag.pre':'<mark>',
             'hl.tag.post':'</mark>',
             'hl.tag.ellipsis':'....',
             'hl.fl':highlight_field + ",_text_",
             'wt':'json'}
  
  req = requests.Request('GET', search_url, params=payload).prepare()
  print('{}\n{}\n{}\n\n{}'.format(
          '-----------START-----------',
                  req.method + ' ' + req.url,
                          '\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
                                  req.body,
                                      ))

  response = requests.get(search_url, params=payload)
  if not response.ok:
    print(response.text)
    return None, None
  
  json_resp = json.loads(response.content)

  search_results = []
  returned_url_hashes = []
  
  docs = json_resp["response"]["docs"]
  try:
    highlights = json_resp["highlighting"]
  except:
    print("no highlights")
    highlights = {}

  for doc in docs:
    if "crawled_url" not in doc:
      continue
    url = doc["crawled_url"]
    title = doc["attr_titles"][0]
    highlight = '....'.join(highlights[url][highlight_field])
    if highlight is None or highlight == "":
      highlight = '....'.join(highlights[url]["_text_"]) 
    score = doc["score"]
    res = SearchResult(url=url, title=title, highlight=highlight, score=score)
    search_results.append(res)
    returned_url_hashes.append("MD5('" + url + "')")
 
  return search_results, returned_url_hashes

def get_distance_matrix(search_results, returned_url_hashes, db, sim_table):
  
  cur = db.cursor()

  returned_url_hashes_str = "(" + ",".join(returned_url_hashes) + ")"
  
  where_str = " WHERE url1_hash IN " + returned_url_hashes_str + " AND "
  where_str += "url2_hash IN " + returned_url_hashes_str
  order_str = " ORDER BY url1_hash, url2_hash;" 
  query_str = "SELECT url1, url2, %s FROM %s " % (", ".join(similarity_columns), sim_table)
  query_str += where_str
  query_str += order_str
  
  print("start query: %s" % (query_str))
  try:
    cur.execute(query_str)
    db.commit()
  except Exception as e:
    db.rollback()
    print ("Couldn't SELECT urls, sim_scores: " + repr(e))
    cur.close()
    return
  print("done query")

  num_urls = len(search_results)
  url_to_ind = {}
  for ind, res in enumerate(search_results):
    url_to_ind[res.url] = ind
  
  dist_matrix = np.ones(shape=(num_urls, num_urls), dtype=np.float64)
  np.fill_diagonal(dist_matrix, 0.0)
  while True:
    row = cur.fetchone()
    if not row:
      break

    ind1 = url_to_ind[ row[0] ]
    ind2 = url_to_ind[ row[1] ]
    weighted_sim_score = np.dot(sim_weights, row[2:])
    dist_matrix[ind1, ind2] = cos_sim_to_dist(weighted_sim_score)
    dist_matrix[ind2, ind1] = cos_sim_to_dist(weighted_sim_score)
  
  np.clip(dist_matrix, 0, 1, dist_matrix)
  cur.close()
  return dist_matrix

def get_clusters(dist_matrix, cluster_alg="dbscan"):
  clusters = []
  epsilon = 0.4
 
  # Get cluster name and optional method
  cluster_alg = cluster_alg.lower()
  split_alg_name = cluster_alg.split('-')
  alg_name = split_alg_name[0]
  if len(split_alg_name) > 1:
    method_name = split_alg_name[1]
  else:
    method_name = ""
  
  # Load appropriate clustering plugin
  cluster_plugin = plugin_manager.getPluginByName(name=alg_name, category="cluster")
  clusters = cluster_plugin.plugin_object.cluster_results(method_name, dist_matrix)
  return clusters

def reformat_to_clusters_of_results(clusters, search_results):
  clusters_of_search_results = {}
  min_cluster = 0
  for ind, res in enumerate(search_results):
    # Any results in cluster "-1" are not actually in a cluster,
    # but are by themselves.
    cluster = clusters[ind]
    if cluster < 0:
      min_cluster -= 1
      cluster = min_cluster
    cluster_str = str(cluster)

    if cluster_str not in clusters_of_search_results:
      clusters_of_search_results[cluster_str] = []
    clusters_of_search_results[cluster_str].append(res)
  return clusters_of_search_results

def get_cluster_summaries(clusters_of_search_results, filepath_of_urlmaps, domain, summary_alg="rake"):
  url_to_extracted_text_file =  get_url_extracted_text_dict(filepath_of_urlmaps)
  
  # Load appropriate summarizing plugin
  summary_alg = summary_alg.lower()
  summary_plugin = plugin_manager.getPluginByName(name=summary_alg, category="summary")
  cluster_to_summaries = summary_plugin.plugin_object.summarize_clusters(url_to_extracted_text_file, clusters_of_search_results, domain)
  return cluster_to_summaries

def get_ranked_clusters(all_clusters, rank_alg="max_score"):
  # Load appropriate ranking plugin
  rank_alg = rank_alg.lower()
  rank_plugin = plugin_manager.getPluginByName(name=rank_alg, category="rank")
  ranked_clusters = rank_plugin.plugin_object.rank_clusters(all_clusters)
  return ranked_clusters

def get_ranked_search_results(query, solr_collection):
  search_results, returned_url_hashes = get_solr_query_response(solr_collection, query)
  return sorted(search_results, key = lambda result: -result.score)

def get_clustered_results(domain, search_terms, filepath_of_urlmaps, db, sim_table, solr_collection, clusterproc_algs):
 
  # Conduct search & get results from solr
  search_results, returned_url_hashes = get_solr_query_response(solr_collection, search_terms)
  if len(search_results) == 0: 
    return []

  # Get distance matrix & list of urls
  dist_matrix = get_distance_matrix(search_results, returned_url_hashes, db, sim_table) 

  # Run clustering algorithm
  clusters = get_clusters(dist_matrix, clusterproc_algs.cluster)
  
  # Reformat as dict of "cluster_num":[search_results]
  clusters_of_search_results = reformat_to_clusters_of_results(clusters, search_results)

  # Get clusters summaries
  cluster_to_summaries = get_cluster_summaries(clusters_of_search_results, filepath_of_urlmaps, domain, clusterproc_algs.summary)

  all_clusters = []
  for cluster_str in clusters_of_search_results:
    cluster = ClusterOfSearchResults(cluster_str)
    cluster.add_search_results(clusters_of_search_results[cluster_str])
    cluster.set_summary(cluster_to_summaries[cluster_str])
    all_clusters.append(cluster)

  ranked_clusters = get_ranked_clusters(all_clusters, clusterproc_algs.rank)
  return ranked_clusters

def main(domain, search_terms, filepath_of_urlmaps, mysql_cnxn_opts, sim_table, solr_collection, clusterproc_algs):
  db = MySQLdb.connect(host=mysql_cnxn_opts.host, port=mysql_cnxn_opts.port,    
                       unix_socket=mysql_cnxn_opts.unix_socket,                 
                       user=mysql_cnxn_opts.user, passwd=mysql_cnxn_opts.password,
                       db=mysql_cnxn_opts.db)
  clusters = get_clustered_results(domain, search_terms, filepath_of_urlmaps, db, sim_table, solr_collection, clusterproc_algs)
  return clusters

"""
if __name__ == '__main__':
  if len(argv) < 3:
    print("Usage: try-clustering <searchQuery> <filepath_of_urlmaps>")
  else:
    searchTerms = argv[1]
    filepath_of_urlmaps = argv[2]
    mysql_cnxn_opts = MySQLDBConnectionOpts(
                        host='localhost', port=8888,
                        unix_socket="/Applications/MAMP/tmp/mysql/mysql.sock",
                        user='emon', passwd='',
                        db='test')
    sim_table = "all_page_similarities"
    main(searchTerms, filepath_of_urlmaps, mysql_cnxn_opts, sim_table)
"""
