// Activity tracking service worker for Twin Activity Tracker
console.log('sw-activity.js loaded');

// Supabase configuration
const SUPABASE_URL = 'https://azukxxbyryqqlagedszg.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImF6dWt4eGJ5cnlxcWxhZ2Vkc3pnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTc3NzE0OTEsImV4cCI6MjA3MzM0NzQ5MX0.oIuToK9KvRehaudNotLg0M5C1PIBJYZWiYgVla-u6KA';

// Get current authenticated user
async function getCurrentUser() {
  const result = await chrome.storage.local.get(['twinUser']);
  return result.twinUser || null;
}

// Check if tracking is enabled
async function isTrackingEnabled() {
  const result = await chrome.storage.local.get(['trackingEnabled']);
  return result.trackingEnabled !== false; // Default to true
}

// Save activity to Supabase
async function saveActivity(activityData) {
  const user = await getCurrentUser();
  const trackingEnabled = await isTrackingEnabled();

  if (!user || !trackingEnabled) {
    console.log('Not saving activity - user not logged in or tracking disabled');
    return;
  }

  try {
    console.log('Saving activity:', activityData);

    const response = await fetch(`${SUPABASE_URL}/rest/v1/activities`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
        'apikey': SUPABASE_ANON_KEY,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        user_id: user.id,
        url: activityData.url,
        title: activityData.title || null,
        // domain is auto-generated in your schema
        processed: false
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Failed to save activity:', errorText);
    } else {
      console.log('Activity saved successfully');
    }
  } catch (error) {
    console.error('Error saving activity:', error);
  }
}

// Get last activity from Supabase
async function getLastActivity() {
  const user = await getCurrentUser();
  
  if (!user) {
    console.log('No user logged in');
    return null;
  }

  try {
    const response = await fetch(`${SUPABASE_URL}/rest/v1/activities?user_id=eq.${user.id}&order=timestamp.desc&limit=1`, {
      headers: {
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
        'apikey': SUPABASE_ANON_KEY,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      console.error('Failed to fetch last activity:', await response.text());
      return null;
    }

    const activities = await response.json();
    return activities.length > 0 ? activities[0].timestamp : null;
  } catch (error) {
    console.error('Error fetching last activity:', error);
    return null;
  }
}

// Handle activity tracking messages
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.type) {
    case 'TRACK_ACTIVITY':
      saveActivity(message.data).then(() => {
        sendResponse({ success: true });
      }).catch(error => {
        console.error('Track activity error:', error);
        sendResponse({ success: false, error: error.message });
      });
      return true; // Will respond asynchronously
      
    case 'GET_LAST_ACTIVITY':
      console.log('GET_LAST_ACTIVITY message received');
      getLastActivity().then(lastActivity => {
        console.log('Last activity retrieved:', lastActivity);
        sendResponse({ 
          success: true, 
          lastActivity: lastActivity 
        });
      }).catch(error => {
        console.error('Get last activity error:', error);
        sendResponse({ success: false, error: error.message });
      });
      return true; // Will respond asynchronously
  }
});

// Track tab navigation automatically
chrome.webNavigation.onCompleted.addListener(async (details) => {
  // Only track main frame navigation (not iframes)
  if (details.frameId === 0) {
    const trackingEnabled = await isTrackingEnabled();
    const user = await getCurrentUser();

    if (!trackingEnabled || !user) {
      return;
    }

    try {
      const tab = await chrome.tabs.get(details.tabId);

      // Filter out chrome:// and extension pages
      if (tab.url &&
          !tab.url.startsWith('chrome://') &&
          !tab.url.startsWith('chrome-extension://') &&
          !tab.url.startsWith('about:') &&
          !tab.url.startsWith('moz-extension://')) {

        console.log('Auto-tracking navigation to:', tab.url);

        await saveActivity({
          url: tab.url,
          title: tab.title || null,
          type: 'navigation'
        });
      }
    } catch (error) {
      console.error('Error tracking navigation:', error);
    }
  }
});

// Track new tab creation
chrome.tabs.onCreated.addListener(async (tab) => {
  const trackingEnabled = await isTrackingEnabled();
  const user = await getCurrentUser();

  if (!trackingEnabled || !user) {
    return;
  }

  if (tab.url &&
      !tab.url.startsWith('chrome://') &&
      !tab.url.startsWith('chrome-extension://') &&
      !tab.url.startsWith('about:')) {

    console.log('Auto-tracking new tab:', tab.url);

    await saveActivity({
      url: tab.url,
      title: tab.title || 'New Tab',
      type: 'new_tab'
    });
  }
});