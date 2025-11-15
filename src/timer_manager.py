import threading
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class TimerManager:
    """Manages timers for sending delayed messages"""
    
    def __init__(self, whatsapp_client):
        self.whatsapp_client = whatsapp_client
        self.active_timers = {}  # phone_number -> timer object
        self.lock = threading.Lock()
    
    def schedule_followup(self, phone_number, delay_seconds=600):
        """
        Schedule a follow-up message "are you there" after delay
        Resets timer if one already exists for this number
        
        Args:
            phone_number (str): Recipient's phone number
            delay_seconds (int): Delay in seconds (default 600 = 10 minutes)
        """
        with self.lock:
            # Cancel existing timer for this number if exists
            if phone_number in self.active_timers:
                self.active_timers[phone_number].cancel()
                logger.info(f"Cancelled existing timer for {phone_number}")
            
            # Create new timer
            timer = threading.Timer(
                delay_seconds,
                self._send_followup,
                args=[phone_number]
            )
            timer.daemon = True
            timer.start()
            
            self.active_timers[phone_number] = timer
            logger.info(f"Scheduled follow-up for {phone_number} in {delay_seconds} seconds")
    
    def _send_followup(self, phone_number):
        """Internal method to send the follow-up message"""
        logger.info(f"Sending follow-up message to {phone_number}")
        success = self.whatsapp_client.send_message(phone_number, "are you there")
        
        # Remove timer from active timers
        with self.lock:
            if phone_number in self.active_timers:
                del self.active_timers[phone_number]
        
        if success:
            logger.info(f"Follow-up message sent successfully to {phone_number}")
        else:
            logger.error(f"Failed to send follow-up message to {phone_number}")
    
    def cancel_timer(self, phone_number):
        """Cancel timer for a specific phone number"""
        with self.lock:
            if phone_number in self.active_timers:
                self.active_timers[phone_number].cancel()
                del self.active_timers[phone_number]
                logger.info(f"Timer cancelled for {phone_number}")

