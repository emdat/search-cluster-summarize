import re 

class ClusterOfSearchResults:                                                   
	def __init__(self, id):                                                       
		self.id = id                                                                
		self.size = 0                                                               
		self.results = []                                                           
		self.summary_str = ""                                                       
																																								
	def add_search_results(self, search_results):                                 
		for search_result in search_results:                                        
			self.add_search_result(search_result)                                     
																																								
	def add_search_result(self, search_result):                                   
		self.size += 1                                                              
		self.results.append(search_result)                                          
																																								
	def set_summary(self, summary):                                               
		self.summary_str = summary                                                  
																																								
class SearchResult:                                                             
	def __init__(self, url, title, highlight, score):                             
		self.url = url                                                              
		self.title = title                                                          
		self.highlight = highlight                                                  
		self.score = score                                                          
		self.highlight_str = re.sub('[\t\n\r\f\v]', ' ', highlight)
