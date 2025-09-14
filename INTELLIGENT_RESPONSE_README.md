# Intelligent SMS Response System

## Overview
The intelligent response system creates contextual prompts for the Cohere agent to handle incoming SMS messages intelligently, taking into account:

1. **Current Message**: The user's incoming SMS text
2. **Conversation History**: Previous SMS exchanges with this user  
3. **Learning Context**: User's recent learning summaries and activities

## Key Features

### 1. Context-Aware Prompting
The `create_intelligent_response_prompt()` function builds comprehensive prompts that include:
- Current user message
- Recent conversation history (last 5 messages)
- Learning summaries from past 36 hours
- Strategic response guidelines

### 2. Intelligent Response Strategy
The agent is instructed to:
- Analyze the type of request (question, help request, check-in, etc.)
- Use tools appropriately (SMS, YouTube transcripts, web scraping)
- Maintain conversational continuity
- Connect new topics to existing learning patterns
- Ask follow-up questions to deepen understanding

### 3. Available Tools
- **send_sms**: Always used to respond to the user
- **get_youtube_transcript**: For video-related questions or learning
- **scrape_website_info**: For web-based resources and documentation

## API Endpoints

### Test Intelligent Response
```
POST /api/test-intelligent-response
```

**Body (all optional):**
```json
{
  "message": "Hey! Can you help me understand React hooks?",
  "sender_number": "+15145850357",
  "message_history": {...},  // Mock conversation data
  "user_summaries": {...}    // Mock learning summaries
}
```

### SMS Webhook (Twilio)
```
POST /sms
```
Automatically processes incoming SMS messages with full context.

## Example Usage

### 1. Testing via API
```bash
curl -X POST http://localhost:3067/api/test-intelligent-response \
  -H "Content-Type: application/json" \
  -d '{"message": "Can you explain useEffect hooks in React?"}'
```

### 2. Real SMS Integration
Send an SMS to your Twilio number. The system will:
1. Fetch conversation history
2. Retrieve user's learning summaries
3. Create contextual prompt
4. Execute Cohere agent with tools
5. Send intelligent response(s)

## Prompt Structure

The generated prompt includes:
- **User's current message**
- **Conversation context** (total messages, recent exchanges)
- **Learning context** (recent study topics, summaries)
- **Response strategy** (5-point framework)
- **Tool usage guidelines**
- **Conversation continuity instructions**

## Response Guidelines

The agent follows a 5-point strategy:
1. **Analyze the Request**: Understand the type and intent
2. **Use Tools Intelligently**: Leverage YouTube, web scraping as needed
3. **Response Guidelines**: Conversational, contextual, actionable
4. **Learning Focus**: Connect concepts, fill gaps, encourage exploration
5. **Conversation Flow**: Maintain continuity and relationship

## Testing

Run the intelligent response test:
```python
# In app.py, set test_mode = "intelligent"
python app.py
```

This creates a comprehensive learning assistant that adapts to each user's learning journey and conversation history!