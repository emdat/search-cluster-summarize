import MySQLdb
from html2text import html2text
import ast
from joblib import Parallel, delayed
import multiprocessing
from sklearn.feature_extraction.text import TfidfVectorizer
from bs4 import BeautifulSoup, SoupStrainer
from sys import argv
from . import ConnectionClasses

similarity_columns = ["url_sim_score", "title_sim_score", "fulltext_sim_score",
                     "plaintext_sim_score"]

def strip_domain(domain, url):
  ind = 0
  try:
    ind = url.index(domain) + 1
  except Exception as e:
    print(repr(e))

  stripped_url = url[ind:]
  if stripped_url == "":
    stripped_url = " "
  return stripped_url

def add_sim_rows(cur, db, sim_rows, table, columns, sim_type, cur_url, cur_ind):
  query_str = ""
  try:
    query_str = "REPLACE INTO " + table + " " + columns + " VALUES" 
    query_str += ",".join(sim_rows)
    query_str += ";"
    cur.execute(query_str)
    db.commit()
    print("%d: %s | %s similarities" % (cur_ind + 1, cur_url, sim_type))    
  except Exception as e:
    print("Exception in inserting all sim scores: " + repr(e))
    print("FAILED ON ROW FOR URL " + str(cur_url))
    print("FAILED QUERY: " + query_str)
    db.rollback()

def insert_all_sim_rows(cur, db, sim_rows, table, columns, cur_url, cur_ind):
  query_str = ""
  try:
    query_str = "REPLACE INTO " + table + " " + columns + " VALUES" 
    query_str += ",".join(sim_rows)
    query_str += ";"
    cur.execute(query_str)
    db.commit()
    print("%d: %s | all similarities" % (cur_ind + 1, cur_url))    
  except Exception as e:
    print("Exception in inserting for all similarities: " + repr(e))
    print("FAILED ON ROW FOR URL " + str(cur_url))
    print("FAILED QUERY: " + query_str)
    db.rollback()

def compute_save_all_sim_scores(sim_score_list, url1, url2, all_to_compare):
    sim_score_tuple_str = "(MD5('" + url1 +"'), MD5('" + url2 + "'), "
    sim_score_tuple_str += "'" + url1 + "', '" + url2 + "', "
    try:
      sim_score_strs = []
      for pair_to_compare in all_to_compare:
        tfidf = TfidfVectorizer().fit_transform(pair_to_compare)
        pairwise_similarity = (tfidf * tfidf.T)[0,1]
        sim_score_strs.append(str(pairwise_similarity)) 
      sim_score_tuple_str += ", ".join(sim_score_strs) + ")"
      
      sim_score_list.append(sim_score_tuple_str)
    except Exception as e:
      print("FAILED ON URL %s, %s" % (url1, url2))
      print("Exception in all sim computation: " + repr(e))
  
def file_comp(cur_file_ind, num_files, url_to_file, domain, sim_table, mysql_cnxn_opts):
  
  db = MySQLdb.connect(host=mysql_cnxn_opts.host, port=mysql_cnxn_opts.port,
                       unix_socket=mysql_cnxn_opts.unix_socket,
                       user=mysql_cnxn_opts.user, passwd=mysql_cnxn_opts.password,
                       db=mysql_cnxn_opts.db)
  cur = db.cursor()
  

  # Retrieve file contents
  url1, fname1, fname_ptext1 = url_to_file[cur_file_ind]
  try:
    file1 = open(fname1, 'r').read()
    file_ptext1 = open(fname_ptext1, 'r').read()
  except Exception as e:
    print("Failed on file %d: %s" % (cur_file_ind, fname1))
    #print(repr(e))
    cur.close()
    return
  #print("START %d / %d : %s" % (cur_file_ind + 1, num_files - 1, url1))

  titleSoup = SoupStrainer("title")
  # Split file contents into url and (stripped?) html content
  # Parse out title
  url1_strip_dom = strip_domain(domain, url1)
  file1_title = url1
  try:
    file1_title = BeautifulSoup(file1, "lxml", parse_only=titleSoup).title.string
  except:
    print("couldnt get f1 title")
    pass
  try:
    file1 = html2text(file1)
  except:
    print("not html2text")

  all_sim_rows = []
  for i in range(cur_file_ind + 1, num_files, 1):
    
    url2, fname2, fname_ptext2 = url_to_file[i]
    try:
      file2 = open(fname2, 'r').read()
      file_ptext2 = open(fname_ptext2, 'r').read()
    except Exception as e:
      print(repr(e))
      cur.close()
      return
  
    # Split file contents into url and (stripped?) html content
    # Parse out title
    url2_strip_dom = strip_domain(domain, url2)
    file2_title = url2
    try:
      file2_title = BeautifulSoup(file2, "lxml", parse_only=titleSoup).title.string
    except:
      pass
    file2 = html2text(file2)

    # Compute and save similarity scores for page urls, titles, and text
    compute_save_all_sim_scores(all_sim_rows, url1, url2, 
                                [ [url1_strip_dom, url2_strip_dom],
                                  [file1_title, file2_title],
                                  [file1, file2],
                                  [file_ptext1, file_ptext2] ])

  # Attempt to insert similarity scores for all pairs involving the current url1
  columns = "(url1_hash, url2_hash, url1, url2, %s)" % (", ".join(similarity_columns)) 
  insert_all_sim_rows(cur=cur, db=db, sim_rows=all_sim_rows,
               table=sim_table, columns=columns,
               cur_url=url1, cur_ind=cur_file_ind) 

  cur.close()
  print("DONE %d / %d : %s" % (cur_file_ind + 1, num_files - 1, url1))

