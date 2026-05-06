#!/usr/bin/env python3
"""
Development utility script for Bagol Stremio Addon
Provides testing, running, and debugging commands
"""

import sys
import argparse
import subprocess
import requests
import logging
from scrapers import registry

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DevUtil:
    """Development utility class"""
    
    def __init__(self):
        self.port = 8008
        self.host = "localhost"
    
    # ========================================================================
    # Test Commands
    # ========================================================================
    
    def test_scrapers(self, scraper_id=None, query="test"):
        """Test scrapers"""
        logger.info(f"Testing scrapers with query: '{query}'")
        logger.info("")
        
        scrapers_to_test = []
        
        if scraper_id and scraper_id != "all":
            scraper = registry.get(scraper_id)
            if scraper:
                scrapers_to_test.append(scraper)
            else:
                logger.error(f"Scraper '{scraper_id}' not found")
                return False
        else:
            scrapers_to_test = registry.get_all()
        
        for scraper in scrapers_to_test:
            logger.info(f"Testing {scraper.SITE_NAME} ({scraper.SCRAPER_ID})...")
            
            try:
                # Search
                results = scraper.search(query)
                logger.info(f"  Search: Found {len(results)} results")
                
                # Get streams from first result
                if results:
                    first_url = results[0].get('url')
                    if first_url:
                        streams = scraper.get_streams(first_url)
                        logger.info(f"  Streams: Found {len(streams)} streams")
                        
                        # Show streams
                        for stream in streams[:3]:
                            logger.info(f"    - {stream.title} ({stream.sources})")
                    
                    logger.info(f"  ✓ OK")
                else:
                    logger.warning(f"  No search results")
                    
            except Exception as e:
                logger.error(f"  ✗ FAILED: {e}")
            
            logger.info("")
        
        return True
    
    def test_endpoint(self, endpoint=None):
        """Test API endpoints"""
        logger.info("Testing API endpoints...")
        logger.info("")
        
        base_url = f"http://{self.host}:{self.port}"
        
        endpoints = {
            "/health": "Health check",
            "/manifest.json": "Addon manifest",
            "/info": "Addon info",
            "/search/batman": "Search endpoint",
            "/stream/movie/test.json": "Stream endpoint",
        }
        
        if endpoint:
            if endpoint in endpoints:
                endpoints = {endpoint: endpoints[endpoint]}
            else:
                logger.error(f"Endpoint '{endpoint}' not found")
                return False
        
        for path, description in endpoints.items():
            url = base_url + path
            logger.info(f"Testing {description}: {path}")
            
            try:
                response = requests.get(url, timeout=5)
                logger.info(f"  Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"  Response: {len(str(data))} bytes")
                    logger.info(f"  ✓ OK")
                else:
                    logger.warning(f"  Status: {response.status_code}")
                    
            except requests.ConnectionError:
                logger.error(f"  ✗ Connection refused (is server running?)")
            except Exception as e:
                logger.error(f"  ✗ Error: {e}")
            
            logger.info("")
        
        return True
    
    def test_dependencies(self):
        """Check if all dependencies are installed"""
        logger.info("Checking dependencies...")
        logger.info("")
        
        dependencies = {
            'flask': 'Flask',
            'bs4': 'BeautifulSoup4',
            'requests': 'Requests',
            'gunicorn': 'Gunicorn'
        }
        
        missing = []
        
        for module, name in dependencies.items():
            try:
                __import__(module)
                logger.info(f"  ✓ {name}")
            except ImportError:
                logger.error(f"  ✗ {name} (missing)")
                missing.append(name)
        
        logger.info("")
        
        if missing:
            logger.error(f"Missing dependencies: {', '.join(missing)}")
            logger.info("Install with: pip install -r requirements.txt")
            return False
        
        logger.info("All dependencies OK!")
        return True
    
    # ========================================================================
    # Run Commands
    # ========================================================================
    
    def run_server(self, mode="development"):
        """Run the addon server"""
        logger.info(f"Running addon server in {mode} mode...")
        logger.info(f"URL: http://{self.host}:{self.port}/manifest.json")
        logger.info("")
        
        # Use start.sh
        cmd = ["bash", "start.sh", mode]
        subprocess.run(cmd)
    
    def run_tests(self):
        """Run all tests"""
        logger.info("Running all tests...")
        logger.info("")
        
        # Check dependencies
        if not self.test_dependencies():
            return False
        
        logger.info("")
        
        # Test scrapers
        if not self.test_scrapers("all", "test"):
            return False
        
        logger.info("")
        
        # Test endpoints
        logger.info("Make sure server is running: python dev.py run")
        
        return True
    
    # ========================================================================
    # Info Commands
    # ========================================================================
    
    def show_scrapers(self):
        """Show registered scrapers"""
        logger.info("Registered scrapers:")
        logger.info("")
        
        scrapers = registry.get_all()
        
        if not scrapers:
            logger.warning("No scrapers registered!")
            return
        
        for scraper in scrapers:
            logger.info(f"  {scraper.SITE_NAME}")
            logger.info(f"    ID: {scraper.SCRAPER_ID}")
            logger.info(f"    URL: {scraper.SITE_URL}")
            logger.info(f"    Logo: {scraper.LOGO_URL}")
            logger.info("")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Bagol Addon Development Utility',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dev.py test                    # Test all scrapers
  python dev.py test --scraper mangoporn --query "batman"
  python dev.py run                     # Run development server
  python dev.py run --production        # Run production server
  python dev.py endpoint                # Test all endpoints
  python dev.py endpoint /health        # Test specific endpoint
  python dev.py check                   # Check dependencies
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test scrapers')
    test_parser.add_argument('--scraper', help='Specific scraper ID (or "all")', default='all')
    test_parser.add_argument('--query', help='Search query', default='test')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run addon server')
    run_parser.add_argument('--production', action='store_true', help='Run in production mode')
    
    # Endpoint command
    endpoint_parser = subparsers.add_parser('endpoint', help='Test API endpoints')
    endpoint_parser.add_argument('path', nargs='?', help='Specific endpoint path')
    
    # Check command
    subparsers.add_parser('check', help='Check dependencies')
    
    # Info command
    subparsers.add_parser('info', help='Show scraper info')
    
    args = parser.parse_args()
    
    util = DevUtil()
    
    if not args.command:
        parser.print_help()
        return 0
    
    if args.command == 'test':
        success = util.test_scrapers(args.scraper, args.query)
        return 0 if success else 1
    
    elif args.command == 'run':
        mode = 'production' if args.production else 'development'
        util.run_server(mode)
        return 0
    
    elif args.command == 'endpoint':
        success = util.test_endpoint(args.path)
        return 0 if success else 1
    
    elif args.command == 'check':
        success = util.test_dependencies()
        return 0 if success else 1
    
    elif args.command == 'info':
        util.show_scrapers()
        return 0
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
