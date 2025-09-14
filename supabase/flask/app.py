
from flask import Flask, jsonify, request
from supabase import create_client, Client as SupabaseClient
import threading
import time
import cohere
import os
from twilio.rest import Client as TwilioClient
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
import re

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

def send_sms(message_body: str): # , to_number: str
    """
    Send SMS using Twilio and return success status
    
    Returns:
        dict: Contains 'success' (bool), 'message_sid' (str), 'status' (str), and 'error' (str) if failed
    """
    to_number="+15145850357"

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

# =============================================================== #
# Cohere Summaries Parsing
# =============================================================== #

def process_user_summaries():
    """
    Iterate through all users and fetch their summaries from the past 24 hours
    
    Returns:
        dict: Contains status and processing results
    """
    print("🔍 Starting user summaries processing...")
    
    try:
        # Calculate 24 hours ago timestamp
        from datetime import datetime, timedelta
        twenty_four_hours_ago = (datetime.now() - timedelta(hours=24)).isoformat()
        
        print(f"📅 Looking for summaries created after: {twenty_four_hours_ago}")
        
        # Fetch all users
        print("📋 Fetching all users...")
        users_response = supabase.table('users').select('id, email').execute()
        
        if users_response.data is None:
            print('❌ Error fetching users:', users_response)
            return {'success': False, 'error': 'Error fetching users'}
            
        users = users_response.data
        print(f"✅ Found {len(users)} users to process")
        
        if not users:
            return {'success': True, 'message': 'No users found', 'results': []}
        
        results = []
        
        # Process each user
        for user in users:
            user_id = user['id']
            user_email = user.get('email', 'No email')
            user_label = user_email if user_email != 'No email' else user_id[:8] + "..."
            
            print(f"🔍 Processing summaries for user: {user_label}")
            
            try:
                # Fetch summaries for this user from the past 24 hours
                summaries_response = supabase.table('summaries') \
                    .select('id, user_id, summary, prompt_generated_at, cohere_finish_reason, cohere_usage, source_activity_ids') \
                    .eq('user_id', user_id) \
                    .gte('prompt_generated_at', twenty_four_hours_ago) \
                    .order('prompt_generated_at', desc=True) \
                    .execute()
                
                if summaries_response.data is None:
                    print(f'❌ Error fetching summaries for {user_label}')
                    results.append({
                        'user_id': user_id,
                        'user_email': user_email,
                        'success': False,
                        'error': 'Error fetching summaries',
                        'summaries_count': 0
                    })
                    continue
                
                summaries = summaries_response.data
                summaries_count = len(summaries)
                
                print(f"📊 Found {summaries_count} summaries for {user_label} in the past 24 hours")
                
                # Process each summary for this user
                user_result = {
                    'user_id': user_id,
                    'user_email': user_email,
                    'success': True,
                    'summaries_count': summaries_count,
                    'summaries': []
                }
                
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
                    
                    processed_summary = {
                        'id': summary['id'],
                        'prompt_generated_at': summary.get('prompt_generated_at'),
                        'summary_text': summary_text,
                        'cohere_finish_reason': summary.get('cohere_finish_reason'),
                        'cohere_usage': summary.get('cohere_usage'),
                        'source_activity_count': len(summary.get('source_activity_ids', []))
                    }
                    
                    user_result['summaries'].append(processed_summary)
                
                results.append(user_result)
                
            except Exception as e:
                print(f'💥 Error processing summaries for {user_label}: {str(e)}')
                results.append({
                    'user_id': user_id,
                    'user_email': user_email,
                    'success': False,
                    'error': str(e),
                    'summaries_count': 0
                })
        
        # Summary statistics
        total_summaries = sum(r.get('summaries_count', 0) for r in results)
        successful_users = len([r for r in results if r.get('success', False)])
        
        print(f"🎉 Processing complete!")
        print(f"📈 Total summaries processed: {total_summaries}")
        print(f"✅ Successful users: {successful_users}/{len(users)}")
        
        return {
            'success': True,
            'total_users': len(users),
            'successful_users': successful_users,
            'total_summaries': total_summaries,
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

def cohere_action_testing(): 
    """
    Test function for Cohere actions with real tool use implementation using multi-step tools
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
                            "description": "The text content of the SMS message to be sent to the user. ",
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
    
    # Test prompt that requires multi-step tool use - inspired by the documentation examples
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
    
    try:
        print("🚀 Starting Cohere multi-tool testing...")
        
        # Initialize the conversation
        messages = [
            {
                'role': 'user',
                'content': test_prompt
            }
        ]
        
        # Track conversation state and token usage
        max_iterations = 5  # Allow multiple iterations for multi-step tool use
        iteration = 0
        total_input_tokens = 0
        total_output_tokens = 0
        
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
                
                tool_results = []
                
                for tool_call in response.message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = tool_call.function.arguments
                    
                    print(f"🔧 Executing tool: {tool_name}")
                    print(f"📋 Arguments: {tool_args}")
                    print(f"📋 Arguments type: {type(tool_args)}")
                    
                    try:
                        # Parse arguments if they're a string
                        if isinstance(tool_args, str):
                            import json
                            tool_args = json.loads(tool_args)
                        
                        # Execute the appropriate tool function
                        if tool_name == "send_sms":
                            result = send_sms(tool_args.get("message_body", ""))
                            
                        elif tool_name == "get_youtube_transcript":
                            result = get_youtube_transcript(tool_args.get("youtube_url", ""))
                            
                        elif tool_name == "scrape_website_info":
                            result = scrape_website_info(tool_args.get("url", ""))
                            
                        else:
                            result = f"Unknown tool: {tool_name}"
                        
                        print(f"✅ Tool result preview: {str(result)[:200]}...")
                        
                        # Format tool result
                        tool_results.append({
                            'call': tool_call,
                            'outputs': [str(result)]
                        })
                        
                    except Exception as e:
                        print(f"❌ Error executing {tool_name}: {str(e)}")
                        tool_results.append({
                            'call': tool_call,
                            'outputs': [f"Error executing {tool_name}: {str(e)}"]
                        })
                
                # Add tool results to conversation - use the correct format for Cohere v2
                for tool_result in tool_results:
                    messages.append({
                        'role': 'tool',
                        'tool_call_id': tool_result['call'].id,
                        'content': tool_result['outputs'][0]
                    })
                
            else:
                # No more tool calls, conversation is complete
                print("🎉 Multi-tool conversation complete!")
                
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
                    'token_usage': {
                        'input_tokens': total_input_tokens,
                        'output_tokens': total_output_tokens,
                        'total_tokens': total_input_tokens + total_output_tokens
                    },
                    'tools_used': [
                        tool_call.function.name 
                        for msg in messages 
                        if msg.get('role') == 'assistant' 
                        for tool_call in (getattr(getattr(co.chat(model='command-r-plus', messages=[msg]), 'message', None), 'tool_calls', None) or [])
                    ]
                }
        
        return {
            'success': False,
            'error': 'Max iterations reached',
            'iterations': iteration,
            'conversation_length': len(messages),
            'token_usage': {
                'input_tokens': total_input_tokens,
                'output_tokens': total_output_tokens,
                'total_tokens': total_input_tokens + total_output_tokens
            }
        }
        
    except Exception as e:
        print(f"💥 Error in cohere_action_testing: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


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


# analyze_all_users()
# print(scrape_website_info(url="https://example.com"))
print(cohere_action_testing())