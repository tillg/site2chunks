#!/bin/bash

# Run the scraper with recursive crawling enabled
# Use --recursive to discover and scrape linked pages from the same domain
# Use --ignore-scraping-state to start from scratch
python3 scrape.py urls.txt --recursive
