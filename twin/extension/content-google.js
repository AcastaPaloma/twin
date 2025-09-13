// Content script for Google search pages
console.log('Twin Google content script loaded');

// Extract search term from URL or page
function getSearchTerm() {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get('q') || '';
}

// Track search when page loads
function trackSearch() {
  const searchTerm = getSearchTerm();
  if (!searchTerm) return;

  // Create a descriptive title for the search activity
  const title = `Google Search: ${searchTerm}`;

  chrome.runtime.sendMessage({
    type: 'ACTIVITY',
    data: {
      url: window.location.href,
      title: title
    }
  });
}

// Track clicks on search results
function trackSearchResultClicks() {
  // Google search result selectors
  const selectors = [
    'a[href^="https://"]', // General links
    'a[href^="http://"]',  // HTTP links
    '.g a',                // Search result links
    '.rc a',               // Result container links
    '[data-ved] a'         // Google's tracked links
  ];

  selectors.forEach(selector => {
    document.querySelectorAll(selector).forEach(link => {
      if (!link.hasAttribute('data-twin-tracked') &&
          !link.href.includes('google.com') &&
          !link.href.includes('accounts.google.com')) {

        link.setAttribute('data-twin-tracked', 'true');

        link.addEventListener('click', (e) => {
          const clickedUrl = link.href;
          const clickedTitle = link.textContent.trim() ||
                              link.getAttribute('aria-label') ||
                              'Search Result Click';

          // Track the click as an activity
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
}// Initialize tracking
function init() {
  trackSearch();
  trackSearchResultClicks();

  // Re-track clicks when new content loads (for infinite scroll, etc.)
  const observer = new MutationObserver(() => {
    trackSearchResultClicks();
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
}

// Wait for page to load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

// Track when user navigates to a new search
window.addEventListener('popstate', () => {
  setTimeout(init, 100); // Small delay to ensure URL is updated
});