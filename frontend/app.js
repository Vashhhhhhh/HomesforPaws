/**
 * app.js — PawsForward Frontend Application Logic (Phase 1)
 * ==========================================================
 * Phase 1 Goal: Prove the frontend can TALK to the backend.
 *
 * This file makes ONE API call to the health check endpoint.
 * If the backend is running, we show "Connected".
 * If not, we show an error. Simple. Verifiable. Real.
 *
 * INTERN NOTE: The Fetch API is how modern JavaScript makes HTTP requests.
 * It returns a Promise — meaning the response doesn't come back instantly.
 * We use async/await syntax to handle this cleanly.
 *
 * Think of a Promise like ordering at a restaurant:
 *   - You place the order (call fetch)
 *   - You don't stand frozen at the counter waiting (async)
 *   - When food is ready, the waiter brings it to you (await resolves)
 *   - If the kitchen is on fire, you get an error (catch)
 */

// ============================================================
// CONFIGURATION
// ============================================================
// In development, the backend runs on port 8000.
// In production, this would be the deployed API domain.
// We'll move this to an environment-specific config in Phase 2.
const API_BASE_URL = "http://127.0.0.1:8000";

// ============================================================
// API HEALTH CHECK
// ============================================================

/**
 * Calls the backend health check endpoint and updates the UI
 * with the connection status.
 */
async function checkApiStatus() {
    const indicator = document.getElementById("status-indicator");

    try {
        // The Fetch API returns a Response object (a Promise).
        // `await` pauses execution here until the response arrives.
        const response = await fetch(`${API_BASE_URL}/`);

        if (!response.ok) {
            // HTTP error (4xx, 5xx) — server responded but with an error.
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        // Parse the JSON body from the response.
        // This is ALSO async — the body might not be fully received yet.
        const data = await response.json();

        // Update the UI to reflect success.
        indicator.textContent = `● Connected — ${data.message}`;
        indicator.className = "status-badge connected";

        console.log("✅ API health check passed:", data);

    } catch (error) {
        // Network error, CORS issue, or server down.
        indicator.textContent = `● Connection failed — Is the backend running? (${error.message})`;
        indicator.className = "status-badge error";

        console.error("❌ API health check failed:", error);
    }
}

// ============================================================
// INITIALIZATION
// ============================================================
// Run when the DOM is fully loaded and parsed.
// Never manipulate DOM elements before this event fires —
// the elements might not exist yet.
document.addEventListener("DOMContentLoaded", () => {
    console.log("🐾 PawsForward frontend initialized.");
    checkApiStatus();
});
