# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.
class DomainClusterSearchConfiguration(models.Model):
  # E.g., "makehaven.org"
  domain = models.CharField(max_length=255, unique=True, primary_key=True, blank=False)
  
  # E.g., "https://makehaven.org"
  domain_base_url = models.TextField() 
  
  # Directory to save crawled (html) pages & extracted plain-text to. 
  # E.g., "/Users/johnsmith/crawler/makehaven"
  crawled_page_output_dir = models.TextField() 

  # File with url_to_filepath maps.
  # By default, will be in crawled_page_dir/urls_to_files.txt,
  # e.g., "/Users/johnsmith/crawler/makehaven/urls_to_files.txt"
  file_of_urlmaps = models.TextField()

  # Base url of solr instance.
  # E.g., "http://localhost:8983/solr"
  solr_base_url = models.TextField()

  # Collection name to save domain pages' info in. 
  # E.g., "makehaven"
  solr_collection_name = models.CharField(max_length=255)

  # Number of shards for solr collection.
  solr_collection_num_shards = models.IntegerField(default=2)

  # Replication factor for solr collection.
  solr_collection_rep_factor = models.IntegerField(default=2)

  # Maximum number of shards per node for solr collection.
  solr_collection_max_shards_per_node = models.IntegerField(default=2)

  # Solr configset to use for this collection. 
  # Usually, "cluster_configs" should be used as it was made for this
  # use case specifically.
  solr_collection_configset = models.CharField(max_length=255,default="cluster_configs")

  # Field on which to add semantic search (by adding a field_blurred field)
  # in solr 
  semantic_search_field = models.CharField(max_length=250, default="_plaintext_")

  # MySQL host to connect to.
  mysql_host = models.CharField(max_length=250, default="localhost")

  # MySQL host to connect to.
  mysql_port = models.IntegerField(default="8888")

  # MySQL host to connect to.
  mysql_unix_socket = models.TextField(default="/tmp/mysql.sock")

  # MySQL user to use to connect.
  mysql_user = models.CharField(max_length=255,default="root")

  # MySQL password for user above.
  mysql_password = models.CharField(max_length=255,blank=True,default="")

  # MySQL database to connect to.
  mysql_database = models.CharField(max_length=255,default="test")
  
  # MySQL table to save url page similarity scores to
  # (includes url, title, and fulltext cosine TFIDF similarities).
  mysql_similarity_table = models.CharField(max_length=100,default="all_page_similarities")

  # Date of last update/crawl of domain
  last_updated = models.DateTimeField(auto_now=True)
  
  def __str__(self):
    return self.domain

class DomainClusterSearchQuery(models.Model):
  # E.g., "makehaven.org"
  domain = models.ForeignKey(DomainClusterSearchConfiguration, on_delete=models.CASCADE, blank=False)

  query = models.TextField()

  CLUSTER_ALG_CHOICES = (
        ('dbscan', 'dbscan'),
        ('hdbscan', 'hdbscan'),
        ('linkage-single', 'linkage-single'),
        ('linkage-complete', 'linkage-complete'),
        ('linkage-average', 'linkage-average'),
        ('linkage-weighted', 'linkage-weighted'),
        ('linkage-centroid', 'linkage-centroid'),
        ('linkage-median', 'linkage-median'),
        ('linkage-ward', 'linkage-ward'),
        ('affinity_propagation', 'affinity_propagation'),
    )
  cluster_algorithm = models.CharField(max_length=100,
                                       choices=CLUSTER_ALG_CHOICES,
                                       default='dbscan') 
  
  SUMMARY_ALG_CHOICES = (
        ('rake', 'rake'),
    )
  summary_algorithm = models.CharField(max_length=100,
                                       choices=SUMMARY_ALG_CHOICES,
                                       default='rake') 
  
  RANK_ALG_CHOICES = (
        ('max_score', 'max_score'),
        ('median_score', 'median_score'),
        ('sum_score', 'sum_score'),
    )
  rank_algorithm = models.CharField(max_length=100,
                                       choices=RANK_ALG_CHOICES,
                                       default='max_score') 
  
  def __str__(self):
    return (str(self.domain) + "?q=" + str(self.query) + 
           "&cluster_alg=" + str(self.cluster_algorithm) +
           "&summary_alg=" + str(self.summary_algorithm) +
           "&rank_alg=" + str(self.rank_algorithm))

