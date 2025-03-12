#!/usr/bin/env python3
"""
Setup script to configure the Warhammer Community News Discord Bot
to run automatically on Windows startup using Task Scheduler.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f" {text}")
    print("=" * 60 + "\n")

def print_step(step_num, text):
    """Print a formatted step."""
    print(f"\n[Step {step_num}] {text}\n")

def is_admin():
    """Check if the script is running with administrator privileges."""
    try:
        return os.getuid() == 0
    except AttributeError:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0

def create_task(task_name, script_path, python_path=None):
    """
    Create a Windows scheduled task to run the bot on startup.
    
    Args:
        task_name (str): Name for the scheduled task
        script_path (str): Full path to the bot script
        python_path (str, optional): Path to the Python executable
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not python_path:
        python_path = sys.executable
    
    # Create the task XML
    task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Runs the Warhammer Community News Discord Bot on system startup</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{python_path}</Command>
      <Arguments>{script_path}</Arguments>
      <WorkingDirectory>{os.path.dirname(script_path)}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""
    
    # Save the task XML to a temporary file
    temp_xml_path = os.path.join(os.environ.get('TEMP', '.'), 'warhammer_task.xml')
    with open(temp_xml_path, 'w', encoding='utf-16') as f:
        f.write(task_xml)
    
    try:
        # Create the task using schtasks
        subprocess.run(
            ['schtasks', '/create', '/tn', task_name, '/xml', temp_xml_path, '/f'],
            check=True,
            capture_output=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating task: {e}")
        print(f"Output: {e.stdout.decode() if e.stdout else ''}")
        print(f"Error: {e.stderr.decode() if e.stderr else ''}")
        return False
    finally:
        # Clean up the temporary file
        try:
            os.remove(temp_xml_path)
        except:
            pass

def main():
    """Main function to set up autostart."""
    print_header("Warhammer Community News Discord Bot - Windows Autostart Setup")
    
    # Check if running on Windows
    if platform.system() != 'Windows':
        print("This script is only for Windows systems.")
        print(f"You are running on {platform.system()}.")
        print("Please see the README.md file for instructions for your operating system.")
        sys.exit(1)
    
    # Check for admin privileges
    if not is_admin():
        print("This script requires administrator privileges to create a scheduled task.")
        print("Please run this script as an administrator.")
        print("Right-click on the script and select 'Run as administrator'.")
        sys.exit(1)
    
    print("This script will set up the Warhammer Community News Discord Bot")
    print("to run automatically when you log in to Windows.")
    
    # Get the full path to the bot script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    bot_script = os.path.join(script_dir, "warhammer_news_discord_bot.py")
    
    if not os.path.exists(bot_script):
        print(f"Error: Could not find {bot_script}")
        print("Make sure you run this script from the same directory as warhammer_news_discord_bot.py")
        sys.exit(1)
    
    print_step(1, "Verify Discord webhook configuration")
    print("Before setting up autostart, make sure you have configured the Discord webhook.")
    print("You can run configure_bot.py to set up the webhook if you haven't already.")
    
    configured = input("Have you configured the Discord webhook? (y/n): ").strip().lower()
    if configured != 'y':
        print("\nPlease run configure_bot.py first to set up the Discord webhook.")
        print("Then run this script again.")
        sys.exit(0)
    
    print_step(2, "Create scheduled task")
    print("Creating a scheduled task to run the bot on startup...")
    
    task_name = "WarhammerNewsBotAutostart"
    success = create_task(task_name, bot_script)
    
    if success:
        print_step(3, "Setup complete")
        print("The bot has been successfully configured to run at startup!")
        print(f"Task name: {task_name}")
        print(f"Script path: {bot_script}")
        print(f"Python path: {sys.executable}")
        
        print("\nYou can manage this task in Task Scheduler:")
        print("1. Open Task Scheduler (taskschd.msc)")
        print("2. Look for the task named 'WarhammerNewsBotAutostart'")
        print("3. You can disable, modify, or delete the task from there")
        
        print("\nThe bot will now start automatically when you log in to Windows.")
    else:
        print_step(3, "Setup failed")
        print("Failed to create the scheduled task.")
        print("You can try to create it manually using Task Scheduler:")
        print("1. Open Task Scheduler (taskschd.msc)")
        print("2. Click 'Create Basic Task'")
        print("3. Follow the wizard to create a task that runs at logon")
        print(f"4. Set the program to: {sys.executable}")
        print(f"5. Set the arguments to: {bot_script}")
        print(f"6. Set the start in directory to: {os.path.dirname(bot_script)}")

if __name__ == "__main__":
    main()
