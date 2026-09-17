/**
 * app.js — PawsForward Frontend Application Logic (Phase 2)
 * ==========================================================
 * Connects all frontend sections to backend API endpoints.
 *
 * Endpoints used:
 *   GET  /                              — Health check
 *   GET  /api/v1/pets                   — List all pets
 *   POST /api/v1/pets                   — Create a pet profile
 *   POST /api/v1/pets/{id}/activate     — Activate pet for matching
 *   POST /api/v1/pets/{id}/deactivate   — Deactivate pet from matching
 *   POST /api/v1/surveys/adopter        — Submit adopter survey
 *   GET  /api/v1/surveys/adopter        — List all surveys
 *   POST /api/v1/recommendations/match  — Run semantic matching
 */

// ============================================================
// CONFIGURATION
// ============================================================
const API_BASE_URL = "http://127.0.0.1:8000";

// ============================================================
// DOM READY — Single entry point
// ============================================================
document.addEventListener("DOMContentLoaded", () => {
    checkApiStatus();
    fetchAllPets();
    fetchAllSurveys();
    initAdopterSurveyForm();
    initPetListingForm();
    initMatchControls();
    initCharCounter();
    initFadeInObserver();
});

// ============================================================
// API STATUS — Fixed bottom-right indicator
// ============================================================
async function checkApiStatus() {
    const dot = document.getElementById("status-dot");
    const text = document.getElementById("status-text");

    try {
        const response = await fetch(`${API_BASE_URL}/`);
        if (response.ok) {
            const data = await response.json();
            dot.className = "status-dot connected";
            text.textContent = "API Connected";
            console.log("[API] Health check passed:", data.message);
        } else {
            dot.className = "status-dot error";
            text.textContent = "API Error";
        }
    } catch (error) {
        dot.className = "status-dot error";
        text.textContent = "API Offline";
        console.error("[API] Cannot reach backend:", error.message);
    }
}

// ============================================================
// BROWSE PETS — Fetch and render all pet profiles
// ============================================================
async function fetchAllPets() {
    const grid = document.getElementById("pet-grid");
    const emptyState = document.getElementById("pet-empty-state");

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/pets`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const pets = await response.json();

        if (pets.length === 0) {
            emptyState.style.display = "block";
            return;
        }

        emptyState.style.display = "none";

        // Clear existing cards (but keep empty state element).
        grid.querySelectorAll(".pet-card").forEach(c => c.remove());

        pets.forEach(pet => {
            grid.appendChild(createPetCard(pet));
        });

    } catch (error) {
        console.error("[PETS] Failed to fetch pets:", error.message);
    }
}

/**
 * Build a pet card DOM element from a pet response object.
 */
function createPetCard(pet) {
    const card = document.createElement("div");
    card.className = "pet-card";
    card.id = `pet-card-${pet.id}`;

    const eligibleBadge = pet.is_eligible_for_matching
        ? `<span class="badge badge-eligible">Eligible</span>`
        : `<span class="badge badge-pending">Pending</span>`;

    const verifiedBadge = pet.is_health_verified
        ? `<span class="badge badge-verified">Verified</span>`
        : "";

    const vetBadge = pet.vet_certificate_toggle
        ? `<span class="badge badge-toggle-on">Vet Cert</span>`
        : `<span class="badge badge-toggle-off">No Vet Cert</span>`;

    const healthBadge = pet.health_records_toggle
        ? `<span class="badge badge-toggle-on">Health Rec</span>`
        : `<span class="badge badge-toggle-off">No Health Rec</span>`;

    const picBadge = pet.has_picture_uploaded
        ? `<span class="badge badge-toggle-on">Photo</span>`
        : `<span class="badge badge-toggle-off">No Photo</span>`;

    const description = pet.description || "No description provided.";

    // Action buttons depend on eligibility state.
    let actionHTML;
    if (pet.is_eligible_for_matching) {
        actionHTML = `<button class="btn btn-danger btn-sm" onclick="deactivatePet(${pet.id})">Deactivate</button>`;
    } else {
        const canActivate = pet.description && pet.description.trim().length > 0;
        actionHTML = canActivate
            ? `<button class="btn btn-primary btn-sm" onclick="activatePet(${pet.id})">Activate for Matching</button>`
            : `<button class="btn btn-sm" disabled title="Add a description first">Activate for Matching</button>`;
    }

    card.innerHTML = `
        <div class="pet-card-header">
            <span class="pet-card-name">${escapeHtml(pet.name)}</span>
            ${eligibleBadge}
        </div>
        <p class="pet-card-description">${escapeHtml(description)}</p>
        <div class="pet-card-badges">
            ${verifiedBadge}${vetBadge}${healthBadge}${picBadge}
        </div>
        <div class="pet-card-actions">
            ${actionHTML}
        </div>
    `;

    return card;
}

// ============================================================
// ACTIVATE / DEACTIVATE PET
// ============================================================
async function activatePet(petId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/pets/${petId}/activate`, {
            method: "POST",
        });

        if (response.ok) {
            console.log(`[PETS] Pet ${petId} activated.`);
            fetchAllPets(); // Refresh the grid.
        } else {
            const err = await response.json().catch(() => null);
            const detail = err?.detail || `HTTP ${response.status}`;
            alert(`Activation failed: ${detail}`);
        }
    } catch (error) {
        alert(`Network error: ${error.message}`);
    }
}

