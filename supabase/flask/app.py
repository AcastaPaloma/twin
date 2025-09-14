
from flask import Flask, jsonify, request
from supabase import create_client, Client as SupabaseClient
import threading
import time
import cohere
import os
from twilio.rest import Client as TwilioClient
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
import re
import json
import logging
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
COHERE_API_KEY = os.getenv('COHERE_API_KEY')
SUPABASE_URL = os.getenv('SUPABASE_URL')  # Note: using actual env var name from .env (missing 'S')
SUPABASE_PUBLISHABLE_KEY = os.getenv('SUPABASE_PUBLISHABLE_KEY')


app = Flask(__name__)

# Initialize Supabase client
supabase: SupabaseClient = create_client(supabase_url=SUPABASE_URL, supabase_key=SUPABASE_PUBLISHABLE_KEY)

# Initialize Cohere client
co = cohere.ClientV2(api_key=COHERE_API_KEY)

twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


# TODO: MOVE THIS TO A NEW "SERVER" - this server should ONLY BE FOR EXISTING FUNCTIONS
# def my_periodic_task():
#     print("This runs every 3 seconds!")

# def run_periodic_task():
#     """Background function that runs the periodic task every 3 seconds"""
#     while True:
#         my_periodic_task()
#         time.sleep(3)

# # Start the periodic task in a background thread
# task_thread = threading.Thread(target=run_periodic_task, daemon=True)
# task_thread.start()

# =============================================================== #
# Twilio Sendgrid
# =============================================================== #

def send_sms(message_body: str, to_number: str): # 
    """
    Send SMS using Twilio and return success status
    
    Returns:
        dict: Contains 'success' (bool), 'message_sid' (str), 'status' (str), and 'error' (str) if failed
    """

    try:
        message = twilio_client.messages.create(
            body=message_body,
            from_=TWILIO_PHONE_NUMBER,
            to=to_number
        )
        
        return {
            'success': True,
            'message_sid': message.sid,
            'status': message.status,
            'to': to_number,
            'from': TWILIO_PHONE_NUMBER,
            'error': None
        }
    except Exception as e:
        return {
            'success': False,
            'message_sid': None,
            'status': 'failed',
            'to': to_number,
            'from': TWILIO_PHONE_NUMBER,
            'error': str(e)
        }

# =============================================================== #
# Video Transcript
# =============================================================== #

def get_youtube_transcript(youtube_url: str):
    """
    Extract transcript text from a YouTube video URL
    
    Args:
        youtube_url (str): The YouTube video URL
        
    Returns:
        str: The transcript text, or None if extraction fails
    """
    try:
        # Extract video ID from various YouTube URL formats
        video_id = None
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([a-zA-Z0-9_-]{11})',
            r'(?:youtube\.com\/.*[?&]v=)([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, youtube_url)
            if match:
                video_id = match.group(1)
                break
        
        if not video_id:
            return None
        
        # Initialize YouTubeTranscriptApi instance and fetch transcript
        ytt_api = YouTubeTranscriptApi()
        fetched_transcript = ytt_api.fetch(video_id)
        
        # Extract transcript snippets and combine into full text
        full_transcript_parts = []
        for snippet in fetched_transcript.snippets:
            full_transcript_parts.append(snippet.text)
        
        # Return the combined transcript text
        return ' '.join(full_transcript_parts)
        
    except Exception as e:
        print(f"Error fetching transcript: {str(e)}")
        return None
    
# =============================================================== #
# Website Scraping Content
# =============================================================== #

def scrape_website_info(url: str):
    """
    Scrape website content and return the body text
    
    Args:
        url (str): The website URL to scrape
        
    Returns:
        str: The website body content as text, or None if scraping fails
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        # Ensure URL has proper protocol
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Set headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Make request with timeout
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise exception for bad status codes
        
        # Parse HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Clean up text - remove extra whitespace and newlines
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
        
    except Exception as e:
        print(f"Error scraping website: {str(e)}")
        return None

# =============================================================== #
# Util Functions
# =============================================================== #

def get_user_by_phone_number(phone_number: str):
    """
    Get user information by phone number
    
    Args:
        phone_number (str): The phone number to look up
        
    Returns:
        dict: Contains user info and success status
    """
    try:
        print(f"🔍 Looking up user by phone number: {phone_number}")
        
        user_response = supabase.table('users') \
            .select('id, email, phone_number, name, onboarding_state') \
            .eq('phone_number', phone_number) \
            .execute()
        
        if not user_response.data:
            print(f"❌ No user found with phone number: {phone_number}")
            return {
                'success': False,
                'error': 'User not found',
                'phone_number': phone_number,
                'user_found': False,
                'user_info': None
            }
        
        user = user_response.data[0]
        user_email = user.get('email', 'No email')
        
        print(f"✅ Found user: {user_email} (ID: {user['id'][:8]}...)")
        
        return {
            'success': True,
            'phone_number': phone_number,
            'user_found': True,
            'user_info': user
        }
        
    except Exception as e:
        print(f"💥 Error looking up user by phone number {phone_number}: {e}")
        return {
            'success': False,
            'error': str(e),
            'phone_number': phone_number,
            'user_found': False,
            'user_info': None
        }

# =============================================================== #
# Onboarding System
# =============================================================== #

def validate_email_format(email: str) -> bool:
    """
    Simple email validation using regex
    
    Args:
        email (str): Email address to validate
        
    Returns:
        bool: True if email format is valid, False otherwise
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def check_onboarding_gates(phone_number: str) -> dict:
    """
    Check user's onboarding status and determine next gate
    
    Args:
        phone_number (str): The phone number to check
        
    Returns:
        dict: {
            'user_exists': bool,
            'user_info': dict or None,
            'onboarding_complete': bool,
            'next_gate': 'registration' | 'email' | 'name' | 'complete',
            'current_state': str or None
        }
    """
    try:
        print(f"🚪 Checking onboarding gates for {phone_number}")
        
        user_lookup = get_user_by_phone_number(phone_number)
        
        if not user_lookup['success'] or not user_lookup['user_found']:
            print(f"🆕 New user - needs registration")
            return {
                'user_exists': False,
                'user_info': None,
                'onboarding_complete': False,
                'next_gate': 'registration',
                'current_state': None
            }
        
        user_info = user_lookup['user_info']
        onboarding_state = user_info.get('onboarding_state')
        email = user_info.get('email')
        name = user_info.get('name')
        
        print(f"📊 User state: onboarding_state='{onboarding_state}', email='{email}', name='{name}'")
        
        # Determine next gate based on current state
        if onboarding_state is None:
            # User exists but no onboarding state set - check email
            if not email or email.strip() == '':
                next_gate = 'email'
                complete = False
            elif not name or name.strip() == '':
                next_gate = 'name'
                complete = False
            else:
                next_gate = 'complete'
                complete = True
        elif onboarding_state == 'awaiting_email':
            next_gate = 'email'
            complete = False
        elif onboarding_state == 'awaiting_name':
            next_gate = 'name'
            complete = False
        elif onboarding_state == 'complete':
            next_gate = 'complete'
            complete = True
        else:
            # Unknown state - default to checking fields
            if not email or email.strip() == '':
                next_gate = 'email'
                complete = False
            elif not name or name.strip() == '':
                next_gate = 'name'
                complete = False
            else:
                next_gate = 'complete'
                complete = True
        
        print(f"🎯 Next gate: {next_gate}, Complete: {complete}")
        
        return {
            'user_exists': True,
            'user_info': user_info,
            'onboarding_complete': complete,
            'next_gate': next_gate,
            'current_state': onboarding_state
        }
        
    except Exception as e:
        print(f"💥 Error checking onboarding gates: {e}")
        return {
            'user_exists': False,
            'user_info': None,
            'onboarding_complete': False,
            'next_gate': 'registration',
            'current_state': None,
            'error': str(e)
        }

def create_new_user(phone_number: str) -> dict:
    """
    Create new user with phone number, set state to 'awaiting_email'
    
    Args:
        phone_number (str): The phone number for the new user
        
    Returns:
        dict: Contains success status and user info
    """
    try:
        print(f"👤 Creating new user for {phone_number}")
        
        # Create new user with minimal info
        new_user_data = {
            'phone_number': phone_number,
            'email': None,  # NULL email, will be filled during onboarding
            'onboarding_state': 'awaiting_email',
            'is_active': True
        }
        
        response = supabase.table('users').insert([new_user_data]).execute()
        
        if response.data:
            user = response.data[0]
            print(f"✅ Created new user: {user['id'][:8]}... for {phone_number}")
            
            return {
                'success': True,
                'user_info': user,
                'message': 'User created successfully'
            }
        else:
            print(f"❌ Failed to create user for {phone_number}")
            return {
                'success': False,
                'error': 'Failed to create user in database'
            }
            
    except Exception as e:
        error_message = str(e)
        print(f"💥 Error creating user for {phone_number}: {error_message}")
        
        # Provide more specific error messages for common constraint violations
        if "users_email_key" in error_message:
            return {
                'success': False,
                'error': f'Email constraint violation: {error_message}'
            }
        elif "users_phone_number_key" in error_message:
            return {
                'success': False,
                'error': f'Phone number already exists: {phone_number}'
            }
        else:
            return {
                'success': False,
                'error': error_message
            }

