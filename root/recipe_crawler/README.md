# Recipe Crawler

A robust and intelligent crawler for finding recipes on websites, even those with anti-scraping measures.

## Overview

The Recipe Crawler package provides tools for crawling websites to find recipe URLs. It includes:

1. **URL Analyzer**: Analyzes URLs to determine if they are likely recipe pages, category pages, or other types.
2. **Recipe Detector**: Analyzes page content to determine if it contains a recipe.
3. **Browser Crawler**: Uses a headless browser to access websites that block traditional crawlers.

## Features

- **Intelligent URL Analysis**: Recognizes common URL patterns for recipes and categories.
- **Content-Based Recipe Detection**: Analyzes page content to identify recipes.
- **Anti-Scraping Measures**: Uses a headless browser to bypass anti-scraping measures.
- **Curiosity-Driven Crawling**: Explores promising paths to find more recipes.

## Usage

### Basic Usage

```python
from root.recipe_crawler.browser_crawler import BrowserCrawler

# Create a browser crawler
crawler = BrowserCrawler()

# Find recipe URLs on a website
recipes = crawler.find_recipe_urls('https://theloopywhisk.com', max_urls=5)
print(f'Found recipes: {recipes}')
```

### Integration with ParallelScraper

The browser crawler is integrated with the ParallelScraper class to provide a fallback for sites with anti-scraping measures:

```python
from root.recipe_scraper.parallel_scraper import ParallelScraper

# Create a parallel scraper with browser crawler enabled
scraper = ParallelScraper(
    db_path='path/to/database.db',
    max_workers=4,
    use_browser_crawler=True
)

# Build a recipe library
stats = scraper.build_recipe_library(
    sites=sites,
    limit=10,
    recipes_per_site=2
)
```

## Requirements

- Python 3.6+
- Selenium
- webdriver-manager
- BeautifulSoup4
- Requests

## Installation

```bash
pip install selenium webdriver-manager
```

## How It Works

1. **URL Analysis**: The URL analyzer examines URL patterns to identify recipe and category pages.
2. **Content Analysis**: The recipe detector analyzes page content to identify recipes.
3. **Browser Automation**: The browser crawler uses Selenium to automate a headless Chrome browser.
4. **Curiosity-Driven Crawling**: The crawler explores promising paths to find more recipes.

## Handling Anti-Scraping Measures

The browser crawler uses several techniques to bypass anti-scraping measures:

1. **Browser Emulation**: Uses a full Chrome browser instance that executes JavaScript.
2. **User-Agent Rotation**: Randomly selects a user agent for each request.
3. **Fingerprint Evasion**: Disables automation flags and adds browser-like headers.
4. **Human-Like Behavior**: Simulates scrolling and adds delays between actions.
5. **Alternative Entry Points**: Tries different entry points if the main URL is blocked.

## Known Anti-Scraping Sites

The crawler has special handling for these sites with known anti-scraping measures:

- theloopywhisk.com
- nytimes.com
- cooking.nytimes.com
- bonappetit.com
- epicurious.com
- foodandwine.com
- seriouseats.com
- smittenkitchen.com
- thekitchn.com