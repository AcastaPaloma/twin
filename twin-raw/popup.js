// Popup script for Twin Activity Tracker
console.log('Twin popup loaded');

document.addEventListener('DOMContentLoaded', async () => {
  await initializePopup();
});

async function initializePopup() {
  const loading = document.getElementById('loading');
  const loginForm = document.getElementById('loginForm');
  const dashboard = document.getElementById('dashboard');
  const settingsForm = document.getElementById('settingsForm');
  
  try {
    // Check if user is logged in
    const response = await chrome.runtime.sendMessage({ type: 'GET_USER' });
    
    loading.style.display = 'none';
    
    if (response && response.user) {
      showDashboard(response.user);
    } else {
      showLoginForm();
    }
    
    // Setup event listeners
    setupEventListeners();
    
    // Update tracking status
    await updateTrackingStatus();
    
  } catch (error) {
    console.error('Error initializing popup:', error);
    loading.style.display = 'none';
    showLoginForm();
    setupEventListeners();
  }
}

function setupEventListeners() {
  // Sign in form
  const signinFormElement = document.getElementById('signinFormElement');
  if (signinFormElement) {
    signinFormElement.addEventListener('submit', handleSignin);
  }

  // Sign up form
  const signupFormElement = document.getElementById('signupFormElement');
  if (signupFormElement) {
    signupFormElement.addEventListener('submit', handleSignup);
  }

  // Settings form
  const settingsFormElement = document.getElementById('settingsFormElement');
  if (settingsFormElement) {
    settingsFormElement.addEventListener('submit', handleSettingsUpdate);
  }

  // Form toggle links
  const showSignupLink = document.getElementById('showSignupLink');
  if (showSignupLink) {
    showSignupLink.addEventListener('click', (e) => {
      e.preventDefault();
      showSignupForm();
    });
  }

  const showSigninLink = document.getElementById('showSigninLink');
  if (showSigninLink) {
    showSigninLink.addEventListener('click', (e) => {
      e.preventDefault();
      showSigninForm();
    });
  }

  // Logout button
  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', handleLogout);
  }

  // Settings button
  const settingsBtn = document.getElementById('settingsBtn');
  if (settingsBtn) {
    settingsBtn.addEventListener('click', showSettings);
  }

  // Cancel settings button
  const cancelSettingsBtn = document.getElementById('cancelSettingsBtn');
  if (cancelSettingsBtn) {
    cancelSettingsBtn.addEventListener('click', () => {
      const currentUser = getCurrentUserFromStorage();
      showDashboard(currentUser);
    });
  }
  
  // Tracking toggle
  const trackingToggle = document.getElementById('trackingToggle');
  if (trackingToggle) {
    trackingToggle.addEventListener('click', handleTrackingToggle);
  }
}

let currentUserData = null;

function showLoginForm() {
  document.getElementById('loginForm').classList.add('show');
  document.getElementById('dashboard').classList.remove('show');
  document.getElementById('settingsForm').classList.remove('show');
  showSigninForm();
}

function showSigninForm() {
  document.getElementById('signinFormElement').classList.remove('hidden');
  document.getElementById('signupFormElement').classList.add('hidden');
  document.getElementById('authSubtitle').textContent = 'Sign in to track your activity';
  clearMessage();
}

function showSignupForm() {
  document.getElementById('signinFormElement').classList.add('hidden');
  document.getElementById('signupFormElement').classList.remove('hidden');
  document.getElementById('authSubtitle').textContent = 'Create your account';
  clearMessage();
}

function showDashboard(user) {
  currentUserData = user;
  document.getElementById('loginForm').classList.remove('show');
  document.getElementById('dashboard').classList.add('show');
  document.getElementById('settingsForm').classList.remove('show');
  document.getElementById('userEmail').textContent = user.email;
}

function showSettings() {
  document.getElementById('loginForm').classList.remove('show');
  document.getElementById('dashboard').classList.remove('show');
  document.getElementById('settingsForm').classList.add('show');
  
  // Pre-populate settings form
  if (currentUserData) {
    document.getElementById('settingsEmail').value = currentUserData.email || '';
    document.getElementById('settingsPhone').value = currentUserData.phone_number || '';
  }
  clearSettingsMessage();
}

function getCurrentUserFromStorage() {
  return currentUserData;
}

async function handleSignin(event) {
  event.preventDefault();
  
  const identifier = document.getElementById('signinIdentifier').value.trim();
  const signinBtn = document.getElementById('signinBtn');
  
  if (!identifier) {
    showMessage('Please enter your email or phone number', 'error');
    return;
  }
  
  signinBtn.disabled = true;
  signinBtn.textContent = 'Signing in...';
  
  try {
    const response = await chrome.runtime.sendMessage({
      type: 'SIGNIN',
      identifier: identifier
    });
    
    if (response && response.success) {
      showMessage('Sign in successful!', 'success');
      setTimeout(() => {
        showDashboard(response.user);
      }, 1000);
    } else {
      showMessage(response?.error || 'Sign in failed. Please try again.', 'error');
    }
    
  } catch (error) {
    console.error('Signin error:', error);
    showMessage('Sign in failed. Please try again.', 'error');
  }
  
  signinBtn.disabled = false;
  signinBtn.textContent = 'Sign In';
}

