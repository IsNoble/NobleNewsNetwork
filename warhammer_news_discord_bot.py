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
import re
from datetime import datetime, date, timedelta
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional

# Configure logging
# File handler with UTF-8 encoding
file_handler = logging.FileHandler("warhammer_bot.log", encoding='utf-8')

# Stream handler with error handling for encoding issues
class EncodingStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            super().emit(record)
        except UnicodeEncodeError:
            # Fall back to ASCII with replacement characters for non-ASCII
            msg = self.format(record)
            stream = self.stream
            # Replace non-ASCII characters with '?' for console output
            stream.write(msg.encode('ascii', 'replace').decode('ascii') + self.terminator)
            self.flush()

# Set logging level to DEBUG to see more information
logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        file_handler,
        EncodingStreamHandler()
    ]
)
logger = logging.getLogger("warhammer_bot")

# Configuration
CONFIG = {
    "warhammer_url": "https://www.warhammer-community.com/en-gb/",
    "discord_webhook_url": "https://discord.com/api/webhooks/1349499463294517308/e067VzmBuxnPli4isJ5wqc0i3YepRRjX0OivdHbhjWsdXdqlYwB6EXKG5u9X_QwODevN",  # To be filled by the user
    "check_interval": 1800,  # Check every hour (in seconds)
    "history_file": "posted_articles.json",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "current_date_only": True,  # Only post articles from the current date or newer
    "days_to_look_back": 0,     # Number of days to look back for articles (0 = today only, 1 = today and yesterday, etc.)
    "strict_date_filtering": False,  # When True, only includes articles that are confirmed to be from today (based on URL or date element). When False, includes articles from within days_to_look_back range.
    "debug_html": True,         # Save HTML for debugging
    "max_articles_per_run": 10, # Maximum number of articles to post in a single run
    "never_assume_today": True  # Never assume an article is from today unless confirmed
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
            
            # Save HTML for debugging if enabled
            if CONFIG.get("debug_html", False):
                with open("warhammer_debug.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                logger.debug("Saved HTML to warhammer_debug.html for debugging")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            articles = []
            today = date.today()
            
            # Log today's date for reference
            logger.debug(f"Today's date: {today.isoformat()} (YYYY-MM-DD)")
            
            # Find all article elements - this selector might need adjustment based on the actual HTML structure
            article_elements = soup.select('article') or soup.select('.post-item') or soup.select('.article-card')
            logger.debug(f"Found {len(article_elements)} article elements with primary selectors")
            
            if not article_elements:
                # Fallback to looking for common article containers
                article_elements = soup.select('.card, .news-item, .post')
                logger.debug(f"Found {len(article_elements)} article elements with fallback selectors")
            
            # If still no elements found, try to find links with titles that might be articles
            if not article_elements:
                logger.warning("Could not find article elements with standard selectors, using fallback method")
                # Look for links that might be article titles
                article_links = []
                for link in soup.find_all('a', href=True):
                    if link.text.strip() and ('/posts/' in link['href'] or '/articles/' in link['href'] or '/videos/' in link['href']):
                        article_links.append(link)
                
                logger.debug(f"Found {len(article_links)} potential article links with fallback method")
                
                for link in article_links:
                    title = link.text.strip()
                    url = link['href']
                    if not url.startswith('http'):
                        url = f"https://www.warhammer-community.com{url}"
                    
                    logger.debug(f"Processing article link: {title} - {url}")
                    
                    # Check if the URL contains today's date
                    is_from_today = self._is_from_today(url, today)
                    logger.debug(f"URL date check for '{title}': {is_from_today}")
                    
                    # Only include articles that are confirmed to be from today
                    if is_from_today:
                        articles.append({
                            'title': title,
                            'url': url,
                            'category': 'Unknown',
                            'pub_date': today.isoformat(),
                            'timestamp': datetime.now().isoformat(),
                            'is_from_today': True,
                            'date_source': 'url'
                        })
                        logger.debug(f"Added article (confirmed from URL): {title}")
                
                logger.info(f"Found {len(articles)} articles confirmed to be from today using fallback method")
                return articles
            
            # Process each article element
            for i, article in enumerate(article_elements):
                logger.debug(f"Processing article element {i+1}/{len(article_elements)}")
                
                # Extract title and URL
                title_element = article.select_one('h2, h3, .title, .post-title')
                link_element = article.select_one('a[href]') or (title_element.find('a') if title_element else None)
                
                if not link_element:
                    logger.debug(f"No link element found for article {i+1}")
                    continue
                
                url = link_element.get('href', '')
                if not url.startswith('http'):
                    url = f"https://www.warhammer-community.com{url}"
                
                title = title_element.text.strip() if title_element else link_element.text.strip()
                logger.debug(f"Found article: {title} - {url}")
                
                # Extract category if available
                category_element = article.select_one('.category, .tag, .post-category')
                category = category_element.text.strip() if category_element else "Unknown"
                logger.debug(f"Category: {category}")
                
                # Try to determine if the article is from today
                is_from_today = False
                pub_date = None
                date_source = "unknown"
                
                # Method 1: Check if the URL contains today's date
                if self._is_from_today(url, today):
                    is_from_today = True
                    pub_date = today
                    date_source = "url"
                    logger.debug(f"Article date determined from URL: {pub_date.isoformat()}")
                
                # Method 2: Look for date elements in the article with expanded selectors
                if not is_from_today:
                    # Expanded list of selectors to find date elements
                    date_element = article.select_one('.date, .post-date, time, .meta-date, .published, .entry-date, .timestamp, [datetime], [data-datetime], [data-date]')
                    
                    if date_element:
                        # Try to get date from datetime attribute first (most reliable)
                        datetime_attr = date_element.get('datetime')
                        if datetime_attr:
                            logger.debug(f"Found datetime attribute: '{datetime_attr}'")
                            try:
                                # ISO format date parsing
                                extracted_date = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00')).date()
                                logger.debug(f"Successfully parsed datetime attribute: {extracted_date.isoformat()}")
                                pub_date = extracted_date
                                date_source = "element-attr"
                                if extracted_date == today:
                                    is_from_today = True
                            except Exception as e:
                                logger.debug(f"Could not parse datetime attribute '{datetime_attr}': {e}")
                        
                        # If no datetime attribute or parsing failed, try text content
                        if pub_date is None:
                            date_text = date_element.text.strip()
                            logger.debug(f"Found date element with text: '{date_text}'")
                            
                            # Try to extract date from text
                            extracted_date = self._parse_date_text(date_text, today)
                            if extracted_date:
                                pub_date = extracted_date
                                date_source = "element-text"
                                if extracted_date == today:
                                    is_from_today = True
                
                # Method 3: Look for Warhammer-specific date format in JSON-like data
                if not pub_date:
                    # Look for the specific date format in the article HTML
                    article_html = str(article)
                    
                    # Try different patterns to match the date in various JSON-like formats
                    date_patterns = [
                        # Match with escaped quotes (common in JSON within HTML)
                        r'date\\\"\:\\\"\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{2})',
                        # Match with regular quotes
                        r'date\":\"\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{2})',
                        # Match with single quotes
                        r"date\':\'\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{2})",
                        # Match without quotes
                        r'date\s*:\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{2})',
                        # Most generic pattern - just find the date format
                        r'(\d{1,2}\s+[A-Za-z]{3}\s+\d{2})'
                    ]
                    
                    date_match = None
                    for pattern in date_patterns:
                        date_match = re.search(pattern, article_html)
                        if date_match:
                            logger.debug(f"Found date with pattern '{pattern}': {date_match.group(1)}")
                            break
                    
                    if date_match:
                        date_text = date_match.group(1)
                        logger.debug(f"Found Warhammer-specific date format: '{date_text}'")
                        
                        try:
                            # Parse the date (format: "DD MMM YY")
                            extracted_date = datetime.strptime(date_text, '%d %b %y').date()
                            logger.debug(f"Successfully parsed Warhammer-specific date: {extracted_date.isoformat()}")
                            pub_date = extracted_date
                            date_source = "json-data"
                            if extracted_date == today:
                                is_from_today = True
                        except Exception as e:
                            logger.debug(f"Could not parse Warhammer-specific date '{date_text}': {e}")
                
                # Method 4: Look for date patterns in the article content
                if not pub_date:
                    # Get all text from the article
                    article_text = article.get_text(" ", strip=True)
                    
                    # Look for common date patterns in the text
                    date_patterns = [
                        r'Posted on (\d{1,2}[thstrd]* [A-Za-z]+ \d{4})',
                        r'Published:? (\d{1,2}[thstrd]* [A-Za-z]+ \d{4})',
                        r'Date:? (\d{1,2}[thstrd]* [A-Za-z]+ \d{4})',
                        r'(\d{1,2}[thstrd]* [A-Za-z]+ \d{4})',  # Just the date format
                        r'(\d{1,2}/\d{1,2}/\d{4})',  # MM/DD/YYYY or DD/MM/YYYY
                        r'(\d{4}-\d{1,2}-\d{1,2})',  # YYYY-MM-DD
                        r'(\d{1,2}\s+[A-Za-z]{3}\s+\d{2})'  # DD MMM YY (e.g., "12 Mar 25")
                    ]
                    
                    for pattern in date_patterns:
                        match = re.search(pattern, article_text)
                        if match:
                            date_text = match.group(1)
                            logger.debug(f"Found date pattern in article text: '{date_text}'")
                            
                            extracted_date = self._parse_date_text(date_text, today)
                            if extracted_date:
                                pub_date = extracted_date
                                date_source = "content"
                                if extracted_date == today:
                                    is_from_today = True
                                break
                
                # If we couldn't determine the date and never_assume_today is enabled, skip this article
                if pub_date is None:
                    if CONFIG.get("never_assume_today", False):
                        logger.debug(f"Skipping article with unknown date (never_assume_today is enabled): {title}")
                        continue
                    else:
                        pub_date = today
                        date_source = "assumed"
                        logger.debug(f"Using today's date for article with unknown date: {title}")
                
                # Create article object
                article_obj = {
                    'title': title,
                    'url': url,
                    'category': category,
                    'pub_date': pub_date.isoformat(),
                    'timestamp': datetime.now().isoformat(),
                    'is_from_today': is_from_today,
                    'date_source': date_source
                }
                
                # If current_date_only is enabled, only include articles from today or newer
                if CONFIG.get("current_date_only", False):
                    days_back = CONFIG.get("days_to_look_back")
                    cutoff_date = today - timedelta(days=days_back)
                    
                    if pub_date >= cutoff_date:
                        # If strict filtering is enabled, only include articles we're sure are from today
                        if CONFIG.get("strict_date_filtering", False) and not is_from_today:
                            logger.info(f"Skipping article due to strict date filtering: {title}")
                            continue
                        
                        articles.append(article_obj)
                        logger.debug(f"Including article from {pub_date} (source: {date_source}): {title}")
                    else:
                        logger.debug(f"Skipping article from {pub_date} (older than cutoff {cutoff_date}): {title}")
                else:
                    articles.append(article_obj)
            
            logger.info(f"Found {len(articles)} articles matching date criteria")
            
            # Sort articles by date (newest first)
            articles.sort(key=lambda x: x['pub_date'], reverse=True)
            
            # Limit the number of articles to post in a single run
            max_articles = CONFIG.get("max_articles_per_run", 10)
            if len(articles) > max_articles:
                logger.info(f"Limiting to {max_articles} articles (out of {len(articles)} found)")
                articles = articles[:max_articles]
            
            return articles
            
        except Exception as e:
            logger.error(f"Error scraping articles: {e}")
            return []
    
    def _parse_date_text(self, date_text: str, today: date) -> Optional[date]:
        """
        Parse a date text string into a date object.
        
        Args:
            date_text (str): The date text to parse
            today (date): Today's date for reference
            
        Returns:
            Optional[date]: The parsed date, or None if parsing failed
        """
        logger.debug(f"Attempting to parse date text: '{date_text}'")
        
        # Remove ordinal suffixes (1st, 2nd, 3rd, 4th, etc.)
        date_text = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_text)
        
        # Try common date formats
        date_formats = [
            '%d %b %Y',       # 01 Jan 2023
            '%d %B %Y',       # 01 January 2023
            '%B %d %Y',       # January 01 2023
            '%B %d, %Y',      # January 01, 2023
            '%d/%m/%Y',       # 01/01/2023 (UK format)
            '%m/%d/%Y',       # 01/01/2023 (US format)
            '%Y-%m-%d',       # 2023-01-01
            '%Y/%m/%d',       # 2023/01/01
            '%d-%m-%Y',       # 01-01-2023
            '%m-%d-%Y',       # 01-01-2023
            '%d.%m.%Y',       # 01.01.2023
            '%Y.%m.%d'        # 2023.01.01
        ]
        
        for fmt in date_formats:
            try:
                extracted_date = datetime.strptime(date_text, fmt).date()
                logger.debug(f"Successfully parsed date '{date_text}' with format '{fmt}': {extracted_date.isoformat()}")
                return extracted_date
            except ValueError:
                continue
        
        # Try to handle relative dates like "today", "yesterday"
        lower_text = date_text.lower()
        if "today" in lower_text:
            return today
        elif "yesterday" in lower_text:
            return today - timedelta(days=1)
        
        # Try to extract month and day without year (assume current year)
        month_day_formats = [
            '%d %b',          # 01 Jan
            '%d %B',          # 01 January
            '%B %d',          # January 01
            '%d/%m',          # 01/01
            '%m/%d'           # 01/01
        ]
        
        for fmt in month_day_formats:
            try:
                # Parse with a dummy year
                dummy_date_text = f"{date_text} 2000"
                dummy_fmt = f"{fmt} %Y"
                extracted_date = datetime.strptime(dummy_date_text, dummy_fmt).date()
                
                # Replace the year with the current year
                current_year_date = date(today.year, extracted_date.month, extracted_date.day)
                
                # If this would make the date in the future, use last year
                if current_year_date > today and current_year_date - today > timedelta(days=3):
                    current_year_date = date(today.year - 1, extracted_date.month, extracted_date.day)
                
                logger.debug(f"Parsed date without year '{date_text}' as: {current_year_date.isoformat()}")
                return current_year_date
            except (ValueError, TypeError):
                continue
        
        logger.debug(f"Could not parse date text: '{date_text}'")
        return None
    
    def _is_from_today(self, url: str, today: date) -> bool:
        """
        Check if a URL contains today's date.
        
        Args:
            url (str): The URL to check
            today (date): Today's date
            
        Returns:
            bool: True if the URL contains today's date, False otherwise
        """
        # Log the URL we're checking
        logger.debug(f"Checking if URL contains today's date: {url}")
        
        # Look for date pattern in URL (e.g., /2023/03/12/)
        date_match = re.search(r'/(\d{4})/(\d{1,2})/(\d{1,2})/', url)
        if date_match:
            try:
                year, month, day = map(int, date_match.groups())
                url_date = date(year, month, day)
                logger.debug(f"Found date in URL: {url_date.isoformat()}, today is {today.isoformat()}")
                return url_date == today
            except Exception as e:
                logger.debug(f"Could not extract date from URL '{url}': {e}")
        
        # Look for date in other formats (e.g., 2023-03-12)
        date_formats = [
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
            r'(\d{1,2})-(\d{1,2})-(\d{4})',  # DD-MM-YYYY
            r'(\d{4})_(\d{1,2})_(\d{1,2})'   # YYYY_MM_DD
        ]
        
        for pattern in date_formats:
            date_match = re.search(pattern, url)
            if date_match:
                try:
                    groups = date_match.groups()
                    if len(groups[0]) == 4:  # YYYY-MM-DD or YYYY_MM_DD
                        year, month, day = map(int, groups)
                    else:  # DD-MM-YYYY
                        day, month, year = map(int, groups)
                    
                    url_date = date(year, month, day)
                    logger.debug(f"Found date in URL with pattern '{pattern}': {url_date.isoformat()}")
                    return url_date == today
                except Exception as e:
                    logger.debug(f"Could not extract date from URL '{url}' using pattern '{pattern}': {e}")
        
        # Check for today's date in the URL in various formats
        today_str = today.strftime('%Y/%m/%d')
        today_str_alt = today.strftime('%d/%m/%Y')
        today_str_dash = today.strftime('%Y-%m-%d')
        today_str_underscore = today.strftime('%Y_%m_%d')
        
        if (today_str in url or 
            today_str_alt in url or 
            today_str_dash in url or 
            today_str_underscore in url):
            logger.debug(f"Found today's date in URL using string matching")
            return True
        
        logger.debug(f"No date found in URL: {url}")
        return False

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
                    "text": "Posted by Noble News Bot"
                },
                "timestamp": article['timestamp']
            }
            
            # Add date source information if available
            if 'date_source' in article:
                date_source = article['date_source']
                pub_date = article['pub_date']
                
                if date_source == 'url':
                    embed["description"] = f"Date confirmed from URL: {pub_date}"
                elif date_source == 'element-attr':
                    embed["description"] = f"Date confirmed from article datetime attribute: {pub_date}"
                elif date_source == 'element-text':
                    embed["description"] = f"Date confirmed from article date text: {pub_date}"
                elif date_source == 'content':
                    embed["description"] = f"Date extracted from article content: {pub_date}"
                elif date_source == 'assumed':
                    embed["description"] = f"Date assumed to be today: {pub_date}"
                else:
                    embed["description"] = f"Date source: {date_source}, Date: {pub_date}"
            
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
    logger.info(f"Current date only mode: {CONFIG.get('current_date_only')}")
    logger.info(f"Strict date filtering: {CONFIG.get('strict_date_filtering')}")
    logger.info(f"Never assume today: {CONFIG.get('never_assume_today')}")
    logger.info(f"Days to look back: {CONFIG.get('days_to_look_back')}")
    logger.info(f"Max articles per run: {CONFIG.get('max_articles_per_run')}")
    
    while True:
        try:
            logger.info("Checking for new articles...")
            articles = scraper.get_articles()
            
            logger.info(f"Found {len(articles)} articles matching date criteria")
            
            new_articles = 0
            for article in articles:
                # Double-check the date if current_date_only is enabled
                if CONFIG.get("current_date_only", False):
                    today = date.today()
                    days_back = CONFIG.get("days_to_look_back")
                    cutoff_date = today - timedelta(days=days_back)
                    
                    article_date = date.fromisoformat(article['pub_date'])
                    if article_date < cutoff_date:
                        logger.info(f"Skipping article from {article_date} (older than cutoff {cutoff_date}): {article['title']}")
                        continue
                    
                    # If strict filtering is enabled, only post articles we're sure are from today
                    if CONFIG.get("strict_date_filtering", False) and not article.get('is_from_today', False):
                        logger.info(f"Skipping article due to strict date filtering: {article['title']}")
                        continue
                
                if not history.is_posted(article['url']):
                    logger.info(f"New article found: {article['title']} (Date: {article['pub_date']}, Source: {article.get('date_source', 'unknown')})")
                    if poster.post_article(article):
                        history.mark_as_posted(article)
                        new_articles += 1
                else:
                    logger.info(f"Article already posted: {article['title']}")
            
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
