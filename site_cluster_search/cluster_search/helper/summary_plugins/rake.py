import cluster_search.helper.PluginClasses as PluginClasses
from cluster_search.helper.ResultClasses import SearchResult
from rake_nltk import Rake
import re
from nltk.corpus import stopwords
import string 
from collections import Counter

class rake(PluginClasses.ISummaryPlugin):
  last_domain_searched = ""
  rake_extractor = Rake()
  regex_nonalnum_keywords = re.compile('(^,+)|(,+$)|([^0-9A-Za-z]+,+)')
  max_chars_read = 10000
  max_phrases_saved = 20
  approx_char_length = 50

  # Add words in the domain as stopwords as they will likely occur in all
  # pages and not be useful as cluster descriptors.
  def custom_rake_extractor(self, domain):
      domain_minus_tld = domain.rpartition('.')[0]
      domain_parts = re.sub('\\.', ' ', domain_minus_tld)
      domain_words = re.sub('[^a-zA-Z0-9]+', ' ', domain_parts)
      domain_words2 = re.sub('([0-9]+)', ' \1 ', domain_words)
      domain_words_set = set(domain_parts.split())
      domain_words_set.update(domain_words.split())
      domain_words_set.update(domain_words2.split())
      my_stopwords = set(stopwords.words('english')).union(domain_words_set)
      return Rake(my_stopwords, string.punctuation)

  # Remove words from the summaries that occur >= threshold number of times.
  def remove_overly_common_keywords(self, counter, cluster_to_summaries, threshold):
    common_words = []
    threshold = max(2, threshold)
    for word, occurrences in counter.items():
      if occurrences >= threshold:
        common_words.append(re.escape(word))

    remove_str = '|'.join(common_words)
    regex_common_words = re.compile(r'\b('+remove_str+r')\b',
                                    flags=re.IGNORECASE)
    
    return {cluster : regex_common_words.sub("", keywords)
            for cluster, keywords in cluster_to_summaries.items()}

  def clip_long_summaries(self, cluster_to_summaries):
    for cluster, summary in cluster_to_summaries.items():
      
      if len(summary) > self.approx_char_length:
        comma_ind = summary.find(',', self.approx_char_length)
        
        if comma_ind != -1:
          summary = summary[:comma_ind]
          cluster_to_summaries[cluster] = summary

    return cluster_to_summaries
  
  def summarize_clusters(self, url_to_text_file, clusters_of_search_results, domain=""):
    if domain != "" and domain != self.last_domain_searched:
      self.rake_extractor = self.custom_rake_extractor(domain)

    cluster_to_summaries = {}
    all_keywords  = []
    for cluster_str, results_list in clusters_of_search_results.items():          
      try:                                                                        
        # Get string of text from all files in cluster                            
        urls = [res.url for res in results_list]                                  
        file_texts = []                                                           
        filepaths = [url_to_text_file[url] for url in urls]             
        for fpath in filepaths:
          try:
            with open(fpath, 'r') as f:                                             
              file_texts.append(f.read()[:self.max_chars_read])                                           
          except:
            print("couldn't open " + fpath)
            pass
        text = '\n'.join(file_texts)                                              
                                                                                  
        # Save summaries for cluster                                              
        self.rake_extractor.extract_keywords_from_text(text)                           
        keyphrases = self.rake_extractor.get_ranked_phrases()
        if len(keyphrases) > self.max_phrases_saved:
          keyphrases = keyphrases[:self.max_phrases_saved]
        unique_keywords = set()
        for keyphrase in keyphrases:
          unique_keywords.update(keyphrase.split())
        all_keywords.extend(unique_keywords)
        cluster_to_summaries[cluster_str] = ", ".join(keyphrases)
      except Exception as e:                                                      
        print("Error getting summaries from cluster " + cluster_str + ": " + repr(e))
        cluster_to_summaries[cluster_str] = ""                                    
        continue                                                                  
  
    # Remove words that occur in more than half the clusters' keywords, as they
    # are likely not useful as distinct descriptors.
    half_nclusters = len(clusters_of_search_results) / 2
    cluster_to_summaries = self.remove_overly_common_keywords(
                                                         Counter(all_keywords),
                                                         cluster_to_summaries,
                                                         half_nclusters)
    
    # Remove non alphanumeric keywords/keyphrases (e.g., ",,," or "-,,"
    cluster_to_summaries = {cluster : self.regex_nonalnum_keywords.sub("", keywords)
                            for cluster, keywords in cluster_to_summaries.items()}
    # Clips long summaries    
    cluster_to_summaries = self.clip_long_summaries(cluster_to_summaries)
    return cluster_to_summaries                       
  