async function handleSignup(event) {
  event.preventDefault();
  
  const email = document.getElementById('signupEmail').value.trim();
  const phone = document.getElementById('signupPhone').value.trim();
  const signupBtn = document.getElementById('signupBtn');
  
  if (!email || !phone) {
    showMessage('Please fill in all fields', 'error');
    return;
  }
  
  signupBtn.disabled = true;
  signupBtn.textContent = 'Creating account...';
  
  try {
    const response = await chrome.runtime.sendMessage({
      type: 'SIGNUP',
      email: email,
      phone: phone
    });
    
    if (response && response.success) {
      showMessage('Account created successfully!', 'success');
      setTimeout(() => {
        showDashboard(response.user);
      }, 1000);
    } else {
      showMessage(response?.error || 'Account creation failed. Please try again.', 'error');
    }
    
  } catch (error) {
    console.error('Signup error:', error);
    showMessage('Account creation failed. Please try again.', 'error');
  }
  
  signupBtn.disabled = false;
  signupBtn.textContent = 'Sign Up';
}

async function handleSettingsUpdate(event) {
  event.preventDefault();
  
  const email = document.getElementById('settingsEmail').value.trim();
  const phone = document.getElementById('settingsPhone').value.trim();
  const saveBtn = document.getElementById('saveSettingsBtn');
  
  if (!email || !phone) {
    showSettingsMessage('Please fill in all fields', 'error');
    return;
  }
  
  saveBtn.disabled = true;
  saveBtn.textContent = 'Saving...';
  
  try {
    const response = await chrome.runtime.sendMessage({
      type: 'UPDATE_USER',
      email: email,
      phone: phone
    });
    
    if (response && response.success) {
      showSettingsMessage('Settings updated successfully!', 'success');
      setTimeout(() => {
        showDashboard(response.user);
      }, 1000);
    } else {
      showSettingsMessage(response?.error || 'Update failed. Please try again.', 'error');
    }
    
  } catch (error) {
    console.error('Settings update error:', error);
    showSettingsMessage('Update failed. Please try again.', 'error');
  }
  
  saveBtn.disabled = false;
  saveBtn.textContent = 'Save Changes';
}

async function handleLogout() {
  try {
    const response = await chrome.runtime.sendMessage({ type: 'LOGOUT' });
    
    if (response && response.success) {
      currentUserData = null;
      showLoginForm();
      // Clear all form fields
      document.getElementById('signinIdentifier').value = '';
      document.getElementById('signupEmail').value = '';
      document.getElementById('signupPhone').value = '';
      document.getElementById('settingsEmail').value = '';
      document.getElementById('settingsPhone').value = '';
      clearMessage();
      clearSettingsMessage();
    }
  } catch (error) {
    console.error('Logout error:', error);
  }
}

async function handleTrackingToggle() {
  const toggle = document.getElementById('trackingToggle');
  const isEnabled = toggle.classList.contains('on');
  const newState = !isEnabled;
  
  try {
    const response = await chrome.runtime.sendMessage({
      type: 'TOGGLE_TRACKING',
      enabled: newState
    });
    
    if (response && response.success) {
      if (newState) {
        toggle.classList.add('on');
      } else {
        toggle.classList.remove('on');
      }
      updateTrackingStatus();
    }
  } catch (error) {
    console.error('Tracking toggle error:', error);
  }
}

async function updateTrackingStatus() {
  try {
    const response = await chrome.runtime.sendMessage({ type: 'GET_TRACKING_STATUS' });
    
    if (response) {
      const toggle = document.getElementById('trackingToggle');
      const statusInfo = document.getElementById('statusInfo');
      
      if (response.enabled) {
        toggle.classList.add('on');
        statusInfo.textContent = 'Activity tracking is enabled';
      } else {
        toggle.classList.remove('on');
        statusInfo.textContent = 'Activity tracking is disabled';
      }
    }
  } catch (error) {
    console.error('Error updating tracking status:', error);
  }
}

function showMessage(text, type) {
  const messageDiv = document.getElementById('message');
  messageDiv.textContent = text;
  messageDiv.className = `message ${type}`;
  messageDiv.style.display = 'block';
}

function clearMessage() {
  const messageDiv = document.getElementById('message');
  messageDiv.style.display = 'none';
}

function showSettingsMessage(text, type) {
  const messageDiv = document.getElementById('settingsMessage');
  messageDiv.textContent = text;
  messageDiv.className = `message ${type}`;
  messageDiv.style.display = 'block';
}

function clearSettingsMessage() {
  const messageDiv = document.getElementById('settingsMessage');
  messageDiv.style.display = 'none';
}