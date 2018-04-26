"""
Adapted for my use case & for Python3 from code at:
https://github.com/o19s/SemanticSearchInNumpy/blob/master/SemanticExtraction/SemanticAnalyzer.py
"""

import requests
from collections import deque
class SolrTermVectorCollector(object):
    def __pathToTvrh(self, solrUrl, collection):
        import urllib.parse
        userSpecifiedUrl = urllib.parse.urlsplit(solrUrl)
        schemeAndNetloc = urllib.parse.SplitResult(scheme=userSpecifiedUrl.scheme,
                                               netloc=userSpecifiedUrl.netloc,
                                               path='',
                                               query='',
                                               fragment='')
        solrBaseUrl = urllib.parse.urlunsplit(schemeAndNetloc)
        solrBaseUrl = urllib.parse.urljoin(solrBaseUrl, 'solr/')
        solrBaseUrl = urllib.parse.urljoin(solrBaseUrl, collection + '/')
        solrBaseUrl = urllib.parse.urljoin(solrBaseUrl, 'tvrh')
        return solrBaseUrl
    
    def __init__(self, solrUrl="http://localhost:8983/solr",
            collection="collection1",
            field='Title',
            feature='tf-idf',
            batchSize=10000,
            numDocs=999999999):
        self.solrTvrhUrl = self.__pathToTvrh(solrUrl, collection)
        self.field = field
        self.feature = feature
        self.batchSize = batchSize
        self.numDocs = numDocs
        self.sess = requests.Session()
        self.count = 0

        self.termVectors = []

    def __iter__(self):
        return self

    def __next__(self):
        if self.count >= self.numDocs:
            raise StopIteration
        if len(self.termVectors) == 0:
            #then get some more!
            params = {"tv.fl": self.field,
                      "fl": "nonexistentfield",#to limit the volumn of data returned
                      "wt": "json",
                      "tv.all": "true",
                      "rows": min(self.batchSize, self.numDocs-self.count),
                      "start": self.count,
                      "q": self.field + ":*"}
            resp = self.sess.get(url=self.solrTvrhUrl, params=params)
            if resp.status_code != 200:
                print(resp.url)
                print(resp.text)
                raise IOError("HTTP Status " + str(resp.status_code))
            self.termVectors = deque(resp.json()['termVectors'][3::2])#overcoming weird non-dictionary json format
        if len(self.termVectors) == 0:
            #then Solr's our of documents
            raise StopIteration
        tv = self.termVectors.popleft()
        id = tv[1]
        termVector = {}
        data = tv[3] #all of the terms and features in this vector
        for i in range(0,len(data),2):
            term = data[i]
            featureValue = [data[i+1][j+1] for j in range(len(data[i+1])) if data[i+1][j] == self.feature][0]
            termVector[term] = featureValue
        self.count += 1
        return (id, termVector)



from collections import defaultdict
class StringIndexDict(object):
    """
    A 2-way dict-like object that only has functionality for getting and item.
    If you get with a string key, it will return the integer associated with that key.
    If you get with a integer key, it will return the string associated with that key.
    If you get an item that's currently not there, then the dict will return the next available
    integer (unique) and return that. If you call freeze on the dict, then nothing more
    can be added to it.
    """
    def __init__(self):
        self.currentIndex = -1
        self.stringDict = defaultdict(self._increment)
        self.indexDict = {}

    def _increment(self):
        self.currentIndex += 1
        self.indexDict[self.currentIndex] = self.keyInQuestion #kinda funky, but since this will always be single threaded, it's ok
        return self.currentIndex

    def __getitem__(self,key):
        self.keyInQuestion = key
        if isinstance(key,str):
            return self.stringDict[key]
        else :
            return self.indexDict[key]

    def size(self):
        return self.currentIndex + 1

    def freeze(self):
        #allow no more changes
        self.stringDict.default_factory = None



