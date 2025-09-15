import threading
import time
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

base_url = "https://xubill0707-3689e15b-0967-45ea-96e8-90e448d7f7c9.socketxp.com"
DELAY_ANALYZE = 10
DELAY_SUMMARY = 30

def call_analyze_users():
    """Call the analyze-users endpoint"""
    try:
        logger.info("🔍 Calling /api/analyze-users endpoint...")
        response = requests.post(f"{base_url}/api/analyze-users", timeout=30)
        response.raise_for_status()
        logger.info(f"✅ analyze-users completed: {response.status_code}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error calling analyze-users: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error in analyze-users: {e}")
        return None

def call_process_summaries():
    """Call the process-summaries endpoint"""
    try:
        logger.info("📊 Calling /api/process-summaries endpoint...")
        response = requests.post(f"{base_url}/api/process-summaries", timeout=30)
        response.raise_for_status()
        logger.info(f"✅ process-summaries completed: {response.status_code}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error calling process-summaries: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error in process-summaries: {e}")
        return None

def run_analyze_users_cron():
    """Background function that calls analyze-users endpoint every 10 seconds"""
    logger.info("🎯 Starting analyze-users cron job...")
    while True:
        try:
            call_analyze_users()
        except Exception as e:
            logger.error(f"💥 Error in analyze-users cron: {e}")
        
        # Wait 10 seconds before next call
        logger.info(f"😴 analyze-users waiting {DELAY_ANALYZE} seconds...")
        time.sleep(DELAY_ANALYZE)

def run_process_summaries_cron():
    """Background function that calls process-summaries endpoint every 10 seconds"""
    logger.info("🎯 Starting process-summaries cron job...")
    while True:
        try:
            call_process_summaries()
        except Exception as e:
            logger.error(f"💥 Error in process-summaries cron: {e}")
        
        # Wait 10 seconds before next call
        logger.info(f"😴 process-summaries waiting {DELAY_SUMMARY} seconds...")
        time.sleep(DELAY_SUMMARY)

# Start both cron jobs in separate background threads
analyze_thread = threading.Thread(target=run_analyze_users_cron, daemon=True)
summaries_thread = threading.Thread(target=run_process_summaries_cron, daemon=True)

analyze_thread.start()
summaries_thread.start()

if __name__ == '__main__':
    logger.info("🚀 Starting Periodic Task Server with 2 simultaneous cron jobs...")
    logger.info(f"📡 Base URL: {base_url}")
    logger.info("⏰ Both endpoints will be called every 10 seconds")
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(60)  # Check every minute that threads are alive
            if not analyze_thread.is_alive():
                logger.error("❌ analyze-users thread died, restarting...")
                analyze_thread = threading.Thread(target=run_analyze_users_cron, daemon=True)
                analyze_thread.start()
            
            if not summaries_thread.is_alive():
                logger.error("❌ process-summaries thread died, restarting...")
                summaries_thread = threading.Thread(target=run_process_summaries_cron, daemon=True)
                summaries_thread.start()
                
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down periodic task server...")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
