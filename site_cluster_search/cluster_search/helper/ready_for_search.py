from . import crawlspider
from . import SolrSemanticSearchEnabler
from . import compute_similarity
from . import ConnectionClasses
import os
import requests
import subprocess

def main(domain, domain_base_url, crawl_output_dir, urlmap_filepath,
         mysql_cnxn_opts, mysql_sim_table, solr_col, semantic_search_field):
  cur_dir = os.path.dirname(os.path.abspath(__file__))

  # 1) Crawling
  spider_dir = os.path.join(cur_dir, "crawlspider.py")
  cmd_to_run_crawler = (
                       "scrapy runspider %s "
                       "-a DOMAIN=%s -a URL=%s "
                       "-a DIR=%s -a URLMAP_FILEPATH=%s "
                       "" ) % (
                       spider_dir, domain, domain_base_url,
                       crawl_output_dir, urlmap_filepath)
  print(cmd_to_run_crawler)
  subprocess.call(cmd_to_run_crawler, shell=True)
  
  # 2) Create collection
  create_col_req = (
                   "%s/admin/collections?action=CREATE&"
                   "name=%s&numShards=%d&replicationFactor=%d&"
                   "maxShardsPerNode=%d&collection.configName=%s") % (
                   solr_col.base_url,
                   solr_col.collection_name, solr_col.num_shards,
                   solr_col.rep_factor, solr_col.max_shards_per_node,
                   solr_col.configset)
  resp = requests.post(create_col_req)
  if resp.status_code != 200 and ("already exists" not in resp.text):
    print(resp.url)
    print(resp.text)
    raise IOError("HTTP Status Code err when trying to create collection")
  # 3) Post files using java
  java_solrcell_dir = os.path.join(cur_dir, "java")
  java_dir_with_solr_jars = os.path.join(cur_dir, "java/solr_jar_files")
  java_solrcell_req_file = os.path.join(cur_dir, "java/SolrCellRequest.java")
  compile_java_solr_req = "javac -cp %s/solr-solrj-7.3.0.jar %s" % (
                          java_dir_with_solr_jars, java_solrcell_req_file)
  run_java_solr_req = "java -cp %s:%s/* SolrCellRequest %s %s %s" % (
                       java_solrcell_dir, java_dir_with_solr_jars,
                       solr_col.base_url, solr_col.collection_name,
                       urlmap_filepath)
  compile_and_run_java_solr_req = "%s; %s" % (
                                  compile_java_solr_req, run_java_solr_req)
  print("start java program to index files")
  subprocess.Popen(compile_and_run_java_solr_req, shell=True).wait()
  print("finish java program to index files")
  # 4) Compute Document/Page Similarities and Post to SQL
  compute_similarity.main(file_with_urlmaps=urlmap_filepath,
                          domain=domain, sim_table=mysql_sim_table,
                          mysql_cnxn_opts=mysql_cnxn_opts)
  # 5) Add Semantic Search Capabilities
  try:
    SolrSemanticSearchEnabler.main(field=semantic_search_field,
                                   collection=solr_col.collection_name,
                                   solrUrl=solr_col.base_url)
  except Exception as e:
    print("Error with SOLR Semantic Search Enabler: " + repr(e))

