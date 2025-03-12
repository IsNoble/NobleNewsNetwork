# NobleNews - Warhammer Community News Discord Bot

This bot automatically scrapes the [Warhammer Community website](https://www.warhammer-community.com/en-gb/) for news articles and posts them to a Discord channel using webhooks. It keeps track of previously posted articles to avoid duplicates.

## Features

- Scrapes the Warhammer Community website for news articles
- Posts new articles to a Discord channel using webhooks
- Avoids duplicate posts by tracking previously posted articles
- Runs automatically at configurable intervals
- Detailed logging for monitoring and troubleshooting

## Requirements

- Python 3.6 or higher
- Required Python packages:
  - requests
  - beautifulsoup4

## Setup Instructions

### 1. Install Required Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create a Discord Webhook

1. Open Discord and go to the server where you want to post the articles
2. Right-click on the channel you want to use and select "Edit Channel"
3. Go to "Integrations" > "Webhooks" > "New Webhook"
4. Give your webhook a name (e.g., "Warhammer News Bot")
5. Copy the webhook URL - you'll need this for the configuration

### 3. Configure the Bot

Open the `warhammer_news_discord_bot.py` file and update the `CONFIG` dictionary:

```python
CONFIG = {
    "warhammer_url": "https://www.warhammer-community.com/en-gb/",
    "discord_webhook_url": "YOUR_DISCORD_WEBHOOK_URL_HERE",  # Replace with your webhook URL
    "check_interval": 3600,  # Check every hour (in seconds)
    "history_file": "posted_articles.json",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "current_date_only": true,  # Only post articles from the current date or newer
    "extract_date_from_url": true  # Try to extract date from URL if no date element found
}
```

### 4. Run the Bot

```bash
python warhammer_news_discord_bot.py
```

The bot will start running and check for new articles at the specified interval. It will log its activity to both the console and a file named `warhammer_bot.log`.

Alternatively, you can use the provided configuration script:

```bash
python configure_bot.py
```

This script will guide you through the process of setting up the Discord webhook and configuring the bot.

### 5. Test the Scraper

To test the scraping functionality without posting to Discord:

```bash
python test_scraper.py
```

This will fetch articles from the Warhammer Community website and display them without posting to Discord.

## Running the Bot Automatically

### Windows (Task Scheduler)

You can use the provided script to set up automatic startup on Windows:

```bash
python setup_autostart_windows.py
```

This script will create a scheduled task to run the bot when you log in to Windows.

Alternatively, you can set it up manually:

1. Open Task Scheduler
2. Click "Create Basic Task"
3. Give it a name and description
4. Set the trigger to "When the computer starts" or "At a specific time"
5. Set the action to "Start a program"
6. Browse to your Python executable (e.g., `C:\Python39\python.exe`)
7. Add the full path to the script as an argument (e.g., `C:\path\to\warhammer_news_discord_bot.py`)
8. Set the "Start in" field to the directory containing the script
9. Finish the wizard

### Linux/macOS (Cron)

1. Open your crontab file:
   ```bash
   crontab -e
   ```

2. Add a line to run the script at system startup:
   ```
   @reboot python3 /path/to/warhammer_news_discord_bot.py
   ```

3. Save and exit

## Customization

You can customize the bot by modifying the `CONFIG` dictionary:

- `check_interval`: How often to check for new articles (in seconds)
- `history_file`: Where to store the history of posted articles
- `user_agent`: The User-Agent header to use when making requests
- `current_date_only`: When set to `true`, the bot will only post articles from the current date or newer. This prevents flooding your Discord channel with older articles when the bot is first run.
- `extract_date_from_url`: When set to `true`, the bot will try to extract the publication date from the article URL if no date element is found on the page.

## Troubleshooting

If the bot is not working correctly:

1. Check the `warhammer_bot.log` file for error messages
2. Verify that your Discord webhook URL is correct
3. Make sure you have installed all required dependencies
4. Check your internet connection

## License

This project is open source and available under the MIT License.