def update_user_email(user_id: str, email: str) -> dict:
    """
    Update user email and set state to 'awaiting_name'
    
    Args:
        user_id (str): The user ID to update
        email (str): The email address to save
        
    Returns:
        dict: Contains success status and updated user info
    """
    try:
        print(f"📧 Updating email for user {user_id[:8]}... to {email}")
        
        response = supabase.table('users') \
            .update({
                'email': email,
                'onboarding_state': 'awaiting_name'
            }) \
            .eq('id', user_id) \
            .execute()
        
        if response.data:
            user = response.data[0]
            print(f"✅ Updated email for user {user_id[:8]}...")
            
            return {
                'success': True,
                'user_info': user,
                'message': 'Email updated successfully'
            }
        else:
            print(f"❌ Failed to update email for user {user_id[:8]}...")
            return {
                'success': False,
                'error': 'Failed to update email in database'
            }
            
    except Exception as e:
        print(f"💥 Error updating email for user {user_id[:8]}...: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def update_user_name(user_id: str, name: str) -> dict:
    """
    Update user name and set state to 'complete'
    
    Args:
        user_id (str): The user ID to update
        name (str): The name to save
        
    Returns:
        dict: Contains success status and updated user info
    """
    try:
        print(f"👤 Updating name for user {user_id[:8]}... to {name}")
        
        response = supabase.table('users') \
            .update({
                'name': name,
                'onboarding_state': 'complete'
            }) \
            .eq('id', user_id) \
            .execute()
        
        if response.data:
            user = response.data[0]
            print(f"✅ Updated name for user {user_id[:8]}... - Onboarding complete!")
            
            return {
                'success': True,
                'user_info': user,
                'message': 'Name updated successfully, onboarding complete'
            }
        else:
            print(f"❌ Failed to update name for user {user_id[:8]}...")
            return {
                'success': False,
                'error': 'Failed to update name in database'
            }
            
    except Exception as e:
        print(f"💥 Error updating name for user {user_id[:8]}...: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def handle_onboarding_flow(incoming_msg: str, sender_number: str, gate_status: dict):
    """
    Route onboarding messages based on gate status
    
    Args:
        incoming_msg (str): The incoming SMS message
        sender_number (str): The phone number of the sender
        gate_status (dict): Result from check_onboarding_gates()
    """
    try:
        next_gate = gate_status['next_gate']
        user_info = gate_status.get('user_info')
        
        print(f"🚪 Handling onboarding gate: {next_gate}")
        
        if next_gate == 'registration':
            # Gate #1: New user registration
            print("🆕 Gate #1: New user registration")
            
            # Create new user
            result = create_new_user(sender_number)
            
            if result['success']:
                # Send welcome message
                welcome_msg = """👋 Welcome to Twin! I'm your intelligent learning assistant that tracks your browsing to help you learn better.

I analyze your web activity and send personalized learning insights via SMS.

To get started, please reply with your email address."""
                
                send_result = send_sms(welcome_msg, sender_number)
                if send_result['success']:
                    print("✅ Welcome message sent successfully")
                else:
                    print(f"❌ Failed to send welcome message: {send_result}")
            else:
                # Send error message
                error_msg = "Sorry, there was an issue setting up your account. Please try again later."
                send_sms(error_msg, sender_number)
                print(f"❌ Failed to create user: {result}")
        
        elif next_gate == 'email':
            # Gate #2: Email collection
            print("📧 Gate #2: Email collection")
            
            # Validate email format
            if validate_email_format(incoming_msg):
                # Valid email - save it
                user_id = user_info['id']
                result = update_user_email(user_id, incoming_msg)
                
                if result['success']:
                    # Send name request message
                    name_request_msg = "✨ Perfect! Last step - what's your name? This helps me personalize your learning experience."
                    
                    send_result = send_sms(name_request_msg, sender_number)
                    if send_result['success']:
                        print("✅ Name request sent successfully")
                    else:
                        print(f"❌ Failed to send name request: {send_result}")
                else:
                    # Send error message
                    error_msg = "Sorry, there was an issue saving your email. Please try again."
                    send_sms(error_msg, sender_number)
                    print(f"❌ Failed to update email: {result}")
            else:
                # Invalid email format
                invalid_email_msg = "❌ That email format doesn't look right. Please send a valid email address (example: you@gmail.com)"
                
                send_result = send_sms(invalid_email_msg, sender_number)
                if send_result['success']:
                    print("✅ Invalid email message sent successfully")
                else:
                    print(f"❌ Failed to send invalid email message: {send_result}")
        
        elif next_gate == 'name':
            # Gate #3: Name collection
            print("👤 Gate #3: Name collection")
            
            # Any non-empty string is valid for name
            name = incoming_msg.strip()
            if name:
                user_id = user_info['id']
                result = update_user_name(user_id, name)
                
                if result['success']:
                    # Send completion message
                    completion_msg = f"🎉 All set, {name}! I'm now your personal learning assistant. I'll track your browsing patterns and send helpful insights.\n\nTry sending me a YouTube video or website URL to get started!"
                    
                    send_result = send_sms(completion_msg, sender_number)
                    if send_result['success']:
                        print("✅ Onboarding completion message sent successfully")
                    else:
                        print(f"❌ Failed to send completion message: {send_result}")
                else:
                    # Send error message
                    error_msg = "Sorry, there was an issue saving your name. Please try again."
                    send_sms(error_msg, sender_number)
                    print(f"❌ Failed to update name: {result}")
            else:
                # Empty name
                empty_name_msg = "Please tell me your name so I can personalize your experience."
                
                send_result = send_sms(empty_name_msg, sender_number)
                if send_result['success']:
                    print("✅ Empty name message sent successfully")
                else:
                    print(f"❌ Failed to send empty name message: {send_result}")
        
        else:
            print(f"❓ Unknown gate: {next_gate}")
            
    except Exception as e:
        print(f"💥 Error in handle_onboarding_flow: {e}")
        # Send generic error message
        error_msg = "Sorry, something went wrong. Please try again."
        send_sms(error_msg, sender_number)

def get_user_summaries_between_dates(user_id: str, start_timestamp: str, end_timestamp: str, only_unprocessed: bool = True):
    """
    Retrieve user summaries between two timestamps
    
    Args:
        user_id (str): The user ID to fetch summaries for
        start_timestamp (str): Start time in ISO format (inclusive)
        end_timestamp (str): End time in ISO format (inclusive)
        only_unprocessed (bool): If True, only fetch summaries that haven't been processed yet
        
    Returns:
        dict: Contains user info, summaries, and metadata
    """
    try:
        print(f"📊 Fetching summaries for user {user_id[:8]}...")
        print(f"📅 Time range: {start_timestamp} to {end_timestamp}")
        
        # Get user info
        user_response = supabase.table('users') \
            .select('id, email, phone_number') \
            .eq('id', user_id) \
            .execute()
        
        if not user_response.data:
            print(f"❌ No user found with ID: {user_id}")
            return {
                'success': False,
                'error': 'User not found',
                'user_id': user_id,
                'user_found': False,
                'summaries_count': 0,
                'summaries': []
            }
        
        user = user_response.data[0]
        user_email = user.get('email', 'No email')
        user_phone = user.get('phone_number', 'No phone')
        
        print(f"✅ Found user: {user_email} (ID: {user_id[:8]}...)")
        
        # Fetch summaries for this user within the specified time range
        summaries_response = supabase.table('summaries') \
            .select('id, user_id, summary, prompt_generated_at, cohere_finish_reason, cohere_usage, source_activity_ids, processed') \
            .eq('user_id', user_id) \
            .gte('prompt_generated_at', start_timestamp) \
            .lte('prompt_generated_at', end_timestamp) \
            .order('prompt_generated_at', desc=True) \
            .execute()
        
        if summaries_response.data is None:
            print(f"❌ Error fetching summaries for user {user_email}")
            return {
                'success': False,
                'error': 'Error fetching summaries',
                'user_id': user_id,
                'user_found': True,
                'user_info': user,
                'summaries_count': 0,
                'summaries': []
            }
        
        summaries = summaries_response.data
        summaries_count = len(summaries)
        
        print(f"📈 Found {summaries_count} summaries for {user_email} in specified time range")
        
        # Format summaries for easy use
        formatted_summaries = []
        unprocessed_summaries = []
        all_summaries_text = ""
        
        for summary in summaries:
            # Extract summary text content
            summary_text = ""
            if summary.get('summary'):
                if isinstance(summary['summary'], list):
                    for item in summary['summary']:
                        if isinstance(item, dict) and 'text' in item:
                            summary_text += item['text']
                elif isinstance(summary['summary'], str):
                    summary_text = summary['summary']
            
            formatted_summary = {
                'id': summary['id'],
                'prompt_generated_at': summary.get('prompt_generated_at'),
                'summary_text': summary_text,
                'cohere_finish_reason': summary.get('cohere_finish_reason'),
                'cohere_usage': summary.get('cohere_usage'),
                'source_activity_count': len(summary.get('source_activity_ids', [])),
                'processed': summary.get('processed', False)
            }
            
            formatted_summaries.append(formatted_summary)
            
            # Track unprocessed summaries separately
            if not summary.get('processed', False):
                unprocessed_summaries.append(formatted_summary)
            
            all_summaries_text += f"\n\n--- Summary from {summary.get('prompt_generated_at', 'Unknown time')} ---\n{summary_text}"
        
        return {
            'success': True,
            'user_id': user_id,
            'user_found': True,
            'user_info': user,
            'summaries_count': summaries_count,
            'unprocessed_count': len(unprocessed_summaries),
            'summaries': formatted_summaries,
            'unprocessed_summaries': unprocessed_summaries,
            'combined_summaries_text': all_summaries_text,
            'time_range': f"{start_timestamp} to {end_timestamp}"
        }
        
    except Exception as e:
        print(f"💥 Error fetching user summaries for {user_id}: {e}")
        return {
            'success': False,
            'error': str(e),
            'user_id': user_id,
            'user_found': False,
            'summaries_count': 0,
            'summaries': []
        }

def get_message_history(phone_number: str, limit: int = 50):
    """
    Retrieve previous messages with a specific phone number
    
    Args:
        phone_number (str): The phone number to get message history for
        limit (int): Maximum number of messages to retrieve (default: 50)
        
    Returns:
        dict: Contains message history and metadata
    """
    try:
        print(f"📞 Fetching message history for {phone_number} (limit: {limit})")
        
        # Get messages where this number was either the sender OR recipient
        # We need to check both directions since messages can go both ways
        messages_from = twilio_client.messages.list(
            from_=phone_number,
            limit=limit
        )
        
        messages_to = twilio_client.messages.list(
            to=phone_number,
            limit=limit
        )
        
        # Combine and sort messages by date (most recent first)
        all_messages = messages_from + messages_to
        
        # Remove duplicates and sort by date_created (newest first)
        unique_messages = {}
        for msg in all_messages:
            unique_messages[msg.sid] = msg
        
        sorted_messages = sorted(
            unique_messages.values(),
            key=lambda x: x.date_created,
            reverse=True
        )[:limit]  # Take only the requested limit after sorting
        
        # Format message history for easy use
        formatted_history = []
        for msg in sorted_messages:
            formatted_msg = {
                'sid': msg.sid,
                'from': msg.from_,
                'to': msg.to,
                'body': msg.body,
                'direction': msg.direction,
                'status': msg.status,
                'date_created': msg.date_created.isoformat() if msg.date_created else None,
                'date_sent': msg.date_sent.isoformat() if msg.date_sent else None,
                'num_media': msg.num_media
            }
            formatted_history.append(formatted_msg)
        
        print(f"📊 Found {len(formatted_history)} messages in history with {phone_number}")
        
        # Create a summary of the conversation
        inbound_count = len([m for m in formatted_history if m['direction'] == 'inbound'])
        outbound_count = len([m for m in formatted_history if m['direction'] in ['outbound-api', 'outbound-call']])
        
        return {
            'success': True,
            'phone_number': phone_number,
            'total_messages': len(formatted_history),
            'inbound_messages': inbound_count,
            'outbound_messages': outbound_count,
            'messages': formatted_history,
            'conversation_summary': {
                'total_messages': len(formatted_history),
                'inbound_count': inbound_count,
                'outbound_count': outbound_count,
                'last_message_date': formatted_history[0]['date_created'] if formatted_history else None,
                'first_message_date': formatted_history[-1]['date_created'] if formatted_history else None
            }
        }
        
    except Exception as e:
        print(f"💥 Error fetching message history for {phone_number}: {e}")
        return {
            'success': False,
            'error': str(e),
            'phone_number': phone_number,
            'total_messages': 0,
            'messages': []
        }

def create_intelligent_response_prompt(incoming_message: str, sender_number: str, message_history: dict = None, user_summaries: dict = None):
    """
    Create an intelligent prompt for the Cohere agent to respond to incoming SMS messages
    
    Args:
        incoming_message (str): The current SMS message from the user
        sender_number (str): The phone number of the sender
        message_history (dict): Previous conversation history with this user
        user_summaries (dict): User's recent learning summaries
        
    Returns:
        str: Comprehensive prompt for the Cohere agent
    """
    
    # Build context sections
    message_context = ""
    learning_context = ""
    conversation_context = ""
    
    # Add message history context
    if message_history and message_history.get('success'):
        total_msgs = message_history.get('total_messages', 0)
        recent_messages = message_history.get('messages', [])
        
        conversation_context = f"""
            CONVERSATION HISTORY:
            - Total previous messages with this user: {total_msgs}
            - Inbound messages: {message_history.get('inbound_messages', 0)}
            - Outbound messages: {message_history.get('outbound_messages', 0)}

            Recent conversation (most recent first):"""
        
        for i, msg in enumerate(recent_messages[:10]):  # Last 10 messages for better context
            direction = "📤 User" if msg['direction'] == 'inbound' else "📥 Assistant"
            timestamp = msg.get('date_created', 'Unknown time')[:16]  # Just date and time
            conversation_context += f"\n{i+1}. [{timestamp}] {direction}: {msg['body']}"
    
    # Add learning context from summaries
    if user_summaries and user_summaries.get('success'):
        summaries_count = user_summaries.get('summaries_count', 0)
        summaries = user_summaries.get('summaries', [])
        
        learning_context = f"""
        USER'S LEARNING CONTEXT (Past 36 hours):
        - Total learning summaries available: {summaries_count}

        Recent Learning Topics and Activities:"""
        
        for i, summary in enumerate(summaries[:5]):  # Show last 5 summaries for better context
            timestamp = summary.get('prompt_generated_at', 'Unknown time')[:16]
            summary_text = summary.get('summary_text', 'No summary available')
            # Include full summary to preserve URLs and detailed context
            # This is critical for answering questions about specific websites/resources consulted
            summary_preview = summary_text[:2000] + '...' if len(summary_text) > 2000 else summary_text
            learning_context += f"\n{i+1}. [{timestamp}]: {summary_preview}"
    
    # Create the comprehensive prompt
    prompt = f"""You are an intelligent learning assistant responding to an SMS message. Your goal is to provide helpful, contextual responses that support the user's learning journey.

                CURRENT MESSAGE FROM USER:
                "{incoming_message}"
                From: {sender_number}

                {conversation_context}

                {learning_context}

                CRITICAL WORKFLOW RULES:
                1. **ALWAYS END WITH SMS**: Every interaction MUST conclude with at least one send_sms call to respond to the user
                2. **CONNECT RECENT MESSAGES**: Look at the most recent 2-3 messages to understand context. If the user previously asked a question and now provides a URL/resource, treat them as connected
                3. **COMPLETE THE REQUEST**: If you use tools like get_youtube_transcript or scrape_website_info, you MUST then send SMS messages that address the original request with the gathered information
                4. **USE LEARNING CONTEXT**: You HAVE ACCESS to the user's detailed browsing history with URLs, titles, and timestamps in the learning context above. When users ask about their browsing history, visited websites, or learning resources, reference this data directly.

                YOUR RESPONSE STRATEGY:
                Based on the user's message, conversation history, and learning context, you should:

                1. **ANALYZE THE FULL CONTEXT**: 
                - Look at the current message AND recent previous messages (last 2-3 exchanges)
                - Is this message providing additional info to a previous request? (e.g., "summarize this video" followed by a YouTube link)
                - Are they asking for help with a specific topic?
                - Are they sharing new learning goals or providing resources?
                - Is this completing a multi-part request?
                - Are they asking about their browsing history, visited URLs, or learning resources? CHECK THE LEARNING CONTEXT SECTION ABOVE - it contains detailed browsing data with URLs, titles, and timestamps.

                2. **USE TOOLS STRATEGICALLY, THEN RESPOND**:
                - **get_youtube_transcript**: If they provide a YouTube URL OR previously asked about a video
                - **scrape_website_info**: If they provide a website URL OR previously asked about web content
                - **send_sms**: MANDATORY - Always conclude with SMS responses that:
                  * Acknowledge their request
                  * Summarize key findings from any tools used OR reference their browsing history from learning context
                  * Provide actionable insights or answers
                  * Ask follow-up questions to continue the conversation

                3. **MULTI-MESSAGE CONTEXT HANDLING**:
                - If recent messages seem related, treat them as one continuous request
                - Example: "can you summarize this video?" followed by "youtube.com/watch?v=abc" = fetch transcript + provide summary via SMS
                - Example: "help me understand React" followed by "reactjs.org" = scrape website + explain React concepts via SMS
                - Always connect the dots between related messages

                4. **RESPONSE GUIDELINES**:
                - Be conversational and friendly (this is SMS, keep it personal)
                - Reference their previous learning if relevant
                - ALWAYS summarize findings from tools in your SMS responses
                - When asked about browsing history/URLs: Extract specific URLs, titles, and domains from the learning context data above
                - Provide actionable insights or next steps
                - Keep individual SMS messages focused but send multiple if needed
                - Connect new information to their existing learning patterns

                5. **BROWSING HISTORY QUERIES**:
                - When users ask "what URLs did I visit?", "remind me of websites I consulted", or similar questions about their browsing history:
                  * Look through ALL the learning summaries in the USER'S LEARNING CONTEXT section above
                  * Extract specific URLs, titles, domains, and timestamps from the learning_graph data
                  * Organize by topic or chronologically as appropriate
                  * Include both the URL and the page title when available
                  * Mention the learning value and relevance if provided
                - NEVER say "I don't have access to URLs" - you DO have access via the learning context data above

                6. **LEARNING FOCUS**:
                - Help them make connections between concepts
                - Identify knowledge gaps and suggest resources
                - Provide practical applications of theoretical concepts
                - Ask thought-provoking questions about their learning

                7. **CONVERSATION FLOW**:
                - Acknowledge their current message AND any related recent messages
                - Build on previous conversations when relevant
                - Use their learning history to provide more personalized advice
                - Maintain continuity in your relationship as their learning assistant

                EXAMPLE WORKFLOWS:
                - User sends: "can you summarize this video?" then "youtube.com/abc"
                  → get_youtube_transcript → send_sms with video summary + insights + follow-up questions
                
                - User sends: "help me learn about X" then "website.com/about-X"
                  → scrape_website_info → send_sms with key concepts + learning plan + questions
                
                - User sends: just a YouTube/website URL after previously asking about that topic
                  → use appropriate tool → send_sms with analysis related to their previous question

                - User asks: "Can you remind me of the URLs I visited?" or "what websites did I consult?"
                  → Look through learning context above → Extract URLs, titles, domains from learning summaries → send_sms with organized list of visited resources + context about what they were learning

                Remember: You must ALWAYS send SMS responses to complete the conversation. Tools are for gathering information, SMS is for communicating with the user. Never use tools without following up with SMS responses that address their original request.
                """
    
    # Save prompt to txt file
    with open('system_prompt.txt', 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    return prompt

# =============================================================== #
# Cohere Analytics
# =============================================================== #

def process_user_with_cohere(user_id, user_email=None, check_recent_activity=True):
    """
    Process a single user's unprocessed activities with Cohere in a separate thread
    
    Args:
        user_id (str): The user ID to process
        user_email (str): Optional user email for logging
        check_recent_activity (bool): If True, skip processing if most recent activity was within 60 seconds
    """
    thread_name = threading.current_thread().name
    user_label = user_email or user_id[:8] + "..."
    
    try:
        print(f"🧵 [{thread_name}] Starting analysis for user {user_label}")
        
        # Get unprocessed activities for this user
        unprocessed_response = supabase.table('activities') \
            .select('id, timestamp, domain, title, url') \
            .eq('user_id', user_id) \
            .eq('processed', False) \
            .execute()
            
        if unprocessed_response.data is None:
            print(f'❌ [{thread_name}] Error fetching unprocessed activities for {user_label}')
            return
            
        unprocessed_activities = unprocessed_response.data
        print(f"📊 [{thread_name}] Found {len(unprocessed_activities)} unprocessed activities for {user_label}")
        
        if not unprocessed_activities or len(unprocessed_activities) == 0:
            print(f"⏩ [{thread_name}] No unprocessed activities for {user_label}, skipping")
            return
        
        # Check if most recent activity is too recent (within 60 seconds)
        if check_recent_activity:
            from datetime import datetime, timezone, timedelta
            now = datetime.now(timezone.utc)
            
            # Find the most recent activity timestamp
            most_recent_timestamp = None
            for activity in unprocessed_activities:
                activity_time_str = activity.get('timestamp')
                if activity_time_str:
                    try:
                        # Parse the timestamp - handle both with and without timezone info
                        if activity_time_str.endswith('Z'):
                            activity_time = datetime.fromisoformat(activity_time_str.replace('Z', '+00:00'))
                        elif '+' in activity_time_str or activity_time_str.endswith('00'):
                            activity_time = datetime.fromisoformat(activity_time_str)
                        else:
                            # Assume UTC if no timezone info
                            activity_time = datetime.fromisoformat(activity_time_str).replace(tzinfo=timezone.utc)
                        
                        if most_recent_timestamp is None or activity_time > most_recent_timestamp:
                            most_recent_timestamp = activity_time
                    except Exception as parse_error:
                        print(f"⚠️ [{thread_name}] Error parsing timestamp '{activity_time_str}': {parse_error}")
                        continue
            
            if most_recent_timestamp:
                time_since_recent = now - most_recent_timestamp
                if time_since_recent.total_seconds() < 60:
                    print(f"⏰ [{thread_name}] Skipping {user_label} - most recent activity was {time_since_recent.total_seconds():.1f} seconds ago (< 60s)")
                    return
                else:
                    print(f"✅ [{thread_name}] Most recent activity for {user_label} was {time_since_recent.total_seconds():.1f} seconds ago, proceeding with processing")
            
            
        # Create detailed activity descriptions for Cohere
        activity_descriptions = []
        key_urls = []
        
        for activity in unprocessed_activities:
            # Build detailed activity entry with URL for potential future processing
            activity_entry = f"Time: {activity['timestamp']}\nDomain: {activity['domain']}\nTitle: {activity['title']}\nURL: {activity.get('url', 'N/A')}\n"
            activity_descriptions.append(activity_entry)
            
            # Collect URLs that might be important learning resources
            if activity.get('url'):
                key_urls.append(activity['url'])
        
        activity_text = '\n'.join(activity_descriptions)
        
        # Create comprehensive learning graph prompt that analyzes all URLs
        prompt = f"""Analyze this user's browsing activity and create a comprehensive learning graph showing their educational journey:

                BROWSING ACTIVITY DATA:
                {activity_text}

                INSTRUCTIONS:
                Create a JSON response that maps the user's learning journey as a hierarchical graph structure. Analyze ALL URLs in the browsing history and categorize them based on their educational relevance.

                REQUIRED JSON STRUCTURE:
                {{
                  "learning_overview": {{
                    "primary_learning_focus": "Main subject/skill the user is studying",
                    "secondary_topics": ["related", "topics", "being", "explored"],
                    "learning_stage": "beginner|intermediate|advanced",
                    "total_learning_urls": number_of_educational_urls
                  }},
                  "learning_graph": {{
                    "main_topic_1": {{
                      "topic_name": "Primary Learning Topic",
                      "relevance_score": 0.9,
                      "sub_topics": {{
                        "sub_topic_1": {{
                          "name": "Specific subtopic",
                          "urls": [
                            {{
                              "url": "full_url_here",
                              "title": "page_title",
                              "domain": "domain.com",
                              "timestamp": "visit_time",
                              "learning_value": "high|medium|low",
                              "content_type": "tutorial|documentation|video|article|course|tool",
                              "relevance_explanation": "Why this URL is relevant to learning"
                            }}
                          ]
                        }}
                      }}
                    }}
                  }},
                  "key_resources": {{
                    "high_value_urls": [
                      {{
                        "url": "most_valuable_learning_url",
                        "title": "page_title",
                        "learning_value_reason": "Why this is particularly valuable for AI analysis"
                      }}
                    ],
                    "recommended_for_ai_analysis": [
                      {{
                        "url": "url_for_deep_analysis", 
                        "content_type": "youtube_video|documentation|tutorial",
                        "analysis_priority": "high|medium|low"
                      }}
                    ]
                  }},
                  "learning_patterns": {{
                    "browsing_behavior": "Sequential learning|Random exploration|Deep dive focus|Comparative research",
                    "knowledge_gaps": ["identified", "gaps", "in", "understanding"],
                    "progression_indicators": ["signs", "of", "learning", "advancement"]
                  }}
                }}

                ANALYSIS GUIDELINES:
                1. Include EVERY URL that has ANY educational relevance - don't filter too strictly
                2. Group URLs by main learning topics, then by subtopics
                3. Assign learning_value (high/medium/low) based on educational content depth
                4. Identify content_type accurately (tutorial, documentation, video, etc.)
                5. Calculate relevance_score for main topics (0.0-1.0) based on frequency and depth
                6. Prioritize URLs for AI analysis based on content richness (YouTube videos, documentation, tutorials)
                7. Look for learning patterns across time - are they progressing through topics systematically?
                8. Identify knowledge gaps where the user might need additional resources

                CONTENT TYPE DEFINITIONS:
                - tutorial: Step-by-step learning content
                - documentation: Official docs, references, specifications
                - video: YouTube, educational videos, lectures
                - article: Blog posts, explanatory articles
                - course: Structured learning platforms (Coursera, Udemy, etc.)
                - tool: Development tools, sandboxes, interactive learning

                Return ONLY the JSON object, no additional text."""
        
        print(f"🤖 [{thread_name}] Calling Cohere API for {user_label}...")
        
        # Call Cohere API
        response = co.chat(
            model='command-r-plus',
            messages=[
                {
                    'role': 'user',
                    'content': prompt,
                },
            ],
            response_format={"type": "json_object"},
        )
        
        print(f"✅ [{thread_name}] Received Cohere response for {user_label}")
        
        # Extract text content from Cohere response
        summary_text = ""
        summary_content_serializable = []
        
        if response and hasattr(response, 'message') and hasattr(response.message, 'content'):
            content = response.message.content
            if isinstance(content, list):
                for item in content:
                    if hasattr(item, 'text'):
                        summary_text += item.text
                        summary_content_serializable.append({
                            'type': 'text', 
                            'text': item.text
                        })
                    elif isinstance(item, dict):
                        if 'text' in item:
                            summary_text += item['text']
                            summary_content_serializable.append(item)
                        else:
                            text_content = str(item)
                            summary_text += text_content
                            summary_content_serializable.append({
                                'type': 'text',
                                'text': text_content
                            })
            else:
                summary_text = str(content)
                summary_content_serializable = [{'type': 'text', 'text': summary_text}]
        
        # Extract URLs from the response for future AI processing
        import re
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        extracted_urls = list(set(re.findall(url_pattern, summary_text)))
        
        # Also include the original key URLs from activities
        all_key_urls = list(set(key_urls + extracted_urls))
        
        # Convert usage to serializable format
        usage_serializable = None
        if hasattr(response, 'usage') and response.usage:
            usage_serializable = {
                'input_tokens': getattr(response.usage, 'input_tokens', None),
                'output_tokens': getattr(response.usage, 'output_tokens', None),
                'total_tokens': getattr(response.usage, 'total_tokens', None),
            }
        
        # Insert summary into database
        from datetime import datetime
        summary_payload = {
            'user_id': user_id,
            'summary': summary_content_serializable,
            'cohere_finish_reason': getattr(response, 'finish_reason', None),
            'cohere_usage': usage_serializable,
            'cohere_prompt': prompt,
            'source_activity_ids': [a['id'] for a in unprocessed_activities],
            'prompt_generated_at': datetime.now().isoformat(),
        }
        
        summary_insert_response = supabase.table('summaries').insert([summary_payload]).execute()
        
        if summary_insert_response.data:
            print(f'💾 [{thread_name}] Summary saved for {user_label}')
            
            # Mark activities as processed
            activity_ids = [a['id'] for a in unprocessed_activities]
            update_response = supabase.table('activities') \
                .update({'processed': True}) \
                .in_('id', activity_ids) \
                .execute()
                
            if update_response.data:
                print(f'✅ [{thread_name}] Marked {len(activity_ids)} activities as processed for {user_label}')
            else:
                print(f'⚠️ [{thread_name}] Failed to mark activities as processed for {user_label}')
        else:
            print(f'❌ [{thread_name}] Error saving summary for {user_label}:', summary_insert_response)
            
    except Exception as e:
        print(f'💥 [{thread_name}] Error processing user {user_label}: {str(e)}')


def analyze_all_users():
    """
    Analyze all users and their activities using Supabase and Cohere with threading
    
    Returns:
        str: Status message indicating success or failure
    """
    print("🔍 Starting multi-threaded user analysis...")
    
    try:
        # Fetch all users
        print("📋 Fetching all users...")
        users_response = supabase.table('users').select('id, email').execute()
        
        if users_response.data is None:
            print('❌ Error fetching users:', users_response)
            return f"Error fetching users"
            
        users = users_response.data
        print(f"✅ Found {len(users)} users to process")
        
        if not users:
            return "No users found to process"
        
        # Create threads for each user
        threads = []
        max_threads = min(len(users), 5)  # Limit to 5 concurrent threads to avoid overwhelming APIs
        
        print(f"🧵 Creating up to {max_threads} threads for processing...")
        
        for i, user in enumerate(users):
            if i >= max_threads:
                # Wait for some threads to complete before starting new ones
                for thread in threads[:max_threads//2]:
                    thread.join()
                threads = [t for t in threads if t.is_alive()]
            
            thread = threading.Thread(
                target=process_user_with_cohere,
                args=(user['id'], user.get('email')),  # check_recent_activity=True by default
                name=f"UserThread-{i+1}"
            )
            thread.start()
            threads.append(thread)
            
            # Small delay to stagger API calls
            time.sleep(0.5)
        
        # Wait for all threads to complete
        print(f"⏳ Waiting for all {len(threads)} threads to complete...")
        for thread in threads:
            thread.join()
        
        print("🎉 All users processed!")
        return f"✅ Successfully processed {len(users)} users with threading"
        
    except Exception as error:
        print('💥 Fatal error in analyze_all_users:', error)
        return f"Fatal error: {error}"


def analyze_single_user_legacy():
    """
    Original single-user analysis function (kept for reference/testing)
    Tests connection with the original test user
    """
    test_user_id = '123e4567-e89b-12d3-a456-426614174000'
    print(f"� Testing single user analysis for {test_user_id}...")
    
    try:
        process_user_with_cohere(test_user_id, "test@example.com")  # check_recent_activity=True by default
        return f"✅ Single user test completed"
    except Exception as error:
        print('💥 Error in single user test:', error)
        return f"Error in single user test: {error}"


@app.route('/api/analyze-users', methods=['POST'])
def api_analyze_users():
    """API endpoint to analyze all users with Cohere"""
    try:
        result = analyze_all_users()
        
        # analyze_all_users returns a string, so we need to format it properly
        if result.startswith('✅'):
            return jsonify({
                'success': True,
                'message': result
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================== #
# Cohere Summaries Parsing
# =============================================================== #

def process_single_user_summaries(user, twenty_four_hours_ago, results_dict, index):
    """
    Process a single user's summaries with Cohere in a separate thread
    
    Args:
        user (dict): User data with id, email, phone_number
        twenty_four_hours_ago (str): ISO timestamp for 24 hours ago
        results_dict (dict): Shared dictionary to store results
        index (int): User index for thread naming
    """
    thread_name = threading.current_thread().name
    user_id = user['id']
    user_email = user.get('email', 'No email')
    user_phone = user.get('phone_number', None)
    user_label = user_email if user_email != 'No email' else user_id[:8] + "..."
    
    try:
        print(f"🧵 [{thread_name}] Processing summaries for user: {user_label}")
        
        # Skip users without phone numbers
        if not user_phone:
            print(f"⚠️ [{thread_name}] Skipping user {user_label} - no phone number available")
            results_dict[index] = {
                'user_id': user_id,
                'user_email': user_email,
                'success': False,
                'error': 'No phone number available',
                'summaries_count': 0,
                'unprocessed_count': 0,
                'agent_execution': None
            }
            return
        
        # Calculate timestamps for past 24 hours
        from datetime import datetime, timedelta, timezone
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=24)
        
        start_timestamp = start_time.isoformat()
        end_timestamp = end_time.isoformat()
        
        # Use the new function to fetch summaries for this user from the past 24 hours
        user_summaries = get_user_summaries_between_dates(user_id, start_timestamp, end_timestamp)
        
        if not user_summaries['success'] or not user_summaries['user_found']:
            print(f'❌ [{thread_name}] Error fetching summaries for {user_label}: {user_summaries.get("error", "Unknown error")}')
            results_dict[index] = {
                'user_id': user_id,
                'user_email': user_email,
                'success': False,
                'error': user_summaries.get('error', 'Error fetching summaries'),
                'summaries_count': 0,
                'unprocessed_count': 0,
                'agent_execution': None
            }
            return
        
        summaries_count = user_summaries['summaries_count']
        unprocessed_count = user_summaries['unprocessed_count']
        summaries = user_summaries['summaries']
        unprocessed_summaries = user_summaries['unprocessed_summaries']
        all_summaries_text = user_summaries['combined_summaries_text']
        
        print(f"📊 [{thread_name}] Found {summaries_count} total summaries ({unprocessed_count} unprocessed) for {user_label} in the past 24 hours")
        
        # Fetch recent message history for context
        print(f"📞 [{thread_name}] Fetching message history for {user_label} to provide conversation context")
        message_history = get_message_history(user_phone, limit=20)  # Get last 20 messages for context
        
        # Process each summary for this user
        user_result = {
            'user_id': user_id,
            'user_email': user_email,
            'user_phone': user_phone,
            'success': True,
            'summaries_count': summaries_count,
            'unprocessed_count': unprocessed_count,
            'message_history_count': message_history.get('total_messages', 0) if message_history and message_history.get('success') else 0,
            'summaries': summaries,  # Already formatted by the new function
            'agent_execution': None
        }
        
        # Only execute Cohere agent if we have unprocessed summaries to analyze
        if unprocessed_count > 0:
            print(f"🤖 [{thread_name}] Executing Cohere agent for {user_label} with {unprocessed_count} unprocessed summaries")
            
            # Separate new (unprocessed) summaries from old (processed) ones for better context
            new_summaries_text = ""
            processed_summaries_text = ""
            
            for summary in summaries:
                summary_text = summary.get('summary_text', '')
                timestamp = summary.get('prompt_generated_at', 'Unknown time')
                
                if summary.get('processed', False):
                    processed_summaries_text += f"\n\n--- PROCESSED Summary from {timestamp} ---\n{summary_text}"
                else:
                    new_summaries_text += f"\n\n--- NEW Summary from {timestamp} ---\n{summary_text}"
            
            # Build conversation context from message history
            conversation_context = ""
            if message_history and message_history.get('success') and message_history.get('total_messages', 0) > 0:
                recent_messages = message_history.get('messages', [])[:10]  # Last 10 messages
                conversation_context = f"""
                RECENT CONVERSATION HISTORY ({message_history.get('total_messages', 0)} total messages):
                """
                
                for i, msg in enumerate(recent_messages):
                    direction = "📤 User" if msg['direction'] == 'inbound' else "📥 Assistant"
                    timestamp = msg.get('date_created', 'Unknown time')[:16] if msg.get('date_created') else 'Unknown time'
                    # Preserve full message context for better AI understanding
                    body = msg.get('body', '')[:500] + '...' if len(msg.get('body', '')) > 500 else msg.get('body', '')
                    conversation_context += f"\n{i+1}. [{timestamp}] {direction}: {body}"
            
            # Create enhanced prompt for the agent with conversation context and smart messaging
            agent_prompt = f"""You are an intelligent learning assistant. You've been analyzing this user's browsing activities and have generated learning summaries. Now you need to decide whether to send helpful SMS messages based on their NEW learning activities.

                IMPORTANT CONTEXT:
                - You have access to ALL their recent summaries for context
                - But you should FOCUS PRIMARILY on the NEW (unprocessed) summaries
                - Only send SMS if the new learning adds meaningful value
                - Don't repeat topics you've recently discussed with them

                {conversation_context}

                PREVIOUS LEARNING SUMMARIES (Already discussed):
                {processed_summaries_text if processed_summaries_text else "No previous summaries processed yet."}

                NEW LEARNING SUMMARIES (Focus on these):
                {new_summaries_text}

                DECISION CRITERIA - Only send SMS messages if:
                1. **New learning is substantial**: The new summaries show significant new topics or meaningful progress
                2. **Not repetitive**: The topics haven't been extensively covered in recent conversations
                3. **Actionable insights available**: You can provide specific questions, suggestions, or next steps
                4. **Different from recent messages**: Don't repeat advice or topics from recent SMS exchanges

                YOUR TASK:
                1. **Analyze the NEW summaries** in context of their conversation history
                2. **Decide if messaging is warranted** based on the criteria above
                3. **If messaging is warranted**: Send 1-3 focused SMS messages with:
                   - Specific questions about their NEW learning
                   - Connections between new and previous topics (if relevant)
                   - Actionable next steps for their new areas of study
                   - Insights that build on their learning trajectory

                MESSAGING GUIDELINES:
                - **Quality over quantity**: Better to send nothing than repeat yourself
                - **Focus on new content**: Reference new summaries primarily
                - **Be conversational**: This is SMS, keep it personal and friendly
                - **Add value**: Each message should provide unique insights or questions
                - **Respect their time**: Don't message if there's nothing meaningful to add

                DECISION FRAMEWORK:
                - If new learning is just browsing/casual research: Consider skipping
                - If new learning shows focused study on new topics: Likely send messages
                - If new learning builds on previous discussions: Send targeted follow-ups
                - If new learning is repetitive of recent conversations: Skip messaging

                Remember: You have the discretion to NOT send any messages if the new learning doesn't warrant it. It's better to stay silent than be repetitive or unhelpful.
                """

            try:
                agent_result = execute_cohere_agent(agent_prompt, user_phone)
                user_result['agent_execution'] = agent_result
                print(f"✅ [{thread_name}] Agent execution completed for {user_label}")
                
                sms_count = agent_result.get('sms_count', 0)
                if sms_count > 0:
                    print(f"📱 [{thread_name}] SMS messages sent: {sms_count}")
                else:
                    print(f"🤐 [{thread_name}] Agent decided not to send SMS (content may be repetitive or not substantial enough)")
                
                # Mark unprocessed summaries as processed after successful agent execution
                if agent_result.get('success', False):
                    try:
                        unprocessed_ids = [s['id'] for s in unprocessed_summaries]
                        if unprocessed_ids:
                            update_response = supabase.table('summaries') \
                                .update({'processed': True}) \
                                .in_('id', unprocessed_ids) \
                                .execute()
                            
                            if update_response.data:
                                print(f"✅ [{thread_name}] Marked {len(unprocessed_ids)} summaries as processed for {user_label}")
                                user_result['summaries_marked_processed'] = len(unprocessed_ids)
                            else:
                                print(f"⚠️ [{thread_name}] Failed to mark summaries as processed for {user_label}")
                                user_result['summaries_marked_processed'] = 0
                    except Exception as mark_error:
                        print(f"❌ [{thread_name}] Error marking summaries as processed for {user_label}: {str(mark_error)}")
                        user_result['summaries_marked_processed'] = 0
                
            except Exception as agent_error:
                print(f"❌ [{thread_name}] Agent execution failed for {user_label}: {str(agent_error)}")
                user_result['agent_execution'] = {
                    'success': False,
                    'error': str(agent_error)
                }
        else:
            print(f"⏩ [{thread_name}] No unprocessed summaries found for {user_label}, skipping agent execution")
        
        results_dict[index] = user_result
        
    except Exception as e:
        print(f'💥 [{thread_name}] Error processing summaries for {user_label}: {str(e)}')
        results_dict[index] = {
            'user_id': user_id,
            'user_email': user_email,
            'user_phone': user_phone,
            'success': False,
            'error': str(e),
            'summaries_count': 0,
            'unprocessed_count': 0,
            'agent_execution': None
        }


def process_user_summaries():
    """
    Iterate through all users and fetch their summaries from the past 24 hours with threading
    
    Returns:
        dict: Contains status and processing results
    """
    print("🔍 Starting multi-threaded user summaries processing...")
    
    try:
        # Calculate 24 hours ago timestamp
        from datetime import datetime, timedelta
        twenty_four_hours_ago = (datetime.now() - timedelta(hours=24)).isoformat()
        
        print(f"📅 Looking for summaries created after: {twenty_four_hours_ago}")
        
        # Fetch all users with phone numbers
        print("📋 Fetching all users...")
        users_response = supabase.table('users').select('id, email, phone_number').execute()
        
        if users_response.data is None:
            print('❌ Error fetching users:', users_response)
            return {'success': False, 'error': 'Error fetching users'}
            
        users = users_response.data
        print(f"✅ Found {len(users)} users to process")
        
        if not users:
            return {'success': True, 'message': 'No users found', 'results': []}
        
        # Create shared dictionary for results and threads
        results_dict = {}
        threads = []
        max_threads = min(len(users), 3)  # Limit to 3 concurrent threads to avoid overwhelming APIs
        
        print(f"🧵 Creating up to {max_threads} threads for processing...")
        
        # Process users in batches to manage thread count
        for i, user in enumerate(users):
            # Wait for some threads to complete if we hit the limit
            if len(threads) >= max_threads:
                # Wait for some threads to complete before starting new ones
                for thread in threads[:max_threads//2]:
                    thread.join()
                threads = [t for t in threads if t.is_alive()]
            
            # Create and start thread for this user
            thread = threading.Thread(
                target=process_single_user_summaries,
                args=(user, twenty_four_hours_ago, results_dict, i),
                name=f"SummaryThread-{i+1}"
            )
            thread.start()
            threads.append(thread)
            
            # Small delay to stagger API calls
            time.sleep(0.5)
        
        # Wait for all threads to complete
        print(f"⏳ Waiting for all {len(threads)} threads to complete...")
        for thread in threads:
            thread.join()
        
        # Convert results dict to list (preserving original order)
        results = [results_dict[i] for i in range(len(users)) if i in results_dict]
        
        # Summary statistics
        total_summaries = sum(r.get('summaries_count', 0) for r in results)
        total_unprocessed = sum(r.get('unprocessed_count', 0) for r in results)
        successful_users = len([r for r in results if r.get('success', False)])
        successful_agent_executions = len([r for r in results if r.get('agent_execution', {}).get('success', False)])
        total_sms_sent = sum(r.get('agent_execution', {}).get('sms_count', 0) for r in results)
        total_summaries_marked_processed = sum(r.get('summaries_marked_processed', 0) for r in results)
        
        # Track smart messaging decisions
        users_with_unprocessed = len([r for r in results if r.get('unprocessed_count', 0) > 0])
        agent_decided_to_message = len([r for r in results if r.get('agent_execution', {}).get('sms_count', 0) > 0])
        agent_decided_to_skip = successful_agent_executions - agent_decided_to_message
        total_message_history_entries = sum(r.get('message_history_count', 0) for r in results)
        
        print(f"🎉 Multi-threaded processing complete!")
        print(f"📈 Total summaries found: {total_summaries}")
        print(f"🔄 Total unprocessed summaries: {total_unprocessed}")
        print(f"✅ Successful users: {successful_users}/{len(users)}")
        print(f"🤖 Successful agent executions: {successful_agent_executions}")
        print(f"📱 Agent decided to send messages: {agent_decided_to_message}/{users_with_unprocessed} users with new content")
        print(f"🤐 Agent decided to skip messaging: {agent_decided_to_skip} (smart filtering)")
        print(f"📱 Total SMS messages sent: {total_sms_sent}")
        print(f"💬 Total conversation history entries: {total_message_history_entries}")
        print(f"✅ Summaries marked as processed: {total_summaries_marked_processed}")
        
        return {
            'success': True,
            'total_users': len(users),
            'successful_users': successful_users,
            'total_summaries': total_summaries,
            'total_unprocessed': total_unprocessed,
            'users_with_unprocessed': users_with_unprocessed,
            'successful_agent_executions': successful_agent_executions,
            'agent_decided_to_message': agent_decided_to_message,
            'agent_decided_to_skip': agent_decided_to_skip,
            'total_sms_sent': total_sms_sent,
            'total_message_history_entries': total_message_history_entries,
            'summaries_marked_processed': total_summaries_marked_processed,
            'time_range': f"Past 24 hours (since {twenty_four_hours_ago})",
            'results': results
        }
        
    except Exception as error:
        print('💥 Fatal error in process_user_summaries:', error)
        return {
            'success': False,
            'error': f"Fatal error: {error}"
        }

# =============================================================== #
# Cohere Tool Use
# =============================================================== #

def execute_cohere_agent(user_prompt: str, to_number: str):
    """
    Execute Cohere agent with multi-tool capabilities based on user instruction
    
    Args:
        user_prompt (str): The instruction/prompt for the agent to execute
        
    Returns:
        dict: Contains execution status, results, and metadata
    """
    
    # Define tools for Cohere
    tools = [
        {
            "type": "function",
            "function": {
                "name": "send_sms",
                "description": "Send SMS messages to the user's phone. Use this to deliver summaries, key insights, or important findings directly to the user's mobile device. Perfect for delivering learning summaries or key takeaways.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message_body": {
                            "type": "string",
                            "description": "The text content of the SMS message to be sent to the user.",
                        }
                    },
                    "required": ["message_body"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_youtube_transcript",
                "description": "Extract transcript text from a YouTube video URL. Returns the full transcript as text.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "youtube_url": {
                            "type": "string",
                            "description": "The YouTube video URL to extract transcript from",
                        }
                    },
                    "required": ["youtube_url"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "scrape_website_info",
                "description": "Scrape website content and return the body text. Returns the website content as clean text.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The website URL to scrape content from",
                        }
                    },
                    "required": ["url"],
                },
            },
        }
    ]
    
    try:
        print(f"🚀 Starting Cohere agent with user prompt...")
        print(f"📝 User prompt: {user_prompt[:100]}{'...' if len(user_prompt) > 100 else ''}")
        
        # Initialize the conversation
        messages = [
            {
                'role': 'user',
                'content': user_prompt
            }
        ]
        
        # Track conversation state and token usage
        max_iterations = 5  # Allow multiple iterations for multi-step tool use
        iteration = 0
        total_input_tokens = 0
        total_output_tokens = 0
        tools_used = []
        sms_messages_sent = []
        
        while iteration < max_iterations:
            iteration += 1
            print(f"🔄 Iteration {iteration}...")
            
            # Call Cohere with tools
            response = co.chat(
                model='command-a-03-2025',
                messages=messages,
                tools=tools,
                temperature=0.3
            )
            
            print(f"📝 Response finish reason: {response.finish_reason}")
            
            # Track token usage
            if hasattr(response, 'usage') and response.usage:
                input_tokens = getattr(response.usage, 'input_tokens', 0)
                output_tokens = getattr(response.usage, 'output_tokens', 0)
                total_input_tokens += input_tokens
                total_output_tokens += output_tokens
                print(f"🪙 Token usage this call - Input: {input_tokens}, Output: {output_tokens}")
                print(f"🪙 Total token usage so far - Input: {total_input_tokens}, Output: {total_output_tokens}")
            
            # Add assistant's response to messages
            assistant_message = {
                'role': 'assistant',
                'content': response.message.content
            }
            
            # Include tool calls in the assistant message if they exist
            if response.message.tool_calls:
                assistant_message['tool_calls'] = response.message.tool_calls
                
            messages.append(assistant_message)
            
            # Handle tool calls
            if response.message.tool_calls:
                print(f"🛠️  Found {len(response.message.tool_calls)} tool call(s)")
                
                for tool_call in response.message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = tool_call.function.arguments
                    
                    print(f"🔧 Executing tool: {tool_name}")
                    print(f"📋 Arguments: {tool_args}")
                    
                    try:
                        # Parse arguments if they're a string
                        if isinstance(tool_args, str):
                            import json
                            tool_args = json.loads(tool_args)
                        
                        # Execute the appropriate tool function
                        if tool_name == "send_sms":
                            result = send_sms(tool_args.get("message_body", ""), to_number=to_number)
                            if result.get('success'):
                                sms_messages_sent.append({
                                    'message_body': tool_args.get("message_body", ""),
                                    'message_sid': result.get('message_sid'),
                                    'status': result.get('status')
                                })
                            tools_used.append(tool_name)
                            
                        elif tool_name == "get_youtube_transcript":
                            result = get_youtube_transcript(tool_args.get("youtube_url", ""))
                            tools_used.append(tool_name)
                            
                        elif tool_name == "scrape_website_info":
                            result = scrape_website_info(tool_args.get("url", ""))
                            tools_used.append(tool_name)
                            
                        else:
                            result = f"Unknown tool: {tool_name}"
                        
                        print(f"✅ Tool result preview: {str(result)[:200]}...")
                        
                        # Add tool results to conversation
                        messages.append({
                            'role': 'tool',
                            'tool_call_id': tool_call.id,
                            'content': str(result)
                        })
                        
                    except Exception as e:
                        print(f"❌ Error executing {tool_name}: {str(e)}")
                        messages.append({
                            'role': 'tool',
                            'tool_call_id': tool_call.id,
                            'content': f"Error executing {tool_name}: {str(e)}"
                        })
                
            else:
                # No more tool calls, conversation is complete
                print("🎉 Agent execution complete!")
                
                # Extract final response text
                final_response = ""
                if hasattr(response.message, 'content') and response.message.content:
                    if isinstance(response.message.content, list):
                        for item in response.message.content:
                            if hasattr(item, 'text'):
                                final_response += item.text
                    else:
                        final_response = str(response.message.content)
                
                return {
                    'success': True,
                    'iterations': iteration,
                    'final_response': final_response,
                    'conversation_length': len(messages),
                    'tools_used': list(set(tools_used)),
                    'sms_messages_sent': sms_messages_sent,
                    'sms_count': len(sms_messages_sent),
                    'token_usage': {
                        'input_tokens': total_input_tokens,
                        'output_tokens': total_output_tokens,
                        'total_tokens': total_input_tokens + total_output_tokens
                    }
                }
        
        return {
            'success': False,
            'error': 'Max iterations reached',
            'iterations': iteration,
            'conversation_length': len(messages),
            'tools_used': list(set(tools_used)),
            'sms_messages_sent': sms_messages_sent,
            'sms_count': len(sms_messages_sent),
            'token_usage': {
                'input_tokens': total_input_tokens,
                'output_tokens': total_output_tokens,
                'total_tokens': total_input_tokens + total_output_tokens
            }
        }
        
    except Exception as e:
        print(f"💥 Error in execute_cohere_agent: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

# =============================================================== #
# Twilio API Listen
# =============================================================== #

@app.route('/sms', methods=['GET', 'POST'])
def sms_reply():
    """Handle incoming SMS messages from Twilio webhook"""
    try:
        # Get the message data from Twilio's webhook request
        incoming_msg = request.values.get('Body', '').strip()
        sender_number = request.values.get('From', '')
        twilio_number = request.values.get('To', '')
        message_sid = request.values.get('MessageSid', '')
        
        print(f"📱 Received SMS from {sender_number} to {twilio_number}")
        print(f"📝 Message: {incoming_msg}")
        print(f"🆔 Message SID: {message_sid}")
        
        # Fetch message history with this caller
        message_history = get_message_history(sender_number, limit=50)
        
        if message_history['success']:
            total_msgs = message_history['total_messages']
            inbound_count = message_history['inbound_messages']
            outbound_count = message_history['outbound_messages']
            
            print(f"📚 Message History Summary:")
            print(f"   Total messages with {sender_number}: {total_msgs}")
            print(f"   Inbound: {inbound_count}, Outbound: {outbound_count}")
            
            # Show last few messages for context
            if message_history['messages']:
                print(f"📜 Recent conversation history:")
                for i, msg in enumerate(message_history['messages'][:5]):  # Show last 5 messages
                    direction_emoji = "📤" if msg['direction'] == 'inbound' else "📥"
                    print(f"   {i+1}. {direction_emoji} {msg['from']} → {msg['to']}: {msg['body'][:50]}{'...' if len(msg['body']) > 50 else ''}")
        
        # CHECK ONBOARDING GATES FIRST
        print(f"🚪 Checking onboarding gates...")
        gate_status = check_onboarding_gates(sender_number)
        
        if gate_status['onboarding_complete']:
            print(f"✅ Onboarding complete - proceeding with normal flow")
            
            # Existing flow: Fetch user summaries and create intelligent context
            user_lookup = get_user_by_phone_number(sender_number)
            
            if user_lookup['success'] and user_lookup['user_found']:
                # Calculate timestamps for past 36 hours
                from datetime import datetime, timedelta, timezone
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(hours=36)
                
                start_timestamp = start_time.isoformat()
                end_timestamp = end_time.isoformat()
                
                user_id = user_lookup['user_info']['id']
                user_summaries = get_user_summaries_between_dates(user_id, start_timestamp, end_timestamp)
                
                if user_summaries['success']:
                    summaries_count = user_summaries['summaries_count']
                    user_info = user_lookup['user_info']
                    
                    print(f"🧠 User Learning Context:")
                    print(f"   User: {user_info.get('email', 'No email')} ({sender_number})")
                    print(f"   Learning summaries: {summaries_count} in past 36 hours")
                    
                    # Show recent learning topics
                    if user_summaries['summaries']:
                        print(f"📝 Recent learning summaries:")
                        for i, summary in enumerate(user_summaries['summaries'][:3]):  # Show last 3 summaries
                            summary_preview = summary['summary_text'][:100] + '...' if len(summary['summary_text']) > 100 else summary['summary_text']
                            print(f"   {i+1}. {summary['prompt_generated_at'][:10]}: {summary_preview}")
                else:
                    print(f"ℹ️  No learning summaries available for user {user_lookup['user_info']['email']}")
                    user_summaries = None
            else:
                print(f"ℹ️  No user found for phone number {sender_number}")
                user_summaries = None

            # Create intelligent prompt for Cohere agent
            context_prompt = create_intelligent_response_prompt(
                incoming_message=incoming_msg,
                sender_number=sender_number,
                message_history=message_history if message_history['success'] else None,
                user_summaries=user_summaries if user_summaries and user_summaries['success'] else None
            )
            
            # Execute intelligent agent with context
            execute_cohere_agent(context_prompt, to_number=sender_number)
            
        else:
            print(f"🚪 Onboarding required - handling gate: {gate_status['next_gate']}")
            # Handle onboarding flow
            handle_onboarding_flow(incoming_msg, sender_number, gate_status)

        # Create a TwiML response
        resp = MessagingResponse()
        
        print(f"✅ Sending TwiML response back to Twilio")
        
        # Return TwiML response
        return str(resp)
        
    except Exception as e:
        print(f"💥 Error handling SMS webhook: {e}")
        # Return empty TwiML response in case of error
        return str(MessagingResponse()), 500


@app.route('/')
def home():
    return jsonify({
        'message': 'Flask + Cohere Agent API',
        'status': 'success',
        'endpoints': {
            'cohere_agent': '/api/cohere-agent (POST) - Execute agent with custom prompt',
            'process_summaries': '/api/process-summaries (POST) - Process user summaries with agent',
            'analyze_users': '/api/analyze-users (POST) - Analyze all users with Cohere',
            'health': '/health (GET) - Health check',
            'sms_webhook': '/sms (POST) - Twilio SMS webhook'
        },
        'tools_available': ['send_sms', 'get_youtube_transcript', 'scrape_website_info'],
        'usage': {
            'cohere_agent': {
                'method': 'POST',
                'payload': {
                    'prompt': 'Your instruction for the agent...',
                    'to_number': '+15145850357 (optional)'
                },
                'description': 'Send a prompt/instruction and the agent will intelligently use available tools to fulfill your request'
            },
            'process_summaries': {
                'method': 'POST',
                'description': 'Process all user summaries and send clarification questions via SMS'
            },
            'analyze_users': {
                'method': 'POST',
                'description': 'Analyze all users activities with Cohere and generate summaries'
            }
        }
    })

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'cohere': 'connected' if COHERE_API_KEY else 'missing_key',
            'supabase': 'connected' if SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY else 'missing_config',
            'twilio': 'connected' if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN else 'missing_config'
        }
    })


