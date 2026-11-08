"""
Threadit - Reddit-Inspired Social Media Application.
Individual College DSA Project.
Flask Application, Routes, Authentication, and Session Management.
"""

import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import database
import features

app = Flask(__name__)
app.secret_key = os.environ.get("THREADIT_SECRET_KEY", "threadit_dsa_secret_key_arcane_2026")

# Database path
DB_PATH = database.DEFAULT_DB_PATH


# Initialize features and in-memory data structures on app start
with app.app_context():
    features.init_features(DB_PATH)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@app.context_processor
def inject_global_data():
    """Inject user information, demo accounts, and communities into all templates."""
    current_user = None
    if "user_id" in session:
        current_user = database.get_user_by_id(session["user_id"], DB_PATH)
        # Update karma from in-memory cache if available
        if current_user:
            current_user = dict(current_user)
            cached_karma = features.karma_manager.get_user_karma(current_user["id"])
            if cached_karma is not None:
                current_user["karma"] = cached_karma

    all_comms = database.get_all_communities(DB_PATH)
    return {
        "current_user": current_user,
        "demo_accounts": database.DEMO_ACCOUNTS,
        "global_communities": all_comms
    }


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")

        user = database.get_user_by_username(username, DB_PATH)
        if user and database.check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["display_name"] = user["display_name"]
            flash(f"Welcome back, {user['display_name']}!", "success")
            next_url = request.args.get("next") or url_for("index")
            return redirect(next_url)
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        display_name = request.form.get("display_name", "").strip()
        password = request.form.get("password", "")
        bio = request.form.get("bio", "").strip()

        if not username or not display_name or not password:
            flash("Username, Display Name, and Password are required.", "danger")
            return render_template("login.html", is_register=True)

        user_id = database.create_user(username, display_name, password, bio, DB_PATH)
        if user_id:
            user = database.get_user_by_id(user_id, DB_PATH)
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["display_name"] = user["display_name"]

            # Update in-memory index & karma
            features.search_engine.index_document(
                "user", user["id"],
                f"{user['username']} {user['display_name']} {user['bio']}",
                dict(user)
            )
            features.karma_manager.user_karma.put(user["id"], 0)
            features.karma_manager.distributed_store.put(f"user:{user['id']}", 0)

            flash("Account created successfully! Welcome to Threadit.", "success")
            return redirect(url_for("index"))
        else:
            flash("Username already taken. Please pick another.", "danger")

    return render_template("login.html", is_register=True)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/switch-account/<username>", methods=["GET", "POST"])
def switch_account(username):
    """Convenience feature for live college exhibition: instantaneous account switching."""
    user = database.get_user_by_username(username.lower().strip(), DB_PATH)
    if user:
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["display_name"] = user["display_name"]
        flash(f"Switched active account to {user['display_name']} (@{user['username']})", "success")
    else:
        flash("Target demo account not found.", "danger")
    return redirect(request.referrer or url_for("index"))


# ============================================================================
# MAIN APPLICATION & POST ROUTES
# ============================================================================

@app.route("/")
def index():
    posts = database.get_all_posts(DB_PATH)
    # Attach current user's vote state from in-memory cache
    current_uid = session.get("user_id")
    for p in posts:
        p["score"] = features.karma_manager.get_post_score(p["id"]) or p["score"]
        p["user_vote"] = features.karma_manager.get_user_vote(current_uid, p["id"]) if current_uid else 0

    trending_data = features.trending_engine.get_trending_posts(k=5, db_path=DB_PATH)
    return render_template("index.html", posts=posts, trending_posts=trending_data["posts"])


@app.route("/post/create", methods=["POST"])
@login_required
def create_post():
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    community_id = request.form.get("community_id", type=int)

    if not title or not content or not community_id:
        flash("Title, content, and community selection are required.", "danger")
        return redirect(url_for("index"))

    post_id = database.create_post(title, content, session["user_id"], community_id, DB_PATH)
    new_post = database.get_post_by_id(post_id, DB_PATH)

    # 1. Update in-memory inverted index
    features.search_engine.index_document(
        "post", post_id, f"{title} {content}", new_post
    )
    # 2. Update in-memory score tracking
    features.karma_manager.post_scores.put(post_id, 0)
    features.karma_manager.distributed_store.put(f"post:{post_id}", 0)

    flash("Post created successfully!", "success")
    return redirect(url_for("view_post", post_id=post_id))