def compute_pair_similarities(file_with_urlmaps, domain, sim_table, mysql_cnxn_opts):
  url_to_file = []
  
  try:
    urls = set()
    with open(file_with_urlmaps, 'r') as f:
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
        url_to_file.append((cur_url, cur_file + ".html", cur_file + "_extracted.txt"))
  except Exception as e:
    print("Error:  " + repr(e))
    raise e

  num_files = len(url_to_file)

  num_cores = multiprocessing.cpu_count()
  print("num cores: " + str(num_cores))

  # Create SQL similarity tables if they do not exist
  db = MySQLdb.connect(host=mysql_cnxn_opts.host, port=mysql_cnxn_opts.port,
                       unix_socket=mysql_cnxn_opts.unix_socket,
                       user=mysql_cnxn_opts.user, passwd=mysql_cnxn_opts.password,
                       db=mysql_cnxn_opts.db)
  cur = db.cursor()
  create_all_similarities_table(db, cur, sim_table)
  cur.close()
  
  # Run parallel jobs to compute & save (in SQL tables) similarity scores
  # Note we only do this until num_files - 2 because the last file will
  # already have computed pairs with all previous files
  Parallel(n_jobs=num_cores)(delayed(file_comp)(cur_file_ind, num_files, url_to_file, domain, sim_table, mysql_cnxn_opts) for cur_file_ind in range(0, num_files - 1, 1));

def create_all_similarities_table(db, cur, tablename):
  create_query = "CREATE TABLE IF NOT EXISTS `" + tablename + "` "
  create_query += """ (
     `url1_hash` CHAR(32) NOT NULL,
     `url2_hash` CHAR(32) NOT NULL,
     `url1` TEXT NOT NULL,
     `url2` TEXT NOT NULL,
     """
  create_query += ", ".join([("`%s` double NOT NULL" % (col_str)) for col_str in similarity_columns])
  create_query += """,
     PRIMARY KEY (`url1_hash`,`url2_hash`),
     KEY `url1_hash` (`url1_hash`),
     KEY `url2_hash` (`url2_hash`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8
    """
  
  try:
    cur.execute(create_query)
    db.commit()
    print("Created table " + tablename)
  except Exception as e:
    print("Exception in creating table " + tablename + ": " + repr(e))
    db.rollback()

def main(file_with_urlmaps, domain, sim_table, mysql_cnxn_opts):
  compute_pair_similarities(file_with_urlmaps=file_with_urlmaps, domain=domain,
                            mysql_cnxn_opts=mysql_cnxn_opts,sim_table=sim_table)

"""
if __name__ == '__main__':
  if len(argv) != 4:
    print("Usage: compute-similarity.py <name of file with url maps> <domain_name> <page_similarity_table>")
  else: 
    file_with_urlmaps = argv[1]
    domain = argv[2]
    sim_table =  argv[3]
    mysql_cnxn_opts = ConnectionClasses.MySQLDBConnectionOpts(host='localhost', port=8888,                            
                       unix_socket="/Applications/MAMP/tmp/mysql/mysql.sock",  
                       user='emon', passwd='',
                       db='test')      
    main(file_with_urlmaps, domain, sim_table, mysql_cnxn_opts)
"""