import scipy.sparse
import numpy
import sparsesvd
class TermDocCollection(object):
    def __init__(self,source=None,numTopics=10):
        self._docDict = StringIndexDict()
        self._termDict = StringIndexDict()
        self._termVectors = []
        self.numTopics = numTopics
        for termVector in source:
            self._termVectors.append( #append tuple of (docNum, {termNum_i,numberOccurrences_i})
                (
                    self._docDict[termVector[0]],
                    {self._termDict[k]:v for k,v in termVector[1].items()}
                )
            )
        self._termDict.freeze()
        self._docDict.freeze()
        self.numTerms = self._termDict.size()
        self.numDocs = self._docDict.size()

        #memoized later:
        self._svd = None
        self._cscMatrix = None
        self._uPrime = None
        self._uStripped = None


    def _getCscMatrix(self):#compressed sparse column matrix
        if self._cscMatrix is not None:
            return self._cscMatrix
        num_nnz, data, indices, indptr = 0, [], [], [0]
        for termVector in self._termVectors:
            newIndices = [i for i in termVector[1].keys()]
            newValues = [v for v in termVector[1].values()]
            indices.extend(newIndices)
            data.extend(newValues)
            num_nnz += len(newValues)
            indptr.append(num_nnz)
        data = numpy.asarray(data)
        indices = numpy.asarray(indices)
        self._cscMatrix = scipy.sparse.csc_matrix((data, indices, indptr),
                shape=(self.numTerms, self.numDocs))
        return self._cscMatrix

    def _getSvd(self):
        if self._svd is not None:
            return self._svd
        self._svd = sparsesvd.sparsesvd(self._getCscMatrix(), self.numTopics)
        return self._svd

    def _getUprime(self):
        if self._uPrime is not None:
            return self._uPrime
        u,s,v = self._getSvd()
        self._uPrime = numpy.dot(u.T,numpy.diag(s))
        return self._uPrime

    def getBlurredTerms(self,doc,cutoff):
        if isinstance(doc,str):
            doc = self._docDict[doc]
        uPrime = self._getUprime()
        _,_,v = self._getSvd()
        blurredField = numpy.dot(uPrime,v[:,doc])
        tokenIds = numpy.where(blurredField>cutoff)[0]
        tokens = [self._termDict[id] for id in tokenIds]
        return (self._docDict[doc], tokens)

    def _getStrippedUprime(self):
        #returns uPrime except that each word is only associated with their maximum 
        #score in any topic (all other values are set to 0). This might give better 
        #results for topic word lists
        if self._uStripped is not None:
            return self._uStripped
        uPrime = self._getUprime()
        uStripped = numpy.zeros(uPrime.shape)
        for termIndex in range(uPrime.shape[0]):
            maxIndex = numpy.argmax(uPrime[termIndex])
            uStripped[termIndex,maxIndex] = uPrime[termIndex,maxIndex]
        self._uStripped = uStripped
        return uStripped

    def getTopic(self,topicNum,cutoff,stripped=True):
        if stripped:
            u = self._getStrippedUprime()
        else:
            u = self._getUprime()

        return  [self._termDict[i] 
                    for i in numpy.where(u.T[topicNum]>cutoff)[0]
                ]
        
    def getRelatedTerms(self,token,numTerms,tokens_only=True):
        uP = self._getUprime()
        termDict = self._termDict
        u,_,_ = self._getSvd()
        strength_and_indices = sorted( zip(numpy.dot(uP[termDict[token]],u),range(len(uP))) , reverse=True )
        method = 0
        if tokens_only:
            method = lambda i: termDict[i[1]]
        else:
            method = lambda i: (termDict[i[1]],i[0])
        return  [ method(i) for i in strength_and_indices[:numTerms] ]


