"""
Spider adapted from:
https://stackoverflow.com/questions/36837594/get-scrapy-spider-to-crawl-entire-site?utm_medium=organic&utm_source=google_rich_qa&utm_campaign=google_rich_qa
"""
import os
import shutil
import urllib.parse
import scrapy
from twisted.internet import reactor
from scrapy.crawler import CrawlerProcess, CrawlerRunner
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.selector import HtmlXPathSelector
from bs4 import BeautifulSoup, SoupStrainer

class MySpider(CrawlSpider):
  name = "Site/domain crawler"
  rules = [Rule(LinkExtractor(canonicalize=True,unique=True),follow=True,callback="parse_item")]
  
  def __init__(self, DOMAIN, URL, DIR, URLMAP_FILEPATH, *args, **kwargs):
    super(MySpider, self).__init__(*args, **kwargs)
    self.allowed_domains = [DOMAIN]  
    self.start_urls = [URL] 
    self.output_dir = DIR
    if (self.output_dir[-1] != "/"):
      self.output_dir += "/"
    self.output_urlmap_fpath = URLMAP_FILEPATH
    if os.path.exists(self.output_dir):
      shutil.rmtree(self.output_dir)
    os.makedirs(self.output_dir)
    self.long_url_cnt = 0

  # Method which starts the requests by visiting all URLs specified in start_urls
  def start_requests(self):
    for url in self.start_urls:
      yield scrapy.Request(url, callback=self.parse, dont_filter=True) 
  
  # Method for parsing items
  def parse_item(self, response):
    content_type = str(response.headers['Content-Type'])
    if content_type is None or "html" not in content_type:
      return []
    
    # Check if the url is actually in the domain
    in_domain = False
    filename = response.url
    netloc = urllib.parse.urlparse(response.url).netloc
    for domain in self.allowed_domains:
      if domain in netloc:
        in_domain = True
        filename = urllib.parse.quote(filename, safe="")
        break
    if not in_domain:
      return []
   
    # Check if filename too long
    # Have counter for ones that are too long 
    if len(filename) > 210:
      filename = filename[:200] + str(self.long_url_cnt)[:10]
      self.long_url_cnt += 1
   
    fpath = os.path.abspath(self.output_dir + filename) #+ ".html")
    with open(fpath + "_extracted.txt", 'w') as f:
      extracted_text = ""
      try:
        soup = BeautifulSoup(response.text, 'lxml',
                             parse_only = SoupStrainer(['h1','h2','h3','h4','h5','h6','p', 'title']))
        extracted_text = soup.get_text(separator='\n')
        f.write(extracted_text)
      except Exception as e:
        print("Skipping; couldn't extract h1-h6, p, title attributes from " + response.url)
        try:
          os.remove(fpath + "_extracted.txt")
        except OSError:
          pass
        return []
    with open(fpath + ".html", 'wb') as f:
      f.write(response.body)

    # Print for url:file mapping
    if os.path.exists(self.output_urlmap_fpath):
      append_write = 'a'
    else:
      append_write = 'w'
    with open(self.output_urlmap_fpath, append_write) as f:
      f.write(response.url + "\n")
      f.write(fpath + "\n")
    
    # The list of items that are found on the particular page
    return []

# Note that the Spider ensures the output_dir is created before having
# files created there.
def run_crawler(domain, domain_url, output_dir, urlmap_fpath):
  runner = CrawlerRunner({
      'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'
    })
  print("start crawling domain=%s" % (domain))
  d = runner.crawl(MySpider, DOMAIN=domain, URL=domain_url, DIR=output_dir, URLMAP_FILEPATH=urlmap_fpath)
  d.addBoth(lambda _: reactor.stop())
  reactor.run()
  print("done crawling domain\n")
  #process.start()