async function deactivatePet(petId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/pets/${petId}/deactivate`, {
            method: "POST",
        });

        if (response.ok) {
            console.log(`[PETS] Pet ${petId} deactivated.`);
            fetchAllPets();
        } else {
            const err = await response.json().catch(() => null);
            const detail = err?.detail || `HTTP ${response.status}`;
            alert(`Deactivation failed: ${detail}`);
        }
    } catch (error) {
        alert(`Network error: ${error.message}`);
    }
}

// ============================================================
// PET LISTING FORM — POST /api/v1/pets
// ============================================================
function initPetListingForm() {
    const form = document.getElementById("pet-listing-form");
    const submitBtn = document.getElementById("submit-pet-btn");
    const message = document.getElementById("pet-message");

    if (!form) return;

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const payload = {
            name: document.getElementById("pet-name").value.trim(),
            owner_id: parseInt(document.getElementById("pet-owner-id").value, 10),
            description: document.getElementById("pet-description").value.trim() || null,
            has_picture_uploaded: document.getElementById("pet-picture-uploaded").checked,
            vet_certificate_toggle: document.getElementById("pet-vet-certificate").checked,
            health_records_toggle: document.getElementById("pet-health-records").checked,
        };

        // Client-side guard.
        if (!payload.name || !payload.owner_id || isNaN(payload.owner_id)) {
            showMessage(message, "Pet name and a valid owner ID are required.", "error");
            return;
        }

        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="spinner"></span> Submitting...`;
        hideMessage(message);

        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/pets`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            if (response.ok) {
                const data = await response.json();
                console.log("[PETS] Pet profile created:", data);
                showMessage(message, `"${data.name}" listed successfully (ID: ${data.id}).`, "success");
                form.reset();
                fetchAllPets(); // Auto-refresh the browse section.
            } else {
                const err = await response.json().catch(() => null);
                const detail = err?.detail || `Status ${response.status}`;
                showMessage(message, `Submission failed: ${detail}`, "error");
            }
        } catch (error) {
            showMessage(message, "Could not reach the server. Is the backend running?", "error");
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = "Submit Pet Profile";
        }
    });
}

// ============================================================
// ADOPTER SURVEY FORM — POST /api/v1/surveys/adopter
// ============================================================
function initAdopterSurveyForm() {
    const form = document.getElementById("adopter-survey-form");
    const submitBtn = document.getElementById("submit-survey-btn");
    const message = document.getElementById("survey-message");

    if (!form) return;

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const payload = {
            name: document.getElementById("survey-name").value.trim(),
            email: document.getElementById("survey-email").value.trim(),
            housing_type: document.getElementById("survey-housing-type").value,
            has_other_pets: document.getElementById("survey-has-other-pets").checked,
            lifestyle_description: document.getElementById("survey-lifestyle").value.trim(),
        };

        if (!payload.name || !payload.email || !payload.housing_type || !payload.lifestyle_description) {
            showMessage(message, "Please fill in all required fields.", "error");
            return;
        }

        if (payload.lifestyle_description.length < 150) {
            showMessage(message, "Lifestyle description must be at least 150 characters.", "error");
            return;
        }

        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="spinner"></span> Submitting...`;
        hideMessage(message);

        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/surveys/adopter`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            if (response.ok) {
                const data = await response.json();
                console.log("[SURVEY] Survey submitted:", data);
                showMessage(message, `Survey submitted successfully (ID: ${data.id}). You can now run a match.`, "success");
                form.reset();
                document.getElementById("lifestyle-char-count").textContent = "0 / 1000";
                fetchAllSurveys(); // Refresh the survey dropdown.
            } else {
                const err = await response.json().catch(() => null);
                const detail = err?.detail || `Status ${response.status}`;
                showMessage(message, `Submission failed: ${detail}`, "error");
            }
        } catch (error) {
            showMessage(message, "Could not reach the server. Is the backend running?", "error");
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = "Submit Survey";
        }
    });
}

// ============================================================
// MATCH ENGINE — Fetch surveys, run match, display results
// ============================================================
async function fetchAllSurveys() {
    const select = document.getElementById("match-survey-select");
    if (!select) return;

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/surveys/adopter`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const surveys = await response.json();

        select.innerHTML = "";

        if (surveys.length === 0) {
            select.innerHTML = `<option value="" disabled selected>No surveys yet</option>`;
            return;
        }

        select.innerHTML = `<option value="" disabled selected>Choose a survey...</option>`;
        surveys.forEach(s => {
            const opt = document.createElement("option");
            opt.value = s.id;
            opt.textContent = `#${s.id} — ${s.name} (${s.housing_type})`;
            select.appendChild(opt);
        });

    } catch (error) {
        console.error("[SURVEYS] Failed to fetch surveys:", error.message);
        select.innerHTML = `<option value="" disabled selected>Failed to load</option>`;
    }
}

