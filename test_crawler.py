from root.recipe_crawler.browser_crawler import BrowserCrawler

crawler = BrowserCrawler()
recipes = crawler.find_recipe_urls('https://theloopywhisk.com', max_urls=3)
print(f'Found recipes: {recipes}')