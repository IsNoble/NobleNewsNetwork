#!/usr/bin/env python3
"""
Test script for the Warhammer Community News Discord Bot.
This script tests the scraping functionality without posting to Discord.
"""

import json
from datetime import date
from warhammer_news_discord_bot import WarhammerNewsScraper, CONFIG

def main():
    """Main function to test the scraper."""
    print("=" * 60)
    print(" Warhammer Community News Scraper Test")
    print("=" * 60)
    print("\nThis script will test the scraping functionality without posting to Discord.")
    print("It will fetch articles from the Warhammer Community website and display them.")
    
    # Show current configuration
    print("\nCurrent configuration:")
    print(f"- Current date only mode: {CONFIG.get('current_date_only', False)}")
    print(f"- Extract date from URL: {CONFIG.get('extract_date_from_url', False)}")
    
    # Ask if user wants to override date filtering for testing
    override = input("\nDo you want to see ALL articles regardless of date? (y/n): ").strip().lower()
    if override == 'y':
        # Temporarily disable date filtering
        original_setting = CONFIG.get('current_date_only', False)
        CONFIG['current_date_only'] = False
        print("Date filtering temporarily disabled for this test.")
    
    print("\nFetching articles...")
    scraper = WarhammerNewsScraper(CONFIG["warhammer_url"], CONFIG["user_agent"])
    articles = scraper.get_articles()
    
    # Restore original setting if we changed it
    if override == 'y':
        CONFIG['current_date_only'] = original_setting
    
    if not articles:
        print("\nNo articles found. The scraper might not be working correctly.")
        print("Please check the following:")
        print("1. Your internet connection")
        print("2. The Warhammer Community website URL in the CONFIG dictionary")
        print("3. The website structure might have changed, requiring updates to the scraper")
        return
    
    print(f"\nFound {len(articles)} articles:")
    print("-" * 60)
    
    for i, article in enumerate(articles, 1):
        print(f"{i}. {article['title']}")
        print(f"   URL: {article['url']}")
        print(f"   Category: {article['category']}")
        if 'pub_date' in article:
            print(f"   Publication Date: {article['pub_date']}")
            # Check if this is today's article
            today = date.today().isoformat()
            if article['pub_date'] == today:
                print(f"   [TODAY'S ARTICLE]")
        print(f"   Timestamp: {article['timestamp']}")
        print("-" * 60)
    
    print("\nScraper test completed successfully!")
    print("If you want to save these results to a file, run: python test_scraper.py > test_results.txt")
    
    # Ask if user wants to save the articles to a JSON file
    save = input("\nDo you want to save these articles to a JSON file? (y/n): ").strip().lower()
    if save == 'y':
        filename = "test_articles.json"
        with open(filename, 'w') as f:
            json.dump(articles, f, indent=2)
        print(f"Articles saved to {filename}")

if __name__ == "__main__":
    main()
