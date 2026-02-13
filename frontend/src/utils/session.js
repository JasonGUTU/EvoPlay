// Session management utility
// Stores session_id per game in localStorage

const STORAGE_KEY_PREFIX = "evoplay_session_";

/**
 * Get or create a session ID for a specific game.
 * Session IDs are stored in localStorage per game name.
 */
export function getSessionId(gameName) {
  const key = STORAGE_KEY_PREFIX + gameName;
  let sessionId = localStorage.getItem(key);
  
  if (!sessionId) {
    // Generate a simple session ID (using timestamp + random)
    sessionId = `s_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    localStorage.setItem(key, sessionId);
  }
  
  return sessionId;
}

/**
 * Reset session ID for a game (creates a new one).
 */
export function resetSessionId(gameName) {
  const key = STORAGE_KEY_PREFIX + gameName;
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
