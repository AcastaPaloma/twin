# Twin Activity Tracker

A Chrome extension that tracks your browsing activity and saves it to a Supabase database for analysis.

## Installation

1. Hop onto chrome://extensions
2. In the top right turn on Developer Mode
3. Click Load Unpacked and select the twin-raw folder
4. Create an account by Texting "Hey Twin" to +1 (587) 870-2558
5. Click the extension icon to open the popup
6. Enter your email to sign in
7. Toggle tracking on/off as needed


## Features

- **User Authentication**: Simple email-based login system
- **Activity Tracking**: Automatically tracks:
  - Page visits and navigation
  - Link clicks
  - Search queries (Google, YouTube, Bing)
  - Time spent on pages
- **Privacy Controls**: Easy toggle to enable/disable tracking
- **Supabase Integration**: All data stored securely in your Supabase database

## Database Schema

The extension uses three main tables:

### Users Table
- `id` (UUID): Primary key
- `email` (text): User's email address
- `is_active` (boolean): Whether user is active
- `created_at` (timestamp): Account creation time

### Activities Table
- `id` (UUID): Primary key
- `user_id` (UUID): Foreign key to users table
- `url` (text): The URL visited
- `title` (text): Page title
- `domain` (text): Auto-generated domain from URL
- `timestamp` (timestamp): When the activity occurred
- `processed` (boolean): Whether the activity has been processed

### Suggestions Table
- `id` (UUID): Primary key
- `user_id` (UUID): Foreign key to users table
- `content` (text): Chat/suggestion content
- `created_at` (timestamp): When created
- `cohere_prompt` (text): AI prompt content
- `sent_at` (timestamp): When sent
- `delivery_status` (text): Status of delivery

## Privacy

- Only tracks when you're logged in and tracking is enabled
- No tracking of chrome:// pages or extension pages
- All data stored in your own Supabase database
- Easy logout and tracking disable options

## Development

The extension includes:
- **Original API Reference Tool**: Type "api" in Chrome address bar
- **Activity Tracking**: New tracking functionality
- **Daily Tips**: Chrome extension development tips

## Configuration

Update Supabase credentials in:
- `sw-auth.js`
- `sw-activity.js`

Set your SUPABASE_URL and SUPABASE_ANON_KEY constants.

The complete tutorial is available [here](https://developer.chrome.com/docs/extensions/get-started/tutorial/service-worker-events).

## Running this extension

1. Clone this repository.
2. Load this directory in Chrome as an [unpacked extension](https://developer.chrome.com/docs/extensions/mv3/getstarted/development-basics/#load-unpacked).
3. Type "api" in the omnibox followed by tab or space and select a suggestion.
4. Click on "Tip" button in the navigation bar.
