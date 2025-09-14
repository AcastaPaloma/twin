#!/usr/bin/env python3
"""
Twilio SMS Message History Deletion Utility

This script provides functionality to delete all SMS message history 
with a specific phone number from Twilio.

Usage:
    python reset_twilio_number.py

Dependencies:
    - twilio
    - python-dotenv
"""

import os
from twilio.rest import Client as TwilioClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

# Initialize Twilio client
twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def delete_message_history_with_number(phone_number: str, dry_run: bool = True):
    """
    Delete all SMS message history with a specific phone number from Twilio
    
    Args:
        phone_number (str): The phone number to delete message history for
        dry_run (bool): If True, only shows what would be deleted without actually deleting
        
    Returns:
        dict: Contains deletion status, counts, and results
    """
    
    print(f"🔍 Searching for messages with phone number: {phone_number}")
    print(f"{'🧪 DRY RUN MODE - No messages will be deleted' if dry_run else '🔥 DELETION MODE - Messages will be permanently deleted'}")
    print("-" * 80)
    
    try:
        # Get messages where this number was the sender (FROM this number TO our Twilio number)
        print("📥 Fetching inbound messages (from target number to our Twilio number)...")
        messages_from_target = list(twilio_client.messages.list(
            from_=phone_number,
            limit=1000  # Adjust limit as needed
        ))
        
        # Get messages where this number was the recipient (FROM our Twilio number TO this number)
        print("📤 Fetching outbound messages (from our Twilio number to target number)...")
        messages_to_target = list(twilio_client.messages.list(
            to=phone_number,
            limit=1000  # Adjust limit as needed
        ))
        
        # Combine all messages
        all_messages = messages_from_target + messages_to_target
        
        # Remove duplicates by SID (in case there are any)
        unique_messages = {}
        for msg in all_messages:
            unique_messages[msg.sid] = msg
        
        messages_to_delete = list(unique_messages.values())
        
        print(f"📊 Found {len(messages_to_delete)} messages to process:")
        print(f"   - Inbound messages (from {phone_number}): {len(messages_from_target)}")
        print(f"   - Outbound messages (to {phone_number}): {len(messages_to_target)}")
        print(f"   - Unique messages total: {len(messages_to_delete)}")
        print("-" * 80)
        
        if not messages_to_delete:
            print("✅ No messages found with this phone number.")
            return {
                'success': True,
                'phone_number': phone_number,
                'total_messages_found': 0,
                'messages_deleted': 0,
                'dry_run': dry_run,
                'deleted_message_sids': [],
                'failed_deletions': []
            }
        
        # Display message details
        print("📋 Message Details:")
        for i, msg in enumerate(messages_to_delete[:10]):  # Show first 10 for preview
            direction = "📥 IN " if msg.from_ == phone_number else "📤 OUT"
            body_preview = (msg.body[:100] + "...") if len(msg.body) > 100 else msg.body
            print(f"   {i+1}. {direction} | {msg.date_created} | SID: {msg.sid[:10]}... | '{body_preview}'")
        
        if len(messages_to_delete) > 10:
            print(f"   ... and {len(messages_to_delete) - 10} more messages")
        
        print("-" * 80)
        
        if dry_run:
            print("🧪 DRY RUN: No messages were deleted. Set dry_run=False to perform actual deletion.")
            return {
                'success': True,
                'phone_number': phone_number,
                'total_messages_found': len(messages_to_delete),
                'messages_deleted': 0,
                'dry_run': True,
                'deleted_message_sids': [],
                'failed_deletions': []
            }
        
        # Perform actual deletion
        print("🔥 Starting message deletion...")
        deleted_sids = []
        failed_deletions = []
        
        for i, msg in enumerate(messages_to_delete):
            try:
                print(f"   Deleting message {i+1}/{len(messages_to_delete)}: {msg.sid[:10]}...")
                msg.delete()
                deleted_sids.append(msg.sid)
                print(f"   ✅ Successfully deleted message {msg.sid[:10]}")
                
            except Exception as delete_error:
                print(f"   ❌ Failed to delete message {msg.sid[:10]}: {str(delete_error)}")
                failed_deletions.append({
                    'sid': msg.sid,
                    'error': str(delete_error),
                    'body_preview': (msg.body[:100] + "...") if len(msg.body) > 100 else msg.body
                })
        
        print("-" * 80)
        print(f"🎯 Deletion Summary:")
        print(f"   - Total messages found: {len(messages_to_delete)}")
        print(f"   - Successfully deleted: {len(deleted_sids)}")
        print(f"   - Failed deletions: {len(failed_deletions)}")
        
        if failed_deletions:
            print("\n❌ Failed Deletions:")
            for failure in failed_deletions:
                print(f"   - SID {failure['sid'][:10]}...: {failure['error']}")
        
        return {
            'success': len(failed_deletions) == 0,
            'phone_number': phone_number,
            'total_messages_found': len(messages_to_delete),
            'messages_deleted': len(deleted_sids),
            'dry_run': False,
            'deleted_message_sids': deleted_sids,
            'failed_deletions': failed_deletions
        }
        
    except Exception as e:
        print(f"💥 Error processing messages for {phone_number}: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'phone_number': phone_number,
            'total_messages_found': 0,
            'messages_deleted': 0,
            'dry_run': dry_run,
            'deleted_message_sids': [],
            'failed_deletions': []
        }


