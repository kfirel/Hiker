#!/usr/bin/env python3
"""
Helper script to start ngrok tunnel for local webhook testing
Run this before starting the Flask app
"""

import sys
import os
# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyngrok import ngrok, conf
import logging
from dotenv import load_dotenv

# Load environment variables from project root
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_ngrok_tunnel(port=5000):
    """
    Start ngrok tunnel on specified port
    
    Args:
        port (int): Local port to expose
        
    Returns:
        str: Public ngrok URL
    """
    try:
        # Set ngrok authtoken if provided in .env
        authtoken = os.getenv('NGROK_AUTHTOKEN')
        if authtoken and authtoken != 'your_ngrok_authtoken_here':
            logger.info("Setting ngrok authtoken from .env file...")
            ngrok.set_auth_token(authtoken)
        else:
            logger.warning("No ngrok authtoken found. Using free tier (limited features).")
            logger.warning("Get your free authtoken at: https://dashboard.ngrok.com/get-started/your-authtoken")
        
        # Kill any existing ngrok processes
        ngrok.kill()
        
        # Start new tunnel
        tunnel = ngrok.connect(port, bind_tls=True)
        public_url = tunnel.public_url
        
        logger.info("=" * 80)
        logger.info("Ngrok tunnel established successfully!")
        logger.info(f"Public URL: {public_url}")
        logger.info(f"Webhook URL: {public_url}/webhook")
        logger.info("=" * 80)
        logger.info("\nIMPORTANT: Copy the Webhook URL above and paste it in your Meta App Dashboard")
        logger.info("Keep this script running while testing your bot")
        logger.info("=" * 80)
        
        # Keep the script running
        input("\nPress Enter to stop ngrok tunnel...\n")
        
    except Exception as e:
        logger.error(f"Failed to start ngrok tunnel: {str(e)}")
        raise
    finally:
        ngrok.kill()
        logger.info("Ngrok tunnel closed")

if __name__ == '__main__':
    start_ngrok_tunnel()