class SolrBlurredTermUpdater(object):
    def __pathToUpdate(self, solrUrl, collection):
        #TODO there is plenty of stuff duplicated in __pathToTvrh above - DRY
        import urllib.parse
        userSpecifiedUrl = urllib.parse.urlsplit(solrUrl)
        schemeAndNetloc = urllib.parse.SplitResult(scheme=userSpecifiedUrl.scheme,
                                               netloc=userSpecifiedUrl.netloc,
                                               path='',
                                               query='',
                                               fragment='')
        solrBaseUrl = urllib.parse.urlunsplit(schemeAndNetloc)
        solrBaseUrl = urllib.parse.urljoin(solrBaseUrl, 'solr/')
        solrBaseUrl = urllib.parse.urljoin(solrBaseUrl, collection + '/')
        solrBaseUrl = urllib.parse.urljoin(solrBaseUrl, 'update')
        return solrBaseUrl

    def __init__(self,
            termDocCollector,
            blurredField,
            solrUrl="http://localhost:8983/solr",
            collection="collection1",
            idField='Id',
            batchSize=1000):
        self.termDocCollector = termDocCollector
        self.solrUpdateUrl = self.__pathToUpdate(solrUrl, collection)
        self.batchSize = batchSize
        self.sess = requests.Session()
        self.batchSize = batchSize
        self.numDocs = termDocCollector.numDocs
        self.docString = u"""
            <doc>
                <field name="{0}">{1}</field>
                <field name="{2}" update="set">{3}</field>
            </doc>""".format(idField,"{0}",blurredField,"{1}")


    def pushToSolr(self,cutoff):
        #TODO create an iterator in the TermDocCollector for this
        for i in range(0,self.numDocs,self.batchSize): 
            docs = [self.termDocCollector.getBlurredTerms(j,cutoff)
                    for j in range(i,min(i+self.batchSize,self.numDocs))]
            docStrings = []
            for doc in docs:
                    docStrings.append(self.docString.format(doc[0]," ".join(doc[1])))
            docStrings = " ".join(docStrings).encode('ascii','xmlcharrefreplace')

            #TODO also needs to be DRYed per the comment above - considr making a lightweight Solr client
            params = {'commit': 'true'}
            headers = {'content-type': 'application/xml'}
            resp = requests.post(self.solrUpdateUrl,
                    u"<add>{0}</add>".format(docStrings),
                    params=params,headers = headers)
            if resp.status_code != 200:
              print("Blurred field probably didn't exist before. Trying again.")
              resp = requests.post(self.solrUpdateUrl,
                      u"<add>{0}</add>".format(docStrings),
                      params=params,headers = headers)
              if resp.status_code != 200:
                print(resp.text)  
                raise IOError("HTTP Status " + str(resp.status_code))
            
            
#############################################

def say(a_list):
    print(" ".join(a_list))

def main(field,collection,solrUrl):
    print("COLLECTING TERMS")
    stvc = SolrTermVectorCollector(field=field,feature='tf',batchSize=1000, collection=collection, solrUrl=solrUrl)
    tdc = TermDocCollection(source=stvc,numTopics=150)

    """
    print("DEMO AUTOGEN SYNONYMS FOR DOCUMENTS")
    print("\n**star wars document**")
    say(tdc.getBlurredTerms('20710',0.2)[1])
    print("**harry potter document**")
    say(tdc.getBlurredTerms('17250',0.1)[1])

    print("\nDEMO TERM SIMILARITY")
    print("**kirk**")
    say(tdc.getRelatedTerms('kirk',30))
    print("**potter**")
    say(tdc.getRelatedTerms('potter',30))
    print("**vader**")
    say(tdc.getRelatedTerms('vader',30))
    print("**power**")
    say(tdc.getRelatedTerms('power',30))
    print("**frodo**")
    say(tdc.getRelatedTerms('frodo',30))
    """
    
    print("\nDEMO TERM SIMILARITY")
    print("**project**")
    #say(tdc.getRelatedTerms('project',30))
    print("**code**")
    #say(tdc.getRelatedTerms('code',30))

    print("\nSENDING UPDATES TO SOLR")
    SolrBlurredTermUpdater(tdc,blurredField= field + "blurred", collection=collection, solrUrl=solrUrl).pushToSolr(0.1)
    print("done")

"""
if __name__ == "__main__":
    from sys import argv
    if not (len(argv) == 3 or len(argv) == 4):
        raise Exception("usage: python SemanticAnalyzer.py solrUrl collection [fieldname]")

    solrUrl = argv[1]
    if solrUrl[-1] == '/':
      solrUrl = solrUrl[:-1]
    collection = argv[2]
    field = argv[3] if len(argv) > 3 else "_text_"
    main(field, collection, solrUrl)
"""
