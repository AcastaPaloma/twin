// Activity tracker content script
console.log('Twin activity tracker loaded on:', window.location.href);

let startTime = Date.now();
let isTracking = false;

// Check if tracking is enabled
chrome.runtime.sendMessage({ type: 'GET_TRACKING_STATUS' }, (response) => {
  isTracking = response && response.enabled;
  if (isTracking) {
    initializeTracking();
  }
});

function initializeTracking() {
  // Track page visit
  trackPageVisit();

  // Track clicks on links
  trackLinkClicks();

  // Track search queries if on search engines
  trackSearchQueries();

  // Track time spent when page unloads
  window.addEventListener('beforeunload', trackTimeSpent);
  window.addEventListener('pagehide', trackTimeSpent);
}

function trackPageVisit() {
  if (!isTracking) return;

  const activityData = {
    url: window.location.href,
    title: document.title,
    timestamp: new Date().toISOString(),
    type: 'page_visit'
  };

  chrome.runtime.sendMessage({
    type: 'TRACK_ACTIVITY',
    data: activityData
  });
}

function trackLinkClicks() {
  if (!isTracking) return;

  document.addEventListener('click', (event) => {
    const link = event.target.closest('a');
    if (link && link.href) {
      const activityData = {
        url: link.href,
        title: link.textContent || link.href,
        timestamp: new Date().toISOString(),
        type: 'link_click',
        sourceUrl: window.location.href
      };

      chrome.runtime.sendMessage({
        type: 'TRACK_ACTIVITY',
        data: activityData
      });
    }
  });
}

function trackSearchQueries() {
  if (!isTracking) return;

  // Google search
  if (window.location.hostname.includes('google.com')) {
    const searchParams = new URLSearchParams(window.location.search);
    const query = searchParams.get('q');

    if (query) {
      const activityData = {
        url: window.location.href,
        title: `Search: ${query}`,
        timestamp: new Date().toISOString(),
        type: 'search',
        searchQuery: query
      };

      chrome.runtime.sendMessage({
        type: 'TRACK_ACTIVITY',
        data: activityData
      });
    }
  }

  // YouTube search
  if (window.location.hostname.includes('youtube.com')) {
    const searchParams = new URLSearchParams(window.location.search);
    const query = searchParams.get('search_query');

    if (query) {
      const activityData = {
        url: window.location.href,
        title: `YouTube Search: ${query}`,
        timestamp: new Date().toISOString(),
        type: 'search',
        searchQuery: query
      };

      chrome.runtime.sendMessage({
        type: 'TRACK_ACTIVITY',
        data: activityData
      });
    }
  }

  // Bing search
  if (window.location.hostname.includes('bing.com')) {
    const searchParams = new URLSearchParams(window.location.search);
    const query = searchParams.get('q');

    if (query) {
      const activityData = {
        url: window.location.href,
        title: `Bing Search: ${query}`,
        timestamp: new Date().toISOString(),
        type: 'search',
        searchQuery: query
      };

      chrome.runtime.sendMessage({
        type: 'TRACK_ACTIVITY',
        data: activityData
      });
    }
  }
}

function trackTimeSpent() {
  if (!isTracking) return;

  const timeSpent = Math.round((Date.now() - startTime) / 1000); // in seconds

  if (timeSpent > 5) { // Only track if spent more than 5 seconds
    const activityData = {
      url: window.location.href,
      title: document.title,
      timestamp: new Date().toISOString(),
      type: 'time_spent',
      timeSpent: timeSpent
    };

    chrome.runtime.sendMessage({
      type: 'TRACK_ACTIVITY',
      data: activityData
    });
  }
}

// Listen for tracking status changes
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'TRACKING_STATUS_CHANGED') {
    isTracking = message.enabled;
    if (isTracking && startTime === 0) {
      startTime = Date.now();
      initializeTracking();
    }
  }
});