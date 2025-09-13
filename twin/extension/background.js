// Background script for Twin extension
console.log('Twin background script loaded');

// Supabase configuration
const SUPABASE_URL = 'https://azukxxbyryqqlagedszg.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImF6dWt4eGJ5cnlxcWxhZ2Vkc3pnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTc3NzE0OTEsImV4cCI6MjA3MzM0NzQ5MX0.oIuToK9KvRehaudNotLg0M5C1PIBJYZWiYgVla-u6KA';

// Get current authenticated user
async function getCurrentUser() {
  const result = await chrome.storage.local.get(['twinUser']);
  return result.twinUser || null;
}

// Set current user
async function setCurrentUser(user) {
  await chrome.storage.local.set({ twinUser: user });
}

// Clear current user (logout)
async function clearCurrentUser() {
  await chrome.storage.local.remove(['twinUser']);
}

// Login user with email
async function loginUser(email) {
  try {
    // Check if user exists in Supabase
    const response = await fetch(`${SUPABASE_URL}/rest/v1/users?email=eq.${encodeURIComponent(email)}&select=*`, {
      headers: {
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
        'apikey': SUPABASE_ANON_KEY
      }
    });

    if (!response.ok) {
      throw new Error('Failed to check user');
    }

    const users = await response.json();

    if (users.length > 0) {
      // User exists, log them in
      const user = users[0];
      await setCurrentUser(user);
      return { success: true, user };
    } else {
      // User doesn't exist, create new user
      const createResponse = await fetch(`${SUPABASE_URL}/rest/v1/users`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
          'apikey': SUPABASE_ANON_KEY,
          'Prefer': 'return=representation'
        },
        body: JSON.stringify({
          email: email,
          is_active: true
        })
      });

      if (!createResponse.ok) {
        throw new Error('Failed to create user');
      }

      const newUsers = await createResponse.json();
      const newUser = newUsers[0];
      await setCurrentUser(newUser);
      return { success: true, user: newUser, isNew: true };
    }
  } catch (error) {
    console.error('Login error:', error);
    return { success: false, error: error.message };
  }
}

// Check if tracking is enabled
async function isTrackingEnabled() {
  const result = await chrome.storage.local.get(['trackingEnabled']);
  return result.trackingEnabled !== false; // Default to true
}

// Save activity to Supabase (matches your activities table schema)
async function saveActivity(data) {
  if (!(await isTrackingEnabled())) return;

  const user = await getCurrentUser();
  if (!user) return; // No authenticated user

  try {
    const response = await fetch(`${SUPABASE_URL}/rest/v1/activities`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
        'apikey': SUPABASE_ANON_KEY
      },
      body: JSON.stringify({
        user_id: user.id,
        url: data.url,
        title: data.title || null,
        // domain is auto-generated in your schema
        processed: false
      })
    });

    if (!response.ok) {
      console.error('Failed to save activity:', await response.text());
    }
  } catch (error) {
    console.error('Error saving activity:', error);
  }
}

// Listen for messages from content scripts and popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('Background received message:', message);

  switch (message.type) {
    case 'LOGIN':
      loginUser(message.email).then(result => {
        sendResponse(result);
      });
      return true; // Will respond asynchronously

    case 'LOGOUT':
      clearCurrentUser().then(() => {
        sendResponse({ success: true });
      });
      return true;

    case 'GET_USER':
      getCurrentUser().then(user => {
        sendResponse({ user });
      });
      return true;

    case 'ACTIVITY':
      saveActivity(message.data);
      sendResponse({ success: true });
      break;

    case 'TOGGLE_TRACKING':
      chrome.storage.local.set({ trackingEnabled: message.enabled });
      sendResponse({ success: true });
      break;

    case 'GET_TRACKING_STATUS':
      isTrackingEnabled().then(enabled => {
        sendResponse({ enabled });
      });
      return true;
  }
});

// Track tab navigation
chrome.webNavigation.onCompleted.addListener(async (details) => {
  if (details.frameId === 0) { // Main frame only
    const tab = await chrome.tabs.get(details.tabId);

    if (tab.url &&
        !tab.url.startsWith('chrome://') &&
        !tab.url.startsWith('chrome-extension://') &&
        !tab.url.startsWith('about:')) {

      await saveActivity({
        url: tab.url,
        title: tab.title
      });
    }
  }
});

// Initialize extension
chrome.runtime.onInstalled.addListener(async () => {
  console.log('Twin extension installed');
});

// Keep service worker alive
chrome.runtime.onStartup.addListener(() => {
  console.log('Twin extension started');
});// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('Background received message:', message);

  switch (message.type) {
    case 'SEARCH_DETECTED':
      saveSearchActivity(message.data);
      break;
    case 'SEARCH_RESULT_CLICK':
      updateSearchActivityWithClick(message.data);
      break;
    case 'PAGE_VISIT':
      saveBrowsingHistory(message.data);
      break;
    case 'PAGE_TIME_SPENT':
      updateBrowsingHistoryWithTime(message.data);
      break;
    case 'LINK_CLICK':
      saveLinkClick(message.data);
      break;
    case 'TOGGLE_TRACKING':
      chrome.storage.local.set({ trackingEnabled: message.enabled });
      break;
  }

  sendResponse({ success: true });
});



// Track tab navigation
chrome.webNavigation.onCompleted.addListener(async (details) => {
  if (details.frameId === 0) { // Main frame only
    const tab = await chrome.tabs.get(details.tabId);

    if (tab.url && !tab.url.startsWith('chrome://') && !tab.url.startsWith('chrome-extension://')) {
      await saveBrowsingHistory({
        url: tab.url,
        title: tab.title,
        referrer: null
      });
    }
  }
});

// Initialize extension
chrome.runtime.onInstalled.addListener(async () => {
  console.log('Twin extension installed');
});

// Keep service worker alive
chrome.runtime.onStartup.addListener(() => {
  console.log('Twin extension started');
});