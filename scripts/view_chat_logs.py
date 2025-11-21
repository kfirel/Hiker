#!/usr/bin/env python3
"""
View chat logs in a more readable, chat-like format
"""

import sys
import os
import re
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def parse_log_file(log_file_path):
    """Parse log file and extract conversation"""
    conversations = []
    current_entry = {}
    reading_message = False
    
    with open(log_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].rstrip('\n')
        original_line = line
        line_stripped = line.strip()
        
        # Skip separators - save current entry and start new one
        if line_stripped.startswith('─') or line_stripped.startswith('═'):
            if current_entry:
                conversations.append(current_entry)
                current_entry = {}
            reading_message = False
            i += 1
            continue
        
        # Skip empty lines
        if not line_stripped:
            i += 1
            continue
        
        # Parse timestamp
        if line_stripped.startswith('⏰'):
            timestamp_str = line_stripped.replace('⏰', '').strip()
            try:
                current_entry['timestamp'] = datetime.fromisoformat(timestamp_str)
            except:
                current_entry['timestamp'] = timestamp_str
            reading_message = False
        
        # Parse direction
        elif line_stripped.startswith('📥'):
            current_entry['direction'] = 'user'
            current_entry['type'] = 'incoming'
            reading_message = False
        elif line_stripped.startswith('📤'):
            current_entry['direction'] = 'bot'
            current_entry['type'] = 'outgoing'
            reading_message = False
        
        # Parse state
        elif line_stripped.startswith('🔹'):
            state = line_stripped.replace('🔹 State:', '').strip()
            current_entry['state'] = state
            reading_message = False
        
        # Parse message header
        elif line_stripped.startswith('💬 Message:'):
            message_text = line_stripped.replace('💬 Message:', '').strip()
            if message_text:
                current_entry['message'] = message_text
                reading_message = False
            else:
                # Multi-line message starts
                current_entry['message'] = ''
                reading_message = True
        
        # Parse buttons
        elif line_stripped.startswith('🔘'):
            buttons = line_stripped.replace('🔘 Buttons:', '').strip()
            current_entry['buttons'] = buttons
            reading_message = False
        
        # Parse event
        elif line_stripped.startswith('⭐'):
            event = line_stripped.replace('⭐ EVENT:', '').strip()
            current_entry['event'] = event
            reading_message = False
        
        # Continue multi-line message
        elif reading_message and (line.startswith('   ') or line_stripped):
            if 'message' not in current_entry:
                current_entry['message'] = ''
            if current_entry['message']:
                current_entry['message'] += '\n' + line_stripped
            else:
                current_entry['message'] = line_stripped
        
        i += 1
    
    if current_entry:
        conversations.append(current_entry)
    
    return conversations

def display_chat_view(conversations):
    """Display conversations in a chat-like format"""
    print("\n" + "="*80)
    print("💬 CHAT CONVERSATION")
    print("="*80 + "\n")
    
    for entry in conversations:
        if not entry:
            continue
        
        # Format timestamp
        timestamp = entry.get('timestamp', '')
        if isinstance(timestamp, datetime):
            time_str = timestamp.strftime('%H:%M:%S')
        else:
            time_str = str(timestamp)[:8] if timestamp else ''
        
        # User message
        if entry.get('type') == 'incoming':
            message = entry.get('message', '')
            print(f"👤 User [{time_str}]")
            print(f"   {message}")
            print()
        
        # Bot message
        elif entry.get('type') == 'outgoing':
            message = entry.get('message', '')
            state = entry.get('state', '')
            buttons = entry.get('buttons', '')
            
            print(f"🤖 Bot [{time_str}]" + (f" | State: {state}" if state else ""))
            if message:
                # Print message with proper indentation
                for line in message.split('\n'):
                    print(f"   {line}")
            
            if buttons:
                print(f"   🔘 Buttons: {buttons}")
            print()
        
        # Event
        elif entry.get('event'):
            event = entry.get('event', '')
            print(f"⭐ EVENT: {event}")
            print()

def main():
    if len(sys.argv) < 2:
        print("Usage: python view_chat_logs.py <phone_number>")
        print("\nExample:")
        print("  python view_chat_logs.py 972524297932")
        print("\nAvailable log files:")
        logs_dir = project_root / 'logs'
        if logs_dir.exists():
            for log_file in sorted(logs_dir.glob('user_*.log')):
                phone = log_file.stem.replace('user_', '')
                print(f"  - {phone}")
        sys.exit(1)
    
    phone_number = sys.argv[1]
    
    # Find log file
    logs_dir = project_root / 'logs'
    log_file = logs_dir / f"user_{phone_number}.log"
    
    if not log_file.exists():
        print(f"❌ Log file not found: {log_file}")
        print(f"\nAvailable log files:")
        for log_file in sorted(logs_dir.glob('user_*.log')):
            phone = log_file.stem.replace('user_', '')
            print(f"  - {phone}")
        sys.exit(1)
    
    # Parse and display
    conversations = parse_log_file(log_file)
    display_chat_view(conversations)
    
    print("="*80)
    print(f"Total entries: {len(conversations)}")
    print("="*80)

if __name__ == '__main__':
    main()

