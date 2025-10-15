I would like to extend my scraper to scrape also the pages that are refrenced on the pages he sees. 

* Keep track of the pages that are to be scraped in an array memory: urls_to_scrape
* At the beginning of a run this array is initialized with the entries in urls.txt
* Every page that is scraped is the scanned for url's it contains:
  * If the url points to a page of the same domain
  * Expand it, i.e. make it from a relative to an absolute url
  * Add it to the array in memory
  * Write the array in memory to a file urls_to_scrape.txt
* Also keep track of the urls that have been already scraped, so to avoid re-scraping them just because they are referenced again: urls_scraped
* The array of already scraped url's should also be written to a text file every time it changes: urls_scraped.txt
* This way, even when a scraping process is interrupted, it can be re-started where it was stopped: It simply reads the 2 files urls_to_scrape.txt and urls_scraped.txt and continues. 
* If I want to start a scraping process from scratch
  * either I delete the files before starting it
  * or I pass in a cli option -ignore_scraping_state
