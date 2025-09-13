// Supabase helper functions
class SupabaseHelper {
  constructor() {
    this.url = 'https://azukxxbyryqqlagedszg.supabase.co';
    this.anonKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImF6dWt4eGJ5cnlxcWxhZ2Vkc3pnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTc3NzE0OTEsImV4cCI6MjA3MzM0NzQ5MX0.oIuToK9KvRehaudNotLg0M5C1PIBJYZWiYgVla-u6KA';
  }

  async request(endpoint, options = {}) {
    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.anonKey}`,
        'apikey': this.anonKey
      }
    };

    const response = await fetch(`${this.url}/rest/v1/${endpoint}`, {
      ...defaultOptions,
      ...options,
      headers: { ...defaultOptions.headers, ...options.headers }
    });

    if (!response.ok) {
      throw new Error(`Supabase error: ${response.status} ${await response.text()}`);
    }

    return response.json();
  }

  async getRecentSearches(userId, limit = 10) {
    return this.request(`search_activities?user_id=eq.${userId}&order=timestamp.desc&limit=${limit}`);
  }

  async getRecentBrowsingHistory(userId, limit = 10) {
    return this.request(`browsing_history?user_id=eq.${userId}&order=visit_timestamp.desc&limit=${limit}`);
  }

  async getSearchStats(userId) {
    // Get search count by engine
    const searchStats = await this.request(
      `search_activities?user_id=eq.${userId}&select=search_engine,count(*)`
    );

    return searchStats;
  }

  async toggleTracking(userId, enabled) {
    return this.request('user_settings', {
      method: 'UPSERT',
      body: JSON.stringify({
        user_id: userId,
        tracking_enabled: enabled
      })
    });
  }

  async getUserSettings(userId) {
    const settings = await this.request(`user_settings?user_id=eq.${userId}`);
    return settings[0] || { tracking_enabled: true };
  }
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
  module.exports = SupabaseHelper;
}