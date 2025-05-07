"""
Scrapy settings for the recipe crawler.
"""

BOT_NAME = 'recipe_crawler'

SPIDER_MODULES = ['root.recipe_crawler.spiders']
NEWSPIDER_MODULE = 'root.recipe_crawler.spiders'

# Obey robots.txt rules, but with some flexibility
ROBOTSTXT_OBEY = False  # Changed to False to bypass some restrictions

# Configure maximum concurrent requests (reduced to be more gentle)
CONCURRENT_REQUESTS = 2

# Configure a delay for requests for the same website (increased to avoid detection)
DOWNLOAD_DELAY = 3
RANDOMIZE_DOWNLOAD_DELAY = True

# Disable cookies to avoid tracking
COOKIES_ENABLED = False

# Configure item pipelines
ITEM_PIPELINES = {
}

# Enable and configure the AutoThrottle extension
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 3
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
AUTOTHROTTLE_DEBUG = False

# Set the default User-Agent to a modern browser
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Enable or disable downloader middlewares
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': 90,
    'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
    'scrapy.downloadermiddlewares.redirect.RedirectMiddleware': 800,
}

# Configure retry settings
RETRY_ENABLED = True
RETRY_TIMES = 5  # Increased retry attempts
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429, 403]  # Added 403 to retry codes

# Configure redirect settings
REDIRECT_ENABLED = True
REDIRECT_MAX_TIMES = 5

# Configure HTTP caching (helps avoid re-downloading unchanged pages)
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 86400  # 24 hours
HTTPCACHE_DIR = 'httpcache'
HTTPCACHE_IGNORE_HTTP_CODES = [403, 404, 500, 502, 503, 504]

# Configure logging
LOG_LEVEL = 'INFO'

# Configure request headers
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
    'DNT': '1',
}