def get_message_stats_for_number(phone_number: str):
    """
    Get statistics about message history with a specific phone number
    
    Args:
        phone_number (str): The phone number to get stats for
        
    Returns:
        dict: Contains message statistics and summary
    """
    try:
        print(f"📊 Getting message statistics for: {phone_number}")
        
        # Get messages from target number to our Twilio number
        messages_from_target = list(twilio_client.messages.list(
            from_=phone_number,
            limit=1000
        ))
        
        # Get messages from our Twilio number to target number
        messages_to_target = list(twilio_client.messages.list(
            to=phone_number,
            limit=1000
        ))
        
        # Combine and deduplicate
        all_messages = messages_from_target + messages_to_target
        unique_messages = {}
        for msg in all_messages:
            unique_messages[msg.sid] = msg
        
        messages = list(unique_messages.values())
        
        # Sort by date (most recent first)
        messages.sort(key=lambda x: x.date_created, reverse=True)
        
        # Calculate stats
        inbound_count = len(messages_from_target)
        outbound_count = len(messages_to_target)
        total_count = len(messages)
        
        # Date range
        first_message_date = messages[-1].date_created if messages else None
        last_message_date = messages[0].date_created if messages else None
        
        print(f"📈 Message Statistics for {phone_number}:")
        print(f"   - Total unique messages: {total_count}")
        print(f"   - Inbound messages: {inbound_count}")
        print(f"   - Outbound messages: {outbound_count}")
        if first_message_date and last_message_date:
            print(f"   - First message: {first_message_date}")
            print(f"   - Last message: {last_message_date}")
        
        return {
            'success': True,
            'phone_number': phone_number,
            'total_messages': total_count,
            'inbound_messages': inbound_count,
            'outbound_messages': outbound_count,
            'first_message_date': str(first_message_date) if first_message_date else None,
            'last_message_date': str(last_message_date) if last_message_date else None,
            'messages_preview': [
                {
                    'sid': msg.sid,
                    'direction': 'inbound' if msg.from_ == phone_number else 'outbound',
                    'date_created': str(msg.date_created),
                    'body_preview': (msg.body[:100] + "...") if len(msg.body) > 100 else msg.body,
                    'status': msg.status
                }
                for msg in messages[:5]  # First 5 messages as preview
            ]
        }
        
    except Exception as e:
        print(f"💥 Error getting stats for {phone_number}: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'phone_number': phone_number
        }


def interactive_deletion():
    """
    Interactive function to safely delete message history with a phone number
    """
    print("🗑️  Twilio Message History Deletion Tool")
    print("=" * 80)
    
    # Get phone number from user
    phone_number = input("Enter the phone number to delete message history for (e.g., +15551234567): ").strip()
    
    if not phone_number:
        print("❌ No phone number provided. Exiting.")
        return
    
    # Ensure phone number has proper format
    if not phone_number.startswith('+'):
        print("⚠️  Adding '+' prefix to phone number...")
        phone_number = '+' + phone_number.lstrip('+')
    
    print(f"\n📱 Target phone number: {phone_number}")
    
    # First, show statistics
    print("\n" + "=" * 80)
    stats = get_message_stats_for_number(phone_number)
    
    if not stats['success']:
        print(f"❌ Error getting message stats: {stats['error']}")
        return
    
    if stats['total_messages'] == 0:
        print("✅ No messages found with this phone number. Nothing to delete.")
        return
    
    # Show preview messages
    if stats['messages_preview']:
        print(f"\n📋 Recent Messages Preview:")
        for msg in stats['messages_preview']:
            direction_emoji = "📥" if msg['direction'] == 'inbound' else "📤"
            print(f"   {direction_emoji} {msg['date_created']} | {msg['status']} | '{msg['body_preview']}'")
    
    # Dry run first
    print("\n" + "=" * 80)
    print("🧪 Running DRY RUN to show what would be deleted...")
    dry_run_result = delete_message_history_with_number(phone_number, dry_run=True)
    
    if not dry_run_result['success']:
        print(f"❌ Error during dry run: {dry_run_result['error']}")
        return
    
    # Confirm deletion
    print("\n" + "=" * 80)
    print("⚠️  WARNING: This will PERMANENTLY DELETE all message history with this number!")
    print(f"📊 Total messages to delete: {dry_run_result['total_messages_found']}")
    
    confirm = input("\nAre you sure you want to proceed with deletion? Type 'DELETE' to confirm: ").strip()
    
    if confirm != 'DELETE':
        print("🛡️  Deletion cancelled. Messages are safe.")
        return
    
    # Perform actual deletion
    print("\n" + "=" * 80)
    print("🔥 Proceeding with ACTUAL DELETION...")
    
    result = delete_message_history_with_number(phone_number, dry_run=False)
    
    if result['success']:
        print(f"\n✅ Successfully deleted {result['messages_deleted']} messages!")
    else:
        print(f"\n❌ Deletion completed with errors. Check the output above for details.")
    
    return result


