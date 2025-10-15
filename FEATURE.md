I want to provide restrictions as to which pages should be skipped, i.e. not scraped:

* By url shape: "https://www.hackingwithswift.com/users/*" should be interpreted as "all pages under https://www.hackingwithswift.com/users/ should be ignored"
* by no of hops, i.e. only go 2 hops further from the pages that are listed in urls.txt

This configuration should be written in a scrape_config.yaml:
* which is the file with the urls to scrape (for ex. urls.txt)
* skip: what pages should be skipped
* recursive: true/false
* out: /scrapes // where the scrape md files belong

If there is a scrape_config.yaml and i launch ./scrape.py it should feed it's config from there.