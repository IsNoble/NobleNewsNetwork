#!/usr/bin/env python3
"""
Configuration script for the Warhammer Community News Discord Bot.
This script helps users set up the bot by guiding them through the process
of creating a Discord webhook and configuring the bot.
"""

import os
import re
import json
import sys

def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f" {text}")
    print("=" * 60 + "\n")

def print_step(step_num, text):
    """Print a formatted step."""
    print(f"\n[Step {step_num}] {text}\n")

def get_input(prompt, default=None, validator=None, error_msg=None):
    """
    Get user input with validation.
    
    Args:
        prompt (str): The prompt to display to the user
        default (str, optional): Default value if user enters nothing
        validator (function, optional): Function to validate input
        error_msg (str, optional): Error message to display if validation fails
        
    Returns:
        str: The validated user input
    """
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
        
    while True:
        user_input = input(prompt).strip()
        
        if not user_input and default:
            user_input = default
            
        if not validator or validator(user_input):
            return user_input
            
        print(f"Error: {error_msg}")

def validate_webhook_url(url):
    """Validate Discord webhook URL."""
    pattern = r'^https://discord\.com/api/webhooks/\d+/[\w-]+$'
    return bool(re.match(pattern, url))

def validate_interval(interval):
    """Validate check interval."""
    try:
        value = int(interval)
        return value > 0
    except ValueError:
        return False

def validate_boolean(value):
    """Validate boolean input."""
    return value.lower() in ['y', 'yes', 'n', 'no', 'true', 'false', '1', '0']

def parse_boolean(value):
    """Parse string to boolean."""
    return value.lower() in ['y', 'yes', 'true', '1']

def main():
    """Main function to configure the bot."""
    print_header("Warhammer Community News Discord Bot Configuration")
    
    print("This script will help you configure the Warhammer Community News Discord Bot.")
    print("You'll need to create a Discord webhook URL before proceeding.")
    
    print_step(1, "Create a Discord webhook")
    print("To create a Discord webhook:")
    print("1. Open Discord and go to the server where you want to post the articles")
    print("2. Right-click on the channel you want to use and select 'Edit Channel'")
    print("3. Go to 'Integrations' > 'Webhooks' > 'New Webhook'")
    print("4. Give your webhook a name (e.g., 'Warhammer News Bot')")
    print("5. Copy the webhook URL")
    
    webhook_url = get_input(
        "Enter your Discord webhook URL",
        validator=validate_webhook_url,
        error_msg="Invalid webhook URL. It should look like: https://discord.com/api/webhooks/123456789/abcdef-ghijkl"
    )
    
    print_step(2, "Configure check interval")
    print("The bot will check for new articles at regular intervals.")
    print("The default is 3600 seconds (1 hour).")
    
    check_interval = get_input(
        "Enter check interval in seconds",
        default="3600",
        validator=validate_interval,
        error_msg="Invalid interval. Please enter a positive number."
    )
    
    print_step(3, "Configure date filtering")
    print("You can choose to only post articles from the current date or newer.")
    print("This helps prevent flooding your Discord channel with old articles when the bot is first run.")
    
    current_date_only = get_input(
        "Only post articles from today or newer? (y/n)",
        default="y",
        validator=validate_boolean,
        error_msg="Invalid input. Please enter 'y' or 'n'."
    )
    current_date_only = parse_boolean(current_date_only)
    
    extract_date_from_url = get_input(
        "Try to extract dates from article URLs if no date element is found? (y/n)",
        default="y",
        validator=validate_boolean,
        error_msg="Invalid input. Please enter 'y' or 'n'."
    )
    extract_date_from_url = parse_boolean(extract_date_from_url)
    
    # Load the existing script
    script_path = "warhammer_news_discord_bot.py"
    if not os.path.exists(script_path):
        print(f"Error: Could not find {script_path}")
        print("Make sure you run this script from the same directory as warhammer_news_discord_bot.py")
        sys.exit(1)
        
    with open(script_path, 'r') as f:
        script_content = f.read()
    
    # Update the CONFIG dictionary
    config_pattern = r'CONFIG = \{[^}]*\}'
    new_config = f'''CONFIG = {{
    "warhammer_url": "https://www.warhammer-community.com/en-gb/",
    "discord_webhook_url": "{webhook_url}",
    "check_interval": {check_interval},
    "history_file": "posted_articles.json",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "current_date_only": {str(current_date_only).lower()},
    "extract_date_from_url": {str(extract_date_from_url).lower()}
}}'''
    
    updated_script = re.sub(config_pattern, new_config, script_content)
    
    # Save the updated script
    with open(script_path, 'w') as f:
        f.write(updated_script)
    
    print_step(4, "Configuration complete")
    print("The bot has been configured successfully!")
    print(f"Discord webhook URL: {webhook_url}")
    print(f"Check interval: {check_interval} seconds")
    
    print_step(5, "Running the bot")
    print("To run the bot, use the following command:")
    print(f"  python {script_path}")
    print("\nThe bot will start checking for new articles and posting them to Discord.")
    print("You can keep it running in the background or set it up to run automatically.")
    print("See the README.md file for instructions on how to run the bot automatically.")
    
    run_now = input("\nDo you want to run the bot now? (y/n): ").strip().lower()
    if run_now == 'y':
        print("\nStarting the bot...")
        print("Press Ctrl+C to stop the bot.")
        os.system(f"python {script_path}")
    else:
        print("\nYou can run the bot later using the command above.")
    
if __name__ == "__main__":
    main()
