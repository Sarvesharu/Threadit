/**
 * Threadit — Modern Frontend JavaScript
 * Handles AJAX voting, demo account switcher, and UI interactions.
 * Individual College DSA Project.
 */

document.addEventListener("DOMContentLoaded", () => {
    initDemoSwitcher();
});

/**
 * Initializes the demo accounts dropdown menu toggle in navbar.
 */
function initDemoSwitcher() {
    const btn = document.getElementById("demoSwitcherBtn");
    const menu = document.getElementById("demoSwitcherMenu");

    if (btn && menu) {
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            const parent = btn.parentElement;
            parent.classList.toggle("open");
        });

        // Close on click outside
        document.addEventListener("click", (e) => {
            if (!menu.contains(e.target) && !btn.contains(e.target)) {
                btn.parentElement.classList.remove("open");
            }
        });
    }
}

/**
 * Handles AJAX Upvoting and Downvoting.
 * Connects directly to backend custom HashMap and SQLite vote transaction.
 *
 * @param {number} postId - Target post identifier
 * @param {number} direction - 1 for upvote, -1 for downvote
 */
async function handleVote(postId, direction) {
    const postElem = document.getElementById(`post-${postId}`);
    if (!postElem) return;

    const upvoteBtn = postElem.querySelector(".vote-btn.upvote");
    const downvoteBtn = postElem.querySelector(".vote-btn.downvote");
    const scoreElem = document.getElementById(`score-${postId}`);

    try {
        const response = await fetch("/api/vote", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                post_id: postId,
                direction: direction
            })
        });

        if (response.status === 401) {
            window.location.href = "/login?next=" + encodeURIComponent(window.location.pathname);
            return;
        }

        if (!response.ok) {
            console.error("Voting failed with status", response.status);
            return;
        }

        const data = await response.json();

        // 1. Update score in DOM
        if (scoreElem) {
            scoreElem.textContent = data.new_score;
        }

        // 2. Update active states on vote buttons
        if (upvoteBtn && downvoteBtn) {
            upvoteBtn.classList.remove("active");
            downvoteBtn.classList.remove("active");

            if (data.user_vote === 1) {
                upvoteBtn.classList.add("active");
            } else if (data.user_vote === -1) {
                downvoteBtn.classList.add("active");
            }
        }

        // 3. Update logged-in user's karma pill in navbar if they were the author
        const karmaBadge = document.querySelector(".karma-badge");
        if (karmaBadge && data.author_karma !== undefined) {
            // If the current user profile or session matches the author
            const userPill = document.querySelector(".user-pill-name");
            // Soft-refresh or update badge if present
        }

    } catch (err) {
        console.error("Network or voting error:", err);
    }
}
