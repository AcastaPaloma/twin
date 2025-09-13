// General content script for all websites (excluding Google and YouTube)
console.log('Twin general content script loaded on:', window.location.hostname);

// Track page visit
function trackPageVisit() {
  // Don't track if this is a Chrome internal page
  if (window.location.protocol === 'chrome:' ||
      window.location.protocol === 'chrome-extension:' ||
      window.location.protocol === 'moz-extension:') {
    return;
  }

  chrome.runtime.sendMessage({
    type: 'ACTIVITY',
    data: {
      url: window.location.href,
      title: document.title || 'Untitled Page'
    }
  });
}

// Track clicks on external links
function trackExternalLinks() {
  document.querySelectorAll('a[href]').forEach(link => {
    if (!link.hasAttribute('data-twin-tracked')) {
      link.setAttribute('data-twin-tracked', 'true');

      link.addEventListener('click', (e) => {
        const clickedUrl = link.href;

        // Only track if it's an external link or seems significant
        if (clickedUrl &&
            (clickedUrl.startsWith('http') || clickedUrl.startsWith('https')) &&
            clickedUrl !== window.location.href) {

          const linkText = link.textContent.trim() ||
                          link.getAttribute('aria-label') ||
                          link.getAttribute('title') ||
                          'Link Click';

          chrome.runtime.sendMessage({
            type: 'ACTIVITY',
            data: {
              url: clickedUrl,
              title: linkText
            }
          });
        }
      });
    }
  });
}

// Detect search forms on the current page
function trackSearchForms() {
  const searchSelectors = [
    'input[type="search"]',
    'input[name*="search"]',
    'input[name*="query"]',
    'input[name*="q"]',
    'input[placeholder*="search" i]',
    'input[placeholder*="find" i]'
  ];

  searchSelectors.forEach(selector => {
    document.querySelectorAll(selector).forEach(input => {
      if (!input.hasAttribute('data-twin-tracked')) {
        input.setAttribute('data-twin-tracked', 'true');

        // Track when user submits search
        const form = input.closest('form');
        if (form) {
          form.addEventListener('submit', (e) => {
            const searchTerm = input.value.trim();
            if (searchTerm) {
              const title = `Search on ${window.location.hostname}: ${searchTerm}`;

              chrome.runtime.sendMessage({
                type: 'ACTIVITY',
                data: {
                  url: window.location.href,
                  title: title
                }
              });
            }
          });
        }
      }
    });
  });
}// Initialize tracking
function init() {
  trackPageVisit();
  trackExternalLinks();
  trackSearchForms();

  // Re-track links when new content loads
  const observer = new MutationObserver(() => {
    trackExternalLinks();
    trackSearchForms();
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

// Track when user leaves the page
window.addEventListener('beforeunload', () => {
  const timeSpent = Math.round((Date.now() - startTime) / 1000);
  chrome.runtime.sendMessage({
    type: 'PAGE_TIME_SPENT',
    data: {
      url: window.location.href,
      timeSpent: timeSpent
    }
  });
});