// Session management utility
// Uses sessionStorage for per-tab isolation, with localStorage fallback for URL-based sessions

const STORAGE_KEY_PREFIX = "evoplay_session_";

/**
 * Get or create a session ID for a specific game.
 * 
 * Priority:
 * 1. URL parameter (if provided, saves to localStorage for persistence)
 * 2. sessionStorage (per-tab, isolated)
 * 3. Generate new one and store in sessionStorage
 * 
 * This ensures each browser tab gets its own independent session,
 * unless explicitly sharing via URL parameter.
 */
export function getSessionId(gameName) {
  const key = STORAGE_KEY_PREFIX + gameName;
  
  // First check sessionStorage (per-tab isolation)
  let sessionId = sessionStorage.getItem(key);
  
  if (!sessionId) {
    // Generate a simple session ID (using timestamp + random)
    sessionId = `s_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    sessionStorage.setItem(key, sessionId);
  }
  
  return sessionId;
}

/**
 * Reset session ID for a game (creates a new one).
 * Clears both sessionStorage and localStorage.
 */
export function resetSessionId(gameName) {
  const key = STORAGE_KEY_PREFIX + gameName;
  sessionStorage.removeItem(key);
  localStorage.removeItem(key);
  return getSessionId(gameName);
}

/**
 * Add session_id to URL query parameters.
 */
export function addSessionToUrl(url, sessionId) {
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}session_id=${encodeURIComponent(sessionId)}`;
}

/**
 * Get session_id from URL query parameters.
 */
export function getSessionIdFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("session_id");
}

/**
 * Set session_id from URL for a specific game (if provided in URL).
 * 
 * When session_id is provided in URL (e.g., from Agent auto-open),
 * it's saved to both sessionStorage (for this tab) and localStorage (for persistence).
 * This allows sharing a session across tabs if needed, or isolating per-tab by default.
 */
export function setSessionIdFromUrl(gameName) {
  const urlSessionId = getSessionIdFromUrl();
  if (urlSessionId) {
    const key = STORAGE_KEY_PREFIX + gameName;
    // Save to sessionStorage for this tab
    sessionStorage.setItem(key, urlSessionId);
    // Also save to localStorage for persistence (e.g., page refresh)
    localStorage.setItem(key, urlSessionId);
    return urlSessionId;
  }
  return null;
}
