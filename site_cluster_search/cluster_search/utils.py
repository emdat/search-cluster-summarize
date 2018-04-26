# Helper functions
from .models import * 
from .helper import ready_for_search
from .helper.ConnectionClasses import *
from .helper import clustering
from .helper.ClusterProcessAlgorithmsClass import *

def get_mysql_cnxn_opts_from_config(domainClusterSearchConfiguration):
  dcsc = domainClusterSearchConfiguration
  mysql_cnxn_opts = MySQLDBConnectionOpts(dcsc.mysql_host, dcsc.mysql_port,
                                         dcsc.mysql_unix_socket,
                                         dcsc.mysql_user, dcsc.mysql_password,
                                         dcsc.mysql_database)
  return mysql_cnxn_opts

def make_domain_ready_for_search(domainClusterSearchConfiguration):
  dcsc = domainClusterSearchConfiguration
  domain = dcsc.domain
  domain_base_url = dcsc.domain_base_url.rstrip("/")
  crawl_output_dir = dcsc.crawled_page_output_dir.rstrip("/")
  urlmap_filepath = dcsc.file_of_urlmaps
  mysql_sim_table = dcsc.mysql_similarity_table
  semantic_search_field = dcsc.semantic_search_field
  mysql_cnxn_opts = get_mysql_cnxn_opts_from_config(dcsc) 
  solr_collection_create_opts = SOLRCollectionCreateOpts(dcsc.solr_base_url,
                                                         dcsc.solr_collection_name,
                                                         dcsc.solr_collection_num_shards,
                                                         dcsc.solr_collection_rep_factor,
                                                         dcsc.solr_collection_max_shards_per_node,
                                                         dcsc.solr_collection_configset)
  print("START GETTING DOMAIN READY")
  ready_for_search.main(domain, domain_base_url, crawl_output_dir,
                               urlmap_filepath, mysql_cnxn_opts, mysql_sim_table,
                               solr_collection_create_opts,
                               semantic_search_field)
  print("DONE GETTING DOMAIN READY")

def get_search_results(domainClusterSearchConfiguration, query):
  dcsc = domainClusterSearchConfiguration
  solr_collection = SOLRCollection(dcsc.solr_base_url,
                                   dcsc.solr_collection_name)
  return clustering.get_ranked_search_results(query, solr_collection)  

def get_clustered_search_results(domainClusterSearchConfiguration, query, cluster_alg, summary_alg, rank_alg):
  dcsc = domainClusterSearchConfiguration
  domain = dcsc.domain
  mysql_cnxn_opts = get_mysql_cnxn_opts_from_config(dcsc) 
  solr_collection = SOLRCollection(dcsc.solr_base_url,
                                   dcsc.solr_collection_name)
  clusterproc_alg = ClusterProcessAlgorithms(cluster_alg, summary_alg, rank_alg)
  clusters = clustering.main(domain, query, dcsc.file_of_urlmaps,
                             mysql_cnxn_opts, dcsc.mysql_similarity_table,
                             solr_collection, clusterproc_alg)
  return clusters
