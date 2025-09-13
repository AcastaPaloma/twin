// Content script for YouTube
console.log('Twin YouTube content script loaded');

// Extract search term from YouTube URL
function getSearchTerm() {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get('search_query') || '';
}

// Track YouTube search
function trackYouTubeSearch() {
  const searchTerm = getSearchTerm();
  if (!searchTerm || !window.location.pathname.includes('/results')) return;

  // Create a descriptive title for the search activity
  const title = `YouTube Search: ${searchTerm}`;

  chrome.runtime.sendMessage({
    type: 'ACTIVITY',
    data: {
      url: window.location.href,
      title: title
    }
  });
}

// Track video clicks from search results and general browsing
function trackVideoClicks() {
  const videoSelectors = [
    'a#video-title',                    // Video title links
    'a[href*="/watch?"]',              // Watch page links
    '.ytd-video-renderer a',           // Video renderer links
    '.ytd-compact-video-renderer a'    // Compact video links
  ];

  videoSelectors.forEach(selector => {
    document.querySelectorAll(selector).forEach(link => {
      if (!link.hasAttribute('data-twin-tracked') && link.href.includes('/watch?')) {
        link.setAttribute('data-twin-tracked', 'true');

        link.addEventListener('click', (e) => {
          const clickedUrl = link.href;
          const clickedTitle = link.textContent.trim() ||
                              link.getAttribute('aria-label') ||
                              'YouTube Video';

          // Track the video click as an activity
          chrome.runtime.sendMessage({
            type: 'ACTIVITY',
            data: {
              url: clickedUrl,
              title: clickedTitle
            }
          });
        });
      }
    });
  });
}

// Track general YouTube activity
function trackYouTubeActivity() {
  // Only track significant page types, not every YouTube page
  if (window.location.pathname.includes('/watch') ||
      window.location.pathname.includes('/results') ||
      window.location.pathname === '/' ||
      window.location.pathname.includes('/channel') ||
      window.location.pathname.includes('/playlist')) {

    chrome.runtime.sendMessage({
      type: 'ACTIVITY',
      data: {
        url: window.location.href,
        title: document.title
      }
    });
  }
}// Initialize tracking
function init() {
  trackYouTubeSearch();
  trackVideoClicks();
  trackYouTubeActivity();

  // Re-track when new content loads (YouTube is a SPA)
  const observer = new MutationObserver(() => {
    trackVideoClicks();
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
}

// YouTube is a single-page application, so we need to listen for navigation
let currentUrl = window.location.href;

function checkForNavigation() {
  if (currentUrl !== window.location.href) {
    currentUrl = window.location.href;
    // Clear session if moving away from search results
    if (!window.location.pathname.includes('/results')) {
      sessionStorage.removeItem('twinYouTubeSession');
    }
    setTimeout(init, 500); // Delay to let YouTube load content
  }
}

// Check for navigation changes
setInterval(checkForNavigation, 1000);

// Initial load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}