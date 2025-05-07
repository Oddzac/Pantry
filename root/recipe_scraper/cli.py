import argparse
import json
import sys
from pathlib import Path

# Add the parent directory to sys.path to import the recipe_scraper package
sys.path.append(str(Path(__file__).resolve().parents[1]))

from recipe_scraper import RecipeParser
from recipe_scraper.spider import RecipeSpider
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


def scrape_single_url(url, output_file=None):
    """
    Scrape a recipe from a single URL.
    
    Args:
        url: URL of the recipe to scrape
        output_file: Optional file to save the recipe to
    """
    parser = RecipeParser()
    
    try:
        recipe = parser.parse_url(url)
        recipe_dict = recipe.dict()
        
        # Print the recipe to stdout or save to file
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(recipe_dict, f, indent=2, ensure_ascii=False)
            print(f"Recipe saved to {output_file}")
        else:
            print(json.dumps(recipe_dict, indent=2, ensure_ascii=False))
        
        return True
    except Exception as e:
        print(f"Error scraping recipe from {url}: {str(e)}")
        return False


def crawl_website(start_url, output_dir, limit=None):
    """
    Crawl a website for recipes.
    
    Args:
        start_url: URL to start crawling from
        output_dir: Directory to save scraped recipes to
        limit: Maximum number of recipes to scrape
    """
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Set up the crawler
    settings = get_project_settings()
    settings.update({
        'FEEDS': {
            str(output_path / 'recipes.json'): {
                'format': 'json',
                'encoding': 'utf8',
                'indent': 2,
                'overwrite': True,
            },
        },
        'CLOSESPIDER_ITEMCOUNT': limit if limit else 0,  # 0 means no limit
        'LOG_LEVEL': 'INFO',
    })
    
    # Parse the domain from the start URL
    from urllib.parse import urlparse
    domain = urlparse(start_url).netloc
    
    # Create and configure the spider
    process = CrawlerProcess(settings)
    process.crawl(
        RecipeSpider,
        start_urls=[start_url],
        allowed_domains=[domain]
    )
    
    print(f"Starting to crawl {start_url} for recipes...")
    process.start()
    print(f"Crawling complete. Results saved to {output_path / 'recipes.json'}")


def main():
    """Main function for the CLI."""
    parser = argparse.ArgumentParser(description='Recipe Scraper CLI')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Parser for the 'scrape' command
    scrape_parser = subparsers.add_parser('scrape', help='Scrape a recipe from a URL')
    scrape_parser.add_argument('url', help='URL of the recipe to scrape')
    scrape_parser.add_argument('-o', '--output', help='Output file to save the recipe to')
    
    # Parser for the 'crawl' command
    crawl_parser = subparsers.add_parser('crawl', help='Crawl a website for recipes')
    crawl_parser.add_argument('url', help='URL to start crawling from')
    crawl_parser.add_argument('-o', '--output-dir', default='recipes', help='Directory to save scraped recipes to')
    crawl_parser.add_argument('-l', '--limit', type=int, help='Maximum number of recipes to scrape')
    
    args = parser.parse_args()
    
    if args.command == 'scrape':
        scrape_single_url(args.url, args.output)
    elif args.command == 'crawl':
        crawl_website(args.url, args.output_dir, args.limit)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()