
from flask import Flask, jsonify, request
from supabase import create_client, Client as SupabaseClient
import threading
import time
import cohere
import os
from twilio.rest import Client as TwilioClient
from dotenv import load_dotenv

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


def my_periodic_task():
    print("This runs every 3 seconds!")

def run_periodic_task():
    """Background function that runs the periodic task every 3 seconds"""
    while True:
        my_periodic_task()
        time.sleep(3)

# Start the periodic task in a background thread
task_thread = threading.Thread(target=run_periodic_task, daemon=True)
task_thread.start()

# =============================================================== #
# Twilio Sendgrid
# =============================================================== #

def send_sms(message_body: str, to_number: str):
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
# Cohere Analytics
# =============================================================== #

def process_user_with_cohere(user_id, user_email=None):
    """
    Process a single user's unprocessed activities with Cohere in a separate thread
    
    Args:
        user_id (str): The user ID to process
        user_email (str): Optional user email for logging
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
        
        # Optimized prompt for learning focus and key resource identification
        prompt = f"""Analyze this browsing activity to identify what the user is trying to learn and key resources for future AI analysis:

                {activity_text}

                Focus on:
                1. MAIN LEARNING TOPICS: What specific subjects/skills is the user studying?
                2. KEY URLs: List the most valuable URLs for future AI summarization:
                - YouTube videos (educational/tutorial content)
                - Documentation sites
                - Course platforms  
                - Technical articles/blogs
                - Learning tools/software

                Prioritize URLs that contain rich educational content that would benefit from AI summarization."""
        
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
                args=(user['id'], user.get('email')),
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
        process_user_with_cohere(test_user_id, "test@example.com")
        return f"✅ Single user test completed"
    except Exception as error:
        print('💥 Error in single user test:', error)
        return f"Error in single user test: {error}"


@app.route('/')
def home():
    return jsonify({
        'message': 'Flask + Twilio SMS API',
        'status': 'success',
        'endpoints': {
            'send_sms': '/api/send-sms (POST)',
            'test_sms': '/api/test-sms (POST)',
            'health': '/health (GET)'
        }
    })


@app.route('/api/test', methods=['GET', 'POST'])
def test_endpoint():
    if request.method == 'GET':
        return jsonify({
            'method': 'GET',
            'message': 'Test endpoint working!'
        })
    elif request.method == 'POST':
        data = request.get_json() if request.is_json else {}
        return jsonify({
            'method': 'POST',
            'message': 'Data received successfully',
            'received_data': data
        })

# if __name__ == '__main__':
#     app.run(debug=True, host='0.0.0.0', port=3067)


analyze_all_users()