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
import time
from dotenv import load_dotenv

# Load environment variables from project root
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def kill_all_ngrok_tunnels():
    """
    Kill all existing ngrok tunnels and processes
    """
    try:
        # Get all active tunnels
        tunnels = ngrok.get_tunnels()
        if tunnels:
            logger.info(f"Found {len(tunnels)} existing tunnel(s), disconnecting...")
            for tunnel in tunnels:
                try:
                    ngrok.disconnect(tunnel.public_url)
                    logger.info(f"Disconnected tunnel: {tunnel.public_url}")
                except Exception as e:
                    logger.warning(f"Could not disconnect tunnel {tunnel.public_url}: {e}")
        
        # Kill all ngrok processes
        ngrok.kill()
        
        # Wait a moment for endpoints to be released
        time.sleep(2)
        logger.info("All ngrok tunnels and processes terminated")
    except Exception as e:
        logger.warning(f"Error while killing existing tunnels: {e}")
        # Still try to kill processes
        try:
            ngrok.kill()
        except:
            pass

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
        
        # Kill any existing ngrok tunnels and processes
        kill_all_ngrok_tunnels()
        
        # Start new tunnel
        try:
            tunnel = ngrok.connect(port, bind_tls=True)
        except Exception as connect_error:
            error_str = str(connect_error)
            # Check if the error is about endpoint already being online
            if "already online" in error_str.lower() or "ERR_NGROK_334" in error_str:
                logger.error("=" * 80)
                logger.error("ERROR: An ngrok endpoint is already running!")
                logger.error("=" * 80)
                logger.error("\nThis usually happens when:")
                logger.error("1. Another ngrok tunnel is running in a different terminal")
                logger.error("2. A previous tunnel didn't close properly")
                logger.error("\nSolutions:")
                logger.error("1. Check for other ngrok processes: ps aux | grep ngrok")
                logger.error("2. Kill all ngrok processes: pkill -f ngrok")
                logger.error("3. Or wait a few minutes for the endpoint to expire")
                logger.error("=" * 80)
                logger.error("\nTrying to force kill all tunnels and retry...")
                
                # Force kill and wait longer
                kill_all_ngrok_tunnels()
                time.sleep(5)  # Wait longer for endpoint to be released
                
                # Try one more time
                logger.info("Retrying tunnel creation...")
                tunnel = ngrok.connect(port, bind_tls=True)
            else:
                raise
        
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
        logger.error("\nTroubleshooting tips:")
        logger.error("1. Check if another ngrok process is running: ps aux | grep ngrok")
        logger.error("2. Kill all ngrok processes: pkill -f ngrok")
        logger.error("3. Wait a few minutes and try again")
        raise
    finally:
        ngrok.kill()
        logger.info("Ngrok tunnel closed")

if __name__ == '__main__':
    start_ngrok_tunnel()

