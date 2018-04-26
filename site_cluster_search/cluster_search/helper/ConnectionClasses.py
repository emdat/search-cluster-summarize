class MySQLDBConnectionOpts:
  def __init__(self, host, port, unix_socket, user, password, database):
    self.host = host
    self.port = port
    self.unix_socket = unix_socket
    self.user = user
    self.password = password
    self.db = database

class SOLRCollectionCreateOpts:
  def __init__(self, base_url, collection_name, num_shards, rep_factor, max_shards_per_node, configset):
    self.base_url = base_url.rstrip("/")
    self.collection_name = collection_name
    self.num_shards = num_shards
    self.rep_factor = rep_factor
    self.max_shards_per_node = max_shards_per_node
    self.configset = configset

class SOLRCollection:
  def __init__(self, base_url, collection_name):
    self.base_url = base_url.rstrip("/")
    self.collection_name = collection_name

