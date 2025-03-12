#!/usr/bin/env python3
"""
Warhammer Community News Discord Bot

This script scrapes the Warhammer Community website for news articles
and posts new links to a specified Discord channel using webhooks.
It keeps track of previously posted links to avoid duplicates.
"""

import os
import json
import time
import logging
import requests
from datetime import datetime, date
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("warhammer_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("warhammer_bot")

# Configuration
CONFIG = {
    "warhammer_url": "https://www.warhammer-community.com/en-gb/",
    "discord_webhook_url": "",  # To be filled by the user
    "check_interval": 3600,  # Check every hour (in seconds)
    "history_file": "posted_articles.json",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "current_date_only": True,  # Only post articles from the current date or newer
    "extract_date_from_url": True  # Try to extract date from URL if no date element found
}

class WarhammerNewsScraper:
    """Scrapes Warhammer Community website for news articles."""
    
    def __init__(self, url: str, user_agent: str):
        self.url = url
        self.headers = {"User-Agent": user_agent}
    
    def get_articles(self) -> List[Dict[str, Any]]:
        """
        Scrapes the Warhammer Community website and returns a list of articles.
        
        Returns:
            List[Dict[str, Any]]: List of article dictionaries with title, url, category, and timestamp
        """
        try:
            response = requests.get(self.url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            articles = []
            
            # Find all article elements - this selector might need adjustment based on the actual HTML structure
            article_elements = soup.select('article') or soup.select('.post-item') or soup.select('.article-card')
            
            if not article_elements:
                # Fallback to looking for common article containers
                article_elements = soup.select('.card, .news-item, .post')
            
            # If still no elements found, try to find links with titles that might be articles
            if not article_elements:
                logger.warning("Could not find article elements with standard selectors, using fallback method")
                # Look for links that might be article titles
                for link in soup.find_all('a', href=True):
                    if link.text.strip() and '/posts/' in link['href'] or '/articles/' in link['href']:
                        title = link.text.strip()
                        url = link['href']
                        if not url.startswith('http'):
                            url = f"https://www.warhammer-community.com{url}"
                        
                        articles.append({
                            'title': title,
                            'url': url,
                            'category': 'Unknown',
                            'timestamp': datetime.now().isoformat()
                        })
                
                return articles
            
            # Process each article element
            for article in article_elements:
                # Extract title and URL
                title_element = article.select_one('h2, h3, .title, .post-title')
                link_element = article.select_one('a[href]') or (title_element.find('a') if title_element else None)
                
                if not link_element:
                    continue
                
                url = link_element.get('href', '')
                if not url.startswith('http'):
                    url = f"https://www.warhammer-community.com{url}"
                
                title = title_element.text.strip() if title_element else link_element.text.strip()
                
                # Extract category if available
                category_element = article.select_one('.category, .tag, .post-category')
                category = category_element.text.strip() if category_element else "Unknown"
                
                # Try to extract publication date
                pub_date = None
                
                # Look for date elements
                date_element = article.select_one('.date, .post-date, time')
                if date_element:
                    date_text = date_element.text.strip()
                    try:
                        # Try common date formats
                        for fmt in ['%d %b %Y', '%B %d, %Y', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                            try:
                                pub_date = datetime.strptime(date_text, fmt).date()
                                break
                            except ValueError:
                                continue
                    except Exception as e:
                        logger.debug(f"Could not parse date '{date_text}': {e}")
                
                # If date not found in elements and extract_date_from_url is enabled, try URL
                if pub_date is None and CONFIG.get("extract_date_from_url", False):
                    # Look for date pattern in URL (e.g., /2023/03/12/)
                    import re
                    date_match = re.search(r'/(\d{4})/(\d{1,2})/(\d{1,2})/', url)
                    if date_match:
                        try:
                            year, month, day = map(int, date_match.groups())
                            pub_date = date(year, month, day)
                        except Exception as e:
                            logger.debug(f"Could not extract date from URL '{url}': {e}")
                
                # If still no date, use current date
                if pub_date is None:
                    pub_date = date.today()
                
                # Create article object
                article_obj = {
                    'title': title,
                    'url': url,
                    'category': category,
                    'pub_date': pub_date.isoformat(),
                    'timestamp': datetime.now().isoformat()
                }
                
                # If current_date_only is enabled, only include articles from today or newer
                if CONFIG.get("current_date_only", False):
                    today = date.today()
                    article_date = date.fromisoformat(article_obj['pub_date'])
                    if article_date >= today:
                        articles.append(article_obj)
                else:
                    articles.append(article_obj)
            
            logger.info(f"Found {len(articles)} articles")
            return articles
            
        except Exception as e:
            logger.error(f"Error scraping articles: {e}")
            return []

class DiscordPoster:
    """Posts messages to Discord using webhooks."""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def post_article(self, article: Dict[str, Any]) -> bool:
        """
        Posts an article to Discord.
        
        Args:
            article (Dict[str, Any]): Article information
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.webhook_url:
            logger.error("Discord webhook URL not configured")
            return False
            
        try:
            # Create a Discord embed for better formatting
            embed = {
                "title": article['title'],
                "url": article['url'],
                "color": 0x9370DB,  # Purple color
                "footer": {
                    "text": f"Category: {article['category']} • Posted by Warhammer News Bot"
                },
                "timestamp": article['timestamp']
            }
            
            payload = {
                "content": f"New Warhammer Community article: {article['title']}",
                "embeds": [embed]
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload
            )
            response.raise_for_status()
            
            logger.info(f"Successfully posted article: {article['title']}")
            return True
            
        except Exception as e:
            logger.error(f"Error posting to Discord: {e}")
            return False

class ArticleHistory:
    """Manages the history of posted articles to avoid duplicates."""
    
    def __init__(self, history_file: str):
        self.history_file = history_file
        self.posted_articles = self._load_history()
    
    def _load_history(self) -> Dict[str, Dict[str, Any]]:
        """
        Loads the history of posted articles from a file.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of posted articles with URL as key
        """
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading history file: {e}")
                return {}
        return {}
    
    def _save_history(self) -> None:
        """Saves the history of posted articles to a file."""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.posted_articles, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving history file: {e}")
    
    def is_posted(self, url: str) -> bool:
        """
        Checks if an article has already been posted.
        
        Args:
            url (str): Article URL
            
        Returns:
            bool: True if already posted, False otherwise
        """
        return url in self.posted_articles
    
    def mark_as_posted(self, article: Dict[str, Any]) -> None:
        """
        Marks an article as posted.
        
        Args:
            article (Dict[str, Any]): Article information
        """
        self.posted_articles[article['url']] = {
            'title': article['title'],
            'category': article['category'],
            'posted_at': datetime.now().isoformat()
        }
        self._save_history()

def validate_config() -> bool:
    """
    Validates the configuration.
    
    Returns:
        bool: True if valid, False otherwise
    """
    if not CONFIG["discord_webhook_url"]:
        logger.error("Discord webhook URL not configured")
        return False
    return True

def main() -> None:
    """Main function to run the bot."""
    logger.info("Starting Warhammer News Discord Bot")
    
    if not validate_config():
        logger.error("Invalid configuration. Please check the CONFIG dictionary.")
        return
    
    scraper = WarhammerNewsScraper(CONFIG["warhammer_url"], CONFIG["user_agent"])
    poster = DiscordPoster(CONFIG["discord_webhook_url"])
    history = ArticleHistory(CONFIG["history_file"])
    
    # Log current settings
    logger.info(f"Current date only mode: {CONFIG.get('current_date_only', False)}")
    
    while True:
        try:
            logger.info("Checking for new articles...")
            articles = scraper.get_articles()
            
            logger.info(f"Found {len(articles)} articles matching date criteria")
            
            new_articles = 0
            for article in articles:
                if not history.is_posted(article['url']):
                    logger.info(f"New article found: {article['title']}")
                    if poster.post_article(article):
                        history.mark_as_posted(article)
                        new_articles += 1
            
            logger.info(f"Posted {new_articles} new articles")
            
            # Sleep until next check
            logger.info(f"Sleeping for {CONFIG['check_interval']} seconds")
            time.sleep(CONFIG["check_interval"])
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            # Sleep for a shorter time if there was an error
            time.sleep(60)

if __name__ == "__main__":
    main()