def main():
    """
    Main function to run the script
    """
    print("🚀 Twilio Message History Deletion Utility")
    print("=" * 80)
    
    # Check if environment variables are set
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        print("❌ Missing required environment variables:")
        print("   - TWILIO_ACCOUNT_SID")
        print("   - TWILIO_AUTH_TOKEN") 
        print("   - TWILIO_PHONE_NUMBER")
        print("\nPlease set these in your .env file and try again.")
        return
    
    print(f"📱 Using Twilio phone number: {TWILIO_PHONE_NUMBER}")
    print(f"🔑 Account SID: {TWILIO_ACCOUNT_SID[:10]}...")
    
    # Run interactive deletion
    interactive_deletion()


if __name__ == '__main__':
    # ============================================================================
    # SIMPLE USAGE: Set the phone number here and run the script
    # ============================================================================
    
    # SET YOUR TARGET PHONE NUMBER HERE
    target_phone_number = "+15145850357"  # Replace with the actual phone number
    
    # Choose operation mode:
    # - dry_run=True: Shows what would be deleted without actually deleting
    # - dry_run=False: Actually deletes the messages (PERMANENT!)
    
    print("🚀 Starting Twilio Message Deletion Process")
    print("=" * 80)
    
    # Check if environment variables are set
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        print("❌ Missing required environment variables:")
        print("   - TWILIO_ACCOUNT_SID")
        print("   - TWILIO_AUTH_TOKEN") 
        print("   - TWILIO_PHONE_NUMBER")
        print("\nPlease set these in your .env file and try again.")
        exit(1)
    
    print(f"📱 Target phone number: {target_phone_number}")
    print(f"📱 Using Twilio phone number: {TWILIO_PHONE_NUMBER}")
    print(f"🔑 Account SID: {TWILIO_ACCOUNT_SID[:10]}...")
    
    # Step 1: Get statistics first
    print("\n" + "=" * 80)
    print("📊 Getting message statistics...")
    stats = get_message_stats_for_number(target_phone_number)
    
    if not stats['success']:
        print(f"❌ Error getting message stats: {stats.get('error', 'Unknown error')}")
        exit(1)
    
    if stats['total_messages'] == 0:
        print("✅ No messages found with this phone number. Nothing to delete.")
        exit(0)
    
    # Step 2: Show preview of recent messages
    if stats['messages_preview']:
        print(f"\n📋 Recent Messages Preview:")
        for msg in stats['messages_preview']:
            direction_emoji = "📥" if msg['direction'] == 'inbound' else "📤"
            print(f"   {direction_emoji} {msg['date_created']} | {msg['status']} | '{msg['body_preview']}'")
    
    # Step 3: Run dry run first to show what would be deleted
    print("\n" + "=" * 80)
    print("🧪 Running DRY RUN to show what would be deleted...")
    dry_run_result = delete_message_history_with_number(target_phone_number, dry_run=True)
    
    if not dry_run_result['success']:
        print(f"❌ Error during dry run: {dry_run_result.get('error', 'Unknown error')}")
        exit(1)
    
    # Step 4: Uncomment the lines below to perform ACTUAL DELETION
    # WARNING: This will permanently delete all messages!
    
    print("\n" + "=" * 80)
    print("⚠️  TO ACTUALLY DELETE MESSAGES:")
    print("   Uncomment the lines below in the code and run again")
    print("   This is a safety measure to prevent accidental deletion")
    print("=" * 80)
    
    # UNCOMMENT THESE LINES TO ACTUALLY DELETE MESSAGES:
    print("🔥 Proceeding with ACTUAL DELETION...")
    actual_result = delete_message_history_with_number(target_phone_number, dry_run=False)
    
    if actual_result['success']:
        print(f"\n✅ Successfully deleted {actual_result['messages_deleted']} messages!")
        print(f"📊 Final summary:")
        print(f"   - Messages found: {actual_result['total_messages_found']}")
        print(f"   - Messages deleted: {actual_result['messages_deleted']}")
        print(f"   - Failed deletions: {len(actual_result['failed_deletions'])}")
    else:
        print(f"\n❌ Deletion completed with errors:")
        print(f"   Error: {actual_result.get('error', 'Unknown error')}")
        if actual_result.get('failed_deletions'):
            print(f"   Failed deletions: {len(actual_result['failed_deletions'])}")
    
    print("\n🛡️  Script completed safely. No messages were deleted.")
