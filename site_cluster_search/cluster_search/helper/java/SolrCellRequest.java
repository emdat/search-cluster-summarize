import java.io.IOException;
import java.io.FileReader;
import java.io.BufferedReader;
import java.io.File;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.nio.charset.Charset;
import java.util.ArrayList;
import org.apache.solr.client.solrj.SolrClient;
import org.apache.solr.common.util.NamedList;
import org.apache.solr.client.solrj.SolrServerException;
import org.apache.solr.client.solrj.impl.HttpSolrClient;
import org.apache.solr.client.solrj.request.AbstractUpdateRequest;
import org.apache.solr.client.solrj.request.ContentStreamUpdateRequest;

/*
 * Input: 1) solr_url, 2) collection_name, 3) filename of file with url:file maps 
 * For each file, send file info to be indexed with attributes 
 * use ?url/url hash? as id
 */
public class SolrCellRequest {

  private static class UrlAndFile {
    String url;
    String file;
  
    UrlAndFile(String u, String f) {
      this.url = u;
      this.file = f;
    }
  }

  public static void main (String[] args) throws IOException, SolrServerException {
    int len = args.length;
    if (len != 3) {
      System.out.println("Usage: SolrCellRequest <solr_url> <collection_name> <filename of url map>");
      return;
    }

    String solrUrl = args[0];
    String collectionName = args[1];
    String filenameOfUrlMaps = args[2];

    ArrayList<UrlAndFile> toIndex = getUrlsAndFilesToIndex(filenameOfUrlMaps);
    
    if (!solrUrl.endsWith("/")) solrUrl += "/";
    SolrClient solrClient = new HttpSolrClient.Builder(solrUrl + collectionName).build();
   
    int numFilesLeftToIndex = toIndex.size();
    for (UrlAndFile urlAndFile : toIndex) {
      // commit == true iff we're on the last file to index
      Boolean commit = (numFilesLeftToIndex-- == 1); 
      indexHTMLFileByUrl(solrClient, urlAndFile, commit); 
    }
  }

  private static ArrayList<UrlAndFile> getUrlsAndFilesToIndex(String filenameOfUrlMaps) {
    ArrayList<UrlAndFile> toIndex = new ArrayList<UrlAndFile> ();
    try {
			File file = new File(filenameOfUrlMaps);
			FileReader fileReader = new FileReader(file);
			BufferedReader bufferedReader = new BufferedReader(fileReader);
			String line1, line2;
			while ((line1 = bufferedReader.readLine()) != null) {
				line2 = bufferedReader.readLine();
        if (line2 == null) break; // Suggests a format problem with file of urls
        
        toIndex.add(new UrlAndFile(line1, line2));
			}
			fileReader.close();
    } catch (IOException e) {
      e.printStackTrace();  
    }

    return toIndex;
  }

  private static String getStringFromFile(String path, Charset encoding)
      throws IOException {
    return new String( Files.readAllBytes( Paths.get(path) ));  
  }
  
  private static void indexHTMLFileByUrl(SolrClient solrClient,
      UrlAndFile urlAndFile, Boolean commit)
      throws IOException, SolrServerException {
    ContentStreamUpdateRequest req =
      new ContentStreamUpdateRequest("/update/extract");
    req.addFile(new File(urlAndFile.file + ".html"), "text/html");
    String plaintext = getStringFromFile(urlAndFile.file + "_extracted.txt",
                                         Charset.forName("UTF-8"));
    // Note that general parameters for extraction should be set in the config file.
    req.setParam("literal.id", urlAndFile.url);
    req.setParam("literal.crawled_url", urlAndFile.url);
    req.setParam("literal._plaintext_", plaintext);
    if (commit) {
      req.setParam("commit", "true");  
    }
    
    try {
      NamedList<Object> result = solrClient.request(req);
      System.out.printf("SOLR post result for url %s: %s\n",
                      urlAndFile.url, result);
    } catch (Exception e) {
      System.out.println(urlAndFile.url);
      System.out.println(e.getMessage());  
    }
  }
}
