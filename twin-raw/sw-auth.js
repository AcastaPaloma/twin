// Authentication service worker for Twin Activity Tracker
console.log('sw-auth.js loaded');

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

// Login user with email and phone
async function loginUser(email, phone = '') {
  try {
    console.log('Attempting login for:', email);

    // Check if user exists in Supabase
    const response = await fetch(`${SUPABASE_URL}/rest/v1/users?email=eq.${encodeURIComponent(email)}&select=*`, {
      headers: {
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
        'apikey': SUPABASE_ANON_KEY,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Failed to check user:', errorText);
      throw new Error('Failed to check user');
    }

    const users = await response.json();
    console.log('Found users:', users);

    if (users.length > 0) {
      // User exists, log them in
      const user = users[0];
      console.log('User found, logging in:', user);

      // Update last login if needed
      const updateResponse = await fetch(`${SUPABASE_URL}/rest/v1/users?id=eq.${user.id}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
          'apikey': SUPABASE_ANON_KEY,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          is_active: true
        })
      });

      if (updateResponse.ok) {
        await setCurrentUser(user);
        return { success: true, user };
      } else {
        console.error('Failed to update user status');
        await setCurrentUser(user);
        return { success: true, user };
      }
    } else {
      // User doesn't exist, create new user
      console.log('Creating new user for:', email);

      const createResponse = await fetch(`${SUPABASE_URL}/rest/v1/users`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
          'apikey': SUPABASE_ANON_KEY,
          'Content-Type': 'application/json',
          'Prefer': 'return=representation'
        },
        body: JSON.stringify({
          email: email,
          phone_number: phone || '', // Use provided phone or empty string
          is_active: true
        })
      });

      if (!createResponse.ok) {
        const errorText = await createResponse.text();
        console.error('Failed to create user:', errorText);
        throw new Error('Failed to create user account');
      }

      const newUsers = await createResponse.json();
      const newUser = newUsers[0];
      console.log('New user created:', newUser);

      await setCurrentUser(newUser);
      return { success: true, user: newUser };
    }
  } catch (error) {
    console.error('Login error:', error);
    return { success: false, error: error.message };
  }
}

// Check tracking status
async function isTrackingEnabled() {
  const result = await chrome.storage.local.get(['trackingEnabled']);
  return result.trackingEnabled !== false; // Default to true
}

// Handle authentication messages
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('Auth message received:', message);

  switch (message.type) {
    case 'LOGIN':
      loginUser(message.email, message.phone).then(result => {
        console.log('Login result:', result);
        sendResponse(result);
      }).catch(error => {
        console.error('Login error:', error);
        sendResponse({ success: false, error: error.message });
      });
      return true; // Will respond asynchronously

    case 'LOGOUT':
      clearCurrentUser().then(() => {
        sendResponse({ success: true });
      }).catch(error => {
        console.error('Logout error:', error);
        sendResponse({ success: false, error: error.message });
      });
      return true;

    case 'GET_USER':
      getCurrentUser().then(user => {
        sendResponse({ user });
      }).catch(error => {
        console.error('Get user error:', error);
        sendResponse({ user: null });
      });
      return true;

    case 'TOGGLE_TRACKING':
      chrome.storage.local.set({ trackingEnabled: message.enabled }).then(() => {
        // Notify all tabs about tracking status change
        chrome.tabs.query({}, (tabs) => {
          tabs.forEach(tab => {
            chrome.tabs.sendMessage(tab.id, {
              type: 'TRACKING_STATUS_CHANGED',
              enabled: message.enabled
            }).catch(() => {
              // Ignore errors for tabs that don't have content script
            });
          });
        });
        sendResponse({ success: true });
      }).catch(error => {
        console.error('Toggle tracking error:', error);
        sendResponse({ success: false, error: error.message });
      });
      return true;

    case 'GET_TRACKING_STATUS':
      isTrackingEnabled().then(enabled => {
        sendResponse({ enabled });
      }).catch(error => {
        console.error('Get tracking status error:', error);
        sendResponse({ enabled: true });
      });
      return true;
  }
});

// Initialize extension
chrome.runtime.onInstalled.addListener(async () => {
  console.log('Twin Activity Tracker installed');

  // Set default tracking status
  const result = await chrome.storage.local.get(['trackingEnabled']);
  if (result.trackingEnabled === undefined) {
    await chrome.storage.local.set({ trackingEnabled: true });
  }
});