@app.route("/post/<int:post_id>")
def view_post(post_id):
    post = database.get_post_by_id(post_id, DB_PATH)
    if not post:
        flash("Post not found.", "danger")
        return redirect(url_for("index"))

    current_uid = session.get("user_id")
    post["score"] = features.karma_manager.get_post_score(post["id"]) or post["score"]
    post["user_vote"] = features.karma_manager.get_user_vote(current_uid, post["id"]) if current_uid else 0

    # Get community breadcrumbs
    breadcrumbs = features.hierarchy_manager.get_breadcrumbs(post["community_id"])
    return render_template("post.html", post=post, breadcrumbs=breadcrumbs)


@app.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = database.get_post_by_id(post_id, DB_PATH)
    if not post:
        flash("Post not found.", "danger")
        return redirect(url_for("index"))

    if post["author_id"] != session["user_id"]:
        flash("Unauthorized: You can only edit your own posts.", "danger")
        return redirect(url_for("view_post", post_id=post_id))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        if not title or not content:
            flash("Title and content cannot be empty.", "danger")
            return render_template("post.html", post=post, is_editing=True)

        database.update_post(post_id, title, content, session["user_id"], DB_PATH)
        updated_post = database.get_post_by_id(post_id, DB_PATH)

        # Update in-memory inverted index
        features.search_engine.remove_document("post", post_id)
        features.search_engine.index_document("post", post_id, f"{title} {content}", updated_post)

        flash("Post updated successfully!", "success")
        return redirect(url_for("view_post", post_id=post_id))

    return render_template("post.html", post=post, is_editing=True)


@app.route("/post/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    post = database.get_post_by_id(post_id, DB_PATH)
    if not post:
        flash("Post not found.", "danger")
        return redirect(url_for("index"))

    if post["author_id"] != session["user_id"]:
        flash("Unauthorized: You can only delete your own posts.", "danger")
        return redirect(url_for("view_post", post_id=post_id))

    database.delete_post(post_id, session["user_id"], DB_PATH)

    # Clean in-memory inverted index and scores
    features.search_engine.remove_document("post", post_id)
    features.karma_manager.post_scores.delete(post_id)
    features.karma_manager.distributed_store.delete(f"post:{post_id}")

    flash("Post deleted successfully.", "info")
    return redirect(url_for("index"))


# ============================================================================
# COMMUNITY & HIERARCHY ROUTES
# ============================================================================

@app.route("/c/<slug>")
def view_community(slug):
    comm = database.get_community_by_slug(slug, DB_PATH)
    if not comm:
        flash("Community not found.", "danger")
        return redirect(url_for("index"))

    breadcrumbs = features.hierarchy_manager.get_breadcrumbs(comm["id"])
    children = features.hierarchy_manager.get_children(comm["id"])
    parent = features.hierarchy_manager.get_parent(comm["id"])

    # Community posts
    conn = database.get_db_connection(DB_PATH)
    posts = conn.execute("""
        SELECT p.*, u.username as author_username, u.display_name as author_display_name,
               c.name as community_name, c.slug as community_slug
        FROM posts p
        JOIN users u ON p.author_id = u.id
        JOIN communities c ON p.community_id = c.id
        WHERE p.community_id = ?
        ORDER BY p.created_at DESC
    """, (comm["id"],)).fetchall()
    conn.close()

    posts_list = [dict(p) for p in posts]
    current_uid = session.get("user_id")
    for p in posts_list:
        p["score"] = features.karma_manager.get_post_score(p["id"]) or p["score"]
        p["user_vote"] = features.karma_manager.get_user_vote(current_uid, p["id"]) if current_uid else 0

    return render_template(
        "community.html",
        community=comm,
        breadcrumbs=breadcrumbs,
        children=children,
        parent=parent,
        posts=posts_list
    )


@app.route("/communities")
@app.route("/explore")
def explore_communities():
    """Visual community hierarchy explorer demonstrating DFS and BFS tree traversal."""
    hierarchy = features.hierarchy_manager.get_hierarchy_tree()
    dfs_nodes = features.hierarchy_manager.get_dfs_order()
    bfs_nodes = features.hierarchy_manager.get_bfs_order()
    return render_template(
        "community.html",
        is_explorer=True,
        hierarchy=hierarchy,
        dfs_nodes=dfs_nodes,
        bfs_nodes=bfs_nodes
    )


# ============================================================================
# SEARCH ROUTE
# ============================================================================

@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    filter_type = request.args.get("type", "all")

    if not query:
        return render_template("search.html", results=None, query="")

    search_result = features.search_engine.search(query, filter_type=filter_type)
    return render_template(
        "search.html",
        results=search_result["results"],
        query=query,
        filter_type=filter_type,
        execution_time_ms=search_result["execution_time_ms"],
        total_matches=search_result["total_matches"],
        tokens=search_result["tokens"]
    )


# ============================================================================
# TRENDING ROUTE
# ============================================================================

@app.route("/trending")
def trending():
    k = request.args.get("k", default=10, type=int)
    k = max(1, min(k, 50))  # Bounds check
    data = features.trending_engine.get_trending_posts(k=k, db_path=DB_PATH)
    return render_template(
        "trending.html",
        posts=data["posts"],
        k=k,
        total_candidates=data["total_candidates"],
        execution_time_ms=data["execution_time_ms"]
    )


# ============================================================================
# USER PROFILE ROUTE
# ============================================================================

@app.route("/u/<username>")
def view_profile(username):
    user = database.get_user_by_username(username.lower().strip(), DB_PATH)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("index"))

    user_dict = dict(user)
    # In-memory karma and sharding
    user_dict["karma"] = features.karma_manager.get_user_karma(user["id"])
    shard_id = features.karma_manager.distributed_store.get_shard_id(f"user:{user['id']}")

    conn = database.get_db_connection(DB_PATH)
    user_posts = conn.execute("""
        SELECT p.*, c.name as community_name, c.slug as community_slug,
               u.username as author_username, u.display_name as author_display_name
        FROM posts p
        JOIN communities c ON p.community_id = c.id
        JOIN users u ON p.author_id = u.id
        WHERE p.author_id = ?
        ORDER BY p.created_at DESC
    """, (user["id"],)).fetchall()
    conn.close()

    posts_list = [dict(p) for p in user_posts]
    current_uid = session.get("user_id")
    for p in posts_list:
        p["score"] = features.karma_manager.get_post_score(p["id"]) or p["score"]
        p["user_vote"] = features.karma_manager.get_user_vote(current_uid, p["id"]) if current_uid else 0

    # Get sharding diagnostic stats
    sharding_stats = features.karma_manager.get_sharding_diagnostics(sample_user_id=user["id"])

    return render_template(
        "profile.html",
        profile_user=user_dict,
        user_shard_id=shard_id,
        posts=posts_list,
        sharding_stats=sharding_stats
    )


# ============================================================================
# AJAX & PERFORMANCE API ROUTES
# ============================================================================

@app.route("/api/vote", methods=["POST"])
def api_vote():
    if "user_id" not in session:
        return jsonify({"error": "Authentication required"}), 401

    data = request.get_json() or {}
    post_id = data.get("post_id")
    direction = data.get("direction")

    if post_id is None or direction not in (-1, 0, 1):
        return jsonify({"error": "Invalid vote payload"}), 400

    try:
        res = features.karma_manager.apply_vote(session["user_id"], int(post_id), int(direction), DB_PATH)
        if not res:
            return jsonify({"error": "Post not found"}), 404
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/performance")
@app.route("/benchmarks")
def performance_page():
    """Live performance comparison page showcasing custom DSA vs baseline scans."""
    benchmarks = features.run_performance_benchmarks(DB_PATH)
    return render_template("trending.html", is_benchmark=True, benchmarks=benchmarks)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
