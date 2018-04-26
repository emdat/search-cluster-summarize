def create_solr_collection(solr_url, collection_name, num_shards=2, replication_factor=2, max_shards_per_node=2, config_name=None):
	req_base = solr_url + "admin/collections"
	payload = {"action":"CREATE", "name":collection_name,
						 "numShards":num_shards,
						 "replicationFactor":replication_factor,
						 "maxShardsPerNode":max_shards_per_node,
						 "collection.configName":config_name}
	r = requests.post(req_base, params=payload)
	print(r.url)
	print(r.text)
	r.raise_for_status()

def enable_soft_commits(solr_url, collection_name, max_secs=3):
	req_base = solr_url + collection_name + "/config
def post_to_solr(solr_url, collection_name)
	

if __name__ == '__main__':
  if len(argv) != 3:
    print("Usage: compute-similarity.py <downloads_directory> <domain_name>")
    return
  downloads_dir = argv[1]
  domain = argv[2]
  compute_pair_similarities(downloads_dir=downloads_dir, domain=domain)
