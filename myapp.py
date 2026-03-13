#!/usr/bin/env python3
"""
Sample application that uses AppleScript functionality
"""

import subprocess
import sys
import os
import json

def run_applescript(script):
    """Run AppleScript and return result"""
    try:
        result = subprocess.run(['osascript', '-e', script], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"AppleScript Error: {e.stderr}")
        return None

def get_system_info():
    """Get Mac system information using AppleScript"""
    # FIX: Use 'system info' to get OS version, computer name, and user name correctly
    script = '''
    set sysInfo to system info
    set os_version to system version of sysInfo
    set computer_name to computer name of sysInfo
    set user_name to short user name of sysInfo
    return os_version & "|" & computer_name & "|" & user_name
    '''
    result = run_applescript(script)
    if result:
        parts = result.split('|')
        return {
            'os_version': parts[0],
            'computer_name': parts[1],
            'user_name': parts[2]
        }
    return None

def show_notification(title, message):
    """Show macOS notification"""
    script = f'''
    display notification "{message}" with title "{title}"
    '''
    run_applescript(script)

def main():
    print("=" * 50)
    print("My Protected AppleScript Application")
    print("=" * 50)
    
    # Get system info
    print("\n📊 System Information:")
    info = get_system_info()
    if info:
        for key, value in info.items():
            print(f"  {key}: {value}")
    
    # Show notification
    print("\n🔔 Showing notification...")
    show_notification("Hello from Protected App", 
                     "This app was built with PyInstaller and encrypted!")
    
    # Simulate some work
    print("\n💻 Doing some work...")
    
    # Example: Get frontmost application
    script = '''
    tell application "System Events"
        set frontApp to name of first application process whose frontmost is true
    end tell
    return frontApp
    '''
    front_app = run_applescript(script)
    if front_app:
        print(f"  Frontmost application: {front_app}")
    
    print("\n✅ Application completed successfully!")

if __name__ == "__main__":
    main()
