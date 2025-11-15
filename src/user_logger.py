"""
User interaction logger
Logs all user interactions to individual log files
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional

class UserLogger:
    """Logger for user interactions"""
    
    def __init__(self, logs_dir='logs'):
        """Initialize user logger
        
        Args:
            logs_dir: Directory to store log files
        """
        # Get absolute path relative to project root
        if not os.path.isabs(logs_dir):
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            logs_dir = os.path.join(project_root, logs_dir)
        
        self.logs_dir = logs_dir
        
        # Create logs directory if it doesn't exist
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)
    
    def _get_log_file_path(self, phone_number: str) -> str:
        """Get log file path for a user
        
        Args:
            phone_number: User's phone number
            
        Returns:
            Path to user's log file
        """
        # Sanitize phone number for filename (remove +, spaces, etc.)
        safe_phone = phone_number.replace('+', '').replace(' ', '').replace('-', '')
        filename = f"user_{safe_phone}.log"
        return os.path.join(self.logs_dir, filename)
    
    def log_interaction(self, phone_number: str, direction: str, message: str, 
                       state: Optional[str] = None, buttons: Optional[list] = None):
        """Log a user interaction
        
        Args:
            phone_number: User's phone number
            direction: 'incoming' or 'outgoing'
            message: The message content
            state: Current conversation state (optional)
            buttons: Buttons sent (optional)
        """
        log_file = self._get_log_file_path(phone_number)
        
        # Prepare log entry
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'direction': direction,
            'message': message,
        }
        
        if state:
            log_entry['state'] = state
        
        if buttons:
            # Handle different button formats
            try:
                if isinstance(buttons, list) and len(buttons) > 0:
                    button_titles = []
                    for btn in buttons:
                        if isinstance(btn, dict):
                            # WhatsApp format: {'type': 'reply', 'reply': {'id': '...', 'title': '...'}}
                            if 'reply' in btn and isinstance(btn['reply'], dict):
                                button_titles.append(btn['reply']['title'])
                            # Simple format: {'id': '...', 'title': '...'}
                            elif 'title' in btn:
                                button_titles.append(btn['title'])
                            else:
                                button_titles.append(str(btn))
                        else:
                            button_titles.append(str(btn))
                    log_entry['buttons'] = button_titles
                else:
                    log_entry['buttons'] = []
            except (KeyError, TypeError) as e:
                log_entry['buttons'] = [f'(error parsing buttons: {e})']
        
        # Write to log file in readable format
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                # Write separator for readability
                f.write('─' * 80 + '\n')
                
                # Write timestamp
                f.write(f"⏰ {log_entry['timestamp']}\n")
                
                # Write direction with icon
                direction_icon = '📥' if direction == 'incoming' else '📤'
                f.write(f"{direction_icon} {direction.upper()}\n")
                
                # Write state if present
                if 'state' in log_entry:
                    f.write(f"🔹 State: {log_entry['state']}\n")
                
                # Write message (with line breaks for long messages)
                message = log_entry['message']
                if len(message) > 60:
                    # Split long messages into multiple lines
                    f.write(f"💬 Message:\n")
                    # Split by newlines first
                    for line in message.split('\n'):
                        if line:
                            f.write(f"   {line}\n")
                else:
                    f.write(f"💬 Message: {message}\n")
                
                # Write buttons if present
                if 'buttons' in log_entry and log_entry['buttons']:
                    f.write(f"🔘 Buttons: {', '.join(log_entry['buttons'])}\n")
                
                f.write('\n')  # Extra line for spacing
        except Exception as e:
            # Don't let logging errors break the app
            logging.error(f"Failed to write to user log: {e}")
    
    def log_user_message(self, phone_number: str, message: str):
        """Log an incoming message from user
        
        Args:
            phone_number: User's phone number
            message: Message from user
        """
        self.log_interaction(phone_number, 'incoming', message)
    
    def log_bot_response(self, phone_number: str, message: str, 
                        state: Optional[str] = None, buttons: Optional[list] = None):
        """Log an outgoing bot response
        
        Args:
            phone_number: User's phone number
            message: Bot's response message
            state: Current conversation state
            buttons: Buttons sent with the message
        """
        self.log_interaction(phone_number, 'outgoing', message, state, buttons)
    
    def log_event(self, phone_number: str, event_type: str, details: dict = None):
        """Log a special event (like restart, registration complete, etc.)
        
        Args:
            phone_number: User's phone number
            event_type: Type of event (restart, registration_complete, etc.)
            details: Additional event details
        """
        log_file = self._get_log_file_path(phone_number)
        
        timestamp = datetime.now().isoformat()
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                # Write separator for readability
                f.write('═' * 80 + '\n')
                f.write(f"⏰ {timestamp}\n")
                f.write(f"⭐ EVENT: {event_type.upper()}\n")
                
                if details:
                    f.write(f"📋 Details:\n")
                    for key, value in details.items():
                        f.write(f"   • {key}: {value}\n")
                
                f.write('═' * 80 + '\n\n')
        except Exception as e:
            logging.error(f"Failed to write event to user log: {e}")
    
    def get_user_logs(self, phone_number: str) -> list:
        """Get all logs for a user
        
        Args:
            phone_number: User's phone number
            
        Returns:
            List of log entries
        """
        log_file = self._get_log_file_path(phone_number)
        
        if not os.path.exists(log_file):
            return []
        
        logs = []
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        logs.append(json.loads(line))
        except Exception as e:
            logging.error(f"Failed to read user log: {e}")
        
        return logs
    
    def clear_user_logs(self, phone_number: str):
        """Clear all logs for a user
        
        Args:
            phone_number: User's phone number
        """
        log_file = self._get_log_file_path(phone_number)
        
        if os.path.exists(log_file):
            try:
                os.remove(log_file)
            except Exception as e:
                logging.error(f"Failed to delete user log: {e}")