function initMatchControls() {
    const matchBtn = document.getElementById("run-match-btn");
    const select = document.getElementById("match-survey-select");
    const refreshBtn = document.getElementById("refresh-pets-btn");

    if (matchBtn && select) {
        matchBtn.addEventListener("click", () => {
            const surveyId = parseInt(select.value, 10);
            if (isNaN(surveyId)) {
                alert("Please select a survey first.");
                return;
            }
            runMatch(surveyId);
        });
    }

    if (refreshBtn) {
        refreshBtn.addEventListener("click", fetchAllPets);
    }
}

async function runMatch(surveyId) {
    const grid = document.getElementById("match-results-grid");
    const emptyState = document.getElementById("match-empty-state");
    const matchBtn = document.getElementById("run-match-btn");

    matchBtn.disabled = true;
    matchBtn.innerHTML = `<span class="spinner"></span> Matching...`;
    grid.innerHTML = "";
    emptyState.style.display = "none";

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/recommendations/match`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ survey_id: surveyId }),
        });

        if (!response.ok) {
            const err = await response.json().catch(() => null);
            const detail = err?.detail || `HTTP ${response.status}`;
            alert(`Match failed: ${detail}`);
            emptyState.style.display = "block";
            return;
        }

        const results = await response.json();

        if (results.length === 0) {
            emptyState.innerHTML = `
                <div class="empty-state-icon">🔍</div>
                <p>No matches found. Make sure some pets are activated for matching.</p>
            `;
            emptyState.style.display = "block";
            return;
        }

        results.forEach((match, index) => {
            grid.appendChild(createMatchCard(match, index + 1));
        });

        // Animate score bars after a brief delay so the transition is visible.
        requestAnimationFrame(() => {
            document.querySelectorAll(".score-bar-fill").forEach(bar => {
                bar.style.width = bar.dataset.width;
            });
        });

    } catch (error) {
        alert(`Network error: ${error.message}`);
        emptyState.style.display = "block";
    } finally {
        matchBtn.disabled = false;
        matchBtn.textContent = "Find Matches";
    }
}

function createMatchCard(match, rank) {
    const card = document.createElement("div");
    card.className = "match-card";

    const pet = match.pet;
    const score = match.similarity_score;
    const pct = Math.round(score * 100);
    const description = pet.description || "No description.";

    card.innerHTML = `
        <div class="match-card-header">
            <span class="match-rank">#${rank}</span>
            <span class="match-score-value">${pct}%</span>
        </div>
        <h3 class="match-card-name">${escapeHtml(pet.name)}</h3>
        <p class="match-card-description">${escapeHtml(description)}</p>
        <div class="score-bar-container">
            <div class="score-bar-fill" data-width="${pct}%" style="width: 0%;"></div>
        </div>
    `;

    return card;
}

// ============================================================
// CHARACTER COUNTER — Lifestyle textarea
// ============================================================
function initCharCounter() {
    const textarea = document.getElementById("survey-lifestyle");
    const counter = document.getElementById("lifestyle-char-count");

    if (textarea && counter) {
        textarea.addEventListener("input", () => {
            counter.textContent = `${textarea.value.length} / 1000`;
        });
    }
}

// ============================================================
// FADE-IN OBSERVER — Animate sections on scroll
// ============================================================
function initFadeInObserver() {
    const targets = document.querySelectorAll(".fade-in");

    if (!("IntersectionObserver" in window)) {
        // Fallback: just show everything.
        targets.forEach(t => t.classList.add("visible"));
        return;
    }

    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add("visible");
                    observer.unobserve(entry.target);
                }
            });
        },
        { threshold: 0.15 }
    );

    targets.forEach(t => observer.observe(t));
}

// ============================================================
// UTILITIES
// ============================================================

/**
 * Show a form message with a given type (success / error).
 */
function showMessage(el, text, type) {
    el.textContent = text;
    el.className = `form-message show ${type}`;
}

function hideMessage(el) {
    el.className = "form-message";
    el.textContent = "";
}

/**
 * Basic HTML escaping to prevent XSS from user-submitted content.
 */
function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}