@app.route('/api/process-summaries', methods=['POST'])
def api_process_summaries():
    """API endpoint to process user summaries with Cohere agent"""
    try:
        result = process_user_summaries()
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Test function for development
def test_cohere_agent():
    """Test the agent with a sample prompt"""
    test_prompt = """
    I'm preparing for an important technical interview about web development and React. I need your help to gather comprehensive information and send me key insights via SMS.

    Here's what I need you to do:

    1. First, get the transcript from this React tutorial video: https://www.youtube.com/watch?v=SqcY0GlETPk (React in 100 Seconds by Fireship)

    2. Then, scrape the official React documentation homepage: https://react.dev

    3. After analyzing both sources, please send me multiple SMS messages with:
       - A summary of the key React concepts from the video (first SMS)
       - The most important React features mentioned on the React.dev homepage (second SMS)  
       - 3-5 potential interview questions I should prepare for based on both sources (third SMS)
       - Any additional tips or insights you think would be valuable for my interview prep (fourth SMS if needed)

    Feel free to send as many SMS messages as you think would be helpful - I want to be thoroughly prepared! Make each SMS focused and actionable.
    """
    
    return execute_cohere_agent(test_prompt, to_number="+15145850357")

def test_process_summaries():
    """Test the new process_user_summaries function with agent integration"""
    print("🧪 Testing process_user_summaries with agent integration...")
    result = process_user_summaries()
    print("🎯 Test result:", result)
    return result

def test_analyze_users():
    """Test the analyze_all_users function"""
    print("🧪 Testing analyze_all_users function...")
    result = analyze_all_users()
    print("🎯 Test result:", result)
    return result


if __name__ == '__main__':
    # Choose what to test
    test_mode = "server"  # Options: "agent", "summaries", "analyze", "intelligent", "server"
    
    if test_mode == "agent":
        print("🧪 Testing Cohere agent...")
        result = test_cohere_agent()
        print("🎯 Test result:", result)
    elif test_mode == "summaries":
        test_process_summaries()
    elif test_mode == "analyze":
        test_analyze_users()
    elif test_mode == "server":
        app.run(debug=True, host='0.0.0.0', port=3067)
    else:
        print("Invalid test mode. Choose 'agent', 'summaries', 'analyze', 'intelligent', or 'server'")

# Run the summaries test by default
# process_user_summaries()