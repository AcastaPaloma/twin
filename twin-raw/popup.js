// Popup script for Twin Activity Tracker
console.log('Twin popup loaded');

document.addEventListener('DOMContentLoaded', async () => {
  await initializePopup();
});

async function initializePopup() {
  const loading = document.getElementById('loading');
  const loginForm = document.getElementById('loginForm');
  const dashboard = document.getElementById('dashboard');

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
  // Login form
  const loginFormElement = document.getElementById('loginFormElement');
  if (loginFormElement) {
    loginFormElement.addEventListener('submit', handleLogin);
  }

  // Logout button
  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', handleLogout);
  }

  // Tracking toggle
  const trackingToggle = document.getElementById('trackingToggle');
  if (trackingToggle) {
    trackingToggle.addEventListener('click', handleTrackingToggle);
  }
}

function showLoginForm() {
  document.getElementById('loginForm').classList.add('show');
  document.getElementById('dashboard').classList.remove('show');
}

function showDashboard(user) {
  document.getElementById('loginForm').classList.remove('show');
  document.getElementById('dashboard').classList.add('show');
  document.getElementById('userEmail').textContent = user.email;
}

async function handleLogin(event) {
  event.preventDefault();

  const email = document.getElementById('email').value.trim();
  const phone = document.getElementById('phone').value.trim();
  const loginBtn = document.getElementById('loginBtn');
  const messageDiv = document.getElementById('message');

  if (!email) {
    showMessage('Please enter an email address', 'error');
    return;
  }

  loginBtn.disabled = true;
  loginBtn.textContent = 'Signing in...';

  try {
    const response = await chrome.runtime.sendMessage({
      type: 'LOGIN',
      email: email,
      phone: phone
    });

    if (response && response.success) {
      showMessage('Login successful!', 'success');
      setTimeout(() => {
        showDashboard(response.user);
      }, 1000);
    } else {
      showMessage(response?.error || 'Login failed. Please try again.', 'error');
    }

  } catch (error) {
    console.error('Login error:', error);
    showMessage('Login failed. Please try again.', 'error');
  }

  loginBtn.disabled = false;
  loginBtn.textContent = 'Sign In';
}

async function handleLogout() {
  try {
    const response = await chrome.runtime.sendMessage({ type: 'LOGOUT' });

    if (response && response.success) {
      showLoginForm();
      document.getElementById('email').value = '';
      document.getElementById('phone').value = '';
      hideMessage();
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

function hideMessage() {
  const messageDiv = document.getElementById('message');
  messageDiv.style.display = 'none';
}