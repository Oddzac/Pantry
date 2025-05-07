from urllib.parse import urlparse
from typing import List, Dict, Any, Optional


class SiteFilter:
    """
    Filter for determining which sites to include or exclude from recipe scraping.
    """
    
    def __init__(self):
        """Initialize the SiteFilter with lists of domains to include or exclude."""
        # List of non-English language domains to skip
        self.non_english_domains = [
            # Dutch
            '.nl', '.be', 
            # German
            '.de', '.at', '.ch',
            # French
            '.fr',
            # Spanish
            '.es', '.mx', '.ar', '.co',
            # Italian
            '.it',
            # Portuguese
            '.pt', '.br',
            # Swedish
            '.se',
            # Norwegian
            '.no',
            # Danish
            '.dk',
            # Finnish
            '.fi',
            # Polish
            '.pl',
            # Czech
            '.cz',
            # Hungarian
            '.hu',
            # Russian
            '.ru',
            # Turkish
            '.tr',
            # Greek
            '.gr',
            # Japanese
            '.jp',
            # Korean
            '.kr',
            # Chinese
            '.cn', '.tw', '.hk',
            # Thai
            '.th',
            # Vietnamese
            '.vn'
        ]
        
        # List of non-English language keywords in URLs
        self.non_english_keywords = [
            # Dutch
            'recepten', 'koken', 'eten',
            # German
            'rezepte', 'kochen', 'essen',
            # French
            'recettes', 'cuisine', 'manger',
            # Spanish
            'recetas', 'cocina', 'comer',
            # Italian
            'ricette', 'cucina', 'mangiare',
            # Portuguese
            'receitas', 'cozinha', 'comer'
        ]
        
        # Specific domains to always include (even if they match non-English patterns)
        self.always_include = [
            'allrecipes.com',
            'foodnetwork.com',
            'epicurious.com',
            'simplyrecipes.com',
            'seriouseats.com',
            'bonappetit.com',
            'tasteofhome.com',
            'delish.com',
            'eatingwell.com',
            'food.com',
            'bbcgoodfood.com',  # English despite .com
            'kingarthurbaking.com',
            'sallysbakingaddiction.com',
            'budgetbytes.com',
            'minimalistbaker.com',
            'cookieandkate.com',
            'smittenkitchen.com',
            'thepioneerwoman.com',
            'skinnytaste.com',
            'damndelicious.net'
        ]
    
    def is_english_site(self, url: str) -> bool:
        """
        Check if a URL is likely to be an English language site.
        
        Args:
            url: URL to check
            
        Returns:
            bool: True if the site is likely in English, False otherwise
        """
        # Parse the URL to get the domain
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        path = parsed_url.path.lower()
        
        # Always include specific domains we know are in English
        for include_domain in self.always_include:
            if include_domain in domain:
                return True
        
        # Check for non-English TLDs
        for tld in self.non_english_domains:
            if domain.endswith(tld):
                return False
        
        # Check for non-English keywords in the domain or path
        for keyword in self.non_english_keywords:
            if keyword in domain or keyword in path:
                return False
        
        # Default to assuming it's English
        return True
    
    def filter_sites(self, sites: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter a list of sites to include only English language sites.
        
        Args:
            sites: List of site dictionaries with 'domain' keys
            
        Returns:
            List[Dict[str, Any]]: Filtered list of sites
        """
        return [site for site in sites if self.is_english_site(site['domain'])]


def main():
    """Test the site filter with some example URLs."""
    filter = SiteFilter()
    
    test_urls = [
        'https://www.allrecipes.com/',
        'https://www.foodnetwork.com/',
        'https://www.epicurious.com/',
        'https://www.bbcgoodfood.com/',
        'https://www.marmiton.fr/',
        'https://www.chefkoch.de/',
        'https://www.smulweb.nl/',
        'https://www.recetasgratis.es/',
        'https://www.giallozafferano.it/',
        'https://15gram.be/'
    ]
    
    print("Testing site filter:")
    for url in test_urls:
        is_english = filter.is_english_site(url)
        print(f"{url}: {'English' if is_english else 'Non-English'}")


if __name__ == '__main__':
    main()