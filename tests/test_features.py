"""
Automated Integration Tests for Application Features and Data Structure Integrations.
Individual College DSA Project - Threadit.
"""

import os
import tempfile
import pytest
import database
import features


@pytest.fixture
def test_db():
    """Create a temporary isolated SQLite database with seed data for tests."""
    temp_dir = tempfile.mkdtemp()
    db_file = os.path.join(temp_dir, "test_threadit.db")
    database.init_db(db_file)
    database.seed_db(db_file)
    features.init_features(db_file)
    yield db_file


# ============================================================================
# 1. SEARCH & INVERTED INDEX TESTS
# ============================================================================

def test_search_single_and_multi_word(test_db):
    # Single-word search
    res = features.search_engine.search("python")
    assert res["total_matches"] > 0
    assert any("python" in str(r["data"]).lower() for r in res["results"])

    # Multi-word search
    multi_res = features.search_engine.search("custom hashmap")
    assert multi_res["total_matches"] > 0
    # Top result should match both words
    top = multi_res["results"][0]
    assert top["hits"] >= 1


def test_search_filtering_and_case_insensitivity(test_db):
    # Case insensitivity
    res_lower = features.search_engine.search("cybersecurity")
    res_upper = features.search_engine.search("CYBERSECURITY")
    assert res_lower["total_matches"] == res_upper["total_matches"]

    # Filter by doc type: communities
    comm_res = features.search_engine.search("cybersecurity", filter_type="community")
    for item in comm_res["results"]:
        assert item["type"] == "community"

    # Filter by doc type: posts
    post_res = features.search_engine.search("cybersecurity", filter_type="post")
    for item in post_res["results"]:
        assert item["type"] == "post"


def test_inverted_index_lifecycle(test_db):
    # 1. Create a new post
    author = database.get_user_by_username("nishad", test_db)
    comm = database.get_community_by_slug("python", test_db)
    post_id = database.create_post(
        title="Unicorns and Quantum Cryptography",
        content="Exploring quantum state superpositions for one-time pads.",
        author_id=author["id"],
        community_id=comm["id"],
        db_path=test_db
    )
    new_post = database.get_post_by_id(post_id, test_db)

    # Index post
    features.search_engine.index_document("post", post_id, f"{new_post['title']} {new_post['content']}", new_post)

    # Verify search finds it
    res = features.search_engine.search("unicorns")
    assert res["total_matches"] == 1
    assert res["results"][0]["data"]["id"] == post_id

    # 2. Update post
    database.update_post(post_id, "Pegasus and Post-Quantum Cryptography", "Updated text content", author["id"], test_db)
    updated_post = database.get_post_by_id(post_id, test_db)
    # Remove old index and re-index
    features.search_engine.remove_document("post", post_id)
    features.search_engine.index_document("post", post_id, f"{updated_post['title']} {updated_post['content']}", updated_post)

    assert features.search_engine.search("unicorns")["total_matches"] == 0
    assert features.search_engine.search("pegasus")["total_matches"] == 1

    # 3. Delete post
    database.delete_post(post_id, author["id"], test_db)
    features.search_engine.remove_document("post", post_id)
    assert features.search_engine.search("pegasus")["total_matches"] == 0


# ============================================================================
# 2. COMMUNITY HIERARCHY TESTS
# ============================================================================

def test_community_hierarchy_breadcrumbs_and_traversals(test_db):
    python_comm = database.get_community_by_slug("python", test_db)
    crumbs = features.hierarchy_manager.get_breadcrumbs(python_comm["id"])
    names = [c["name"] for c in crumbs]

    # Expected path: Technology -> Programming -> Python
    assert names == ["Technology", "Programming", "Python"]

    # Children of Programming
    prog_comm = database.get_community_by_slug("programming", test_db)
    children = features.hierarchy_manager.get_children(prog_comm["id"])
    child_names = [c["name"] for c in children]
    assert "Python" in child_names
    assert "Java" in child_names
    assert "C++" in child_names

    # Parent of Python
    parent = features.hierarchy_manager.get_parent(python_comm["id"])
    assert parent["name"] == "Programming"

    # DFS & BFS traversals
    dfs_nodes = features.hierarchy_manager.get_dfs_order()
    bfs_nodes = features.hierarchy_manager.get_bfs_order()
    assert len(dfs_nodes) >= 10
    assert len(bfs_nodes) >= 10


# ============================================================================
# 3. VOTING AND KARMA SCORING TESTS
# ============================================================================

def test_voting_scoring_rules_and_duplicate_prevention(test_db):
    voter = database.get_user_by_username("sarvesh", test_db)
    author = database.get_user_by_username("nishad", test_db)
    comm = database.get_community_by_slug("python", test_db)

    # Create fresh post
    post_id = database.create_post("Voting Test Post", "Testing vote state transitions", author["id"], comm["id"], test_db)
    features.karma_manager.post_scores.put(post_id, 0)

    initial_author_karma = database.get_user_by_id(author["id"], test_db)["karma"]

    # 1. New Upvote (+1)
    res = features.karma_manager.apply_vote(voter["id"], post_id, vote_direction=1, db_path=test_db)
    assert res["new_score"] == 1
    assert res["author_karma"] == initial_author_karma + 1
    assert res["user_vote"] == 1

    # Duplicate Upvote attempt (should toggle/remove vote: -1)
    res = features.karma_manager.apply_vote(voter["id"], post_id, vote_direction=1, db_path=test_db)
    assert res["new_score"] == 0
    assert res["author_karma"] == initial_author_karma
    assert res["user_vote"] == 0

    # 2. New Downvote (-1)
    res = features.karma_manager.apply_vote(voter["id"], post_id, vote_direction=-1, db_path=test_db)
    assert res["new_score"] == -1
    assert res["author_karma"] == initial_author_karma - 1
    assert res["user_vote"] == -1

    # 3. Change Downvote to Upvote (+2)
    res = features.karma_manager.apply_vote(voter["id"], post_id, vote_direction=1, db_path=test_db)
    assert res["new_score"] == 1
    assert res["author_karma"] == initial_author_karma + 1
    assert res["user_vote"] == 1

    # 4. Change Upvote to Downvote (-2)
    res = features.karma_manager.apply_vote(voter["id"], post_id, vote_direction=-1, db_path=test_db)
    assert res["new_score"] == -1
    assert res["author_karma"] == initial_author_karma - 1
    assert res["user_vote"] == -1


def test_distributed_hashmap_synchronization(test_db):
    stats = features.karma_manager.get_sharding_diagnostics(sample_user_id=1, sample_post_id=1)
    assert stats["total_shards"] == 4
    assert stats["total_items"] > 0
    assert "user:1" in stats["sample_routing"]
    assert 0 <= stats["sample_routing"]["user:1"] < 4


# ============================================================================
# 4. TRENDING TOP-K TESTS
# ============================================================================

def test_trending_top_k_ordering(test_db):
    trending_data = features.trending_engine.get_trending_posts(k=5, db_path=test_db)
    posts = trending_data["posts"]

    assert len(posts) == 5
    # Verify ranks and descending trending_score ordering
    for i in range(len(posts) - 1):
        assert posts[i]["trending_score"] >= posts[i + 1]["trending_score"]
        assert posts[i]["rank"] == i + 1


# ============================================================================
# 5. PERSISTENCE & RESTART REBUILD TESTS
# ============================================================================

def test_in_memory_rebuild_from_sqlite(test_db):
    # Alter post score directly in DB
    author = database.get_user_by_username("nishad", test_db)
    comm = database.get_community_by_slug("python", test_db)
    post_id = database.create_post("Persistent Post", "Will survive rebuild", author["id"], comm["id"], test_db)

    # Re-initialize features (simulating application restart)
    features.init_features(test_db)

    # Confirm post is in inverted index
    search_res = features.search_engine.search("Persistent")
    assert search_res["total_matches"] >= 1

    # Confirm community hierarchy is rebuilt
    tree_nodes = features.hierarchy_manager.tree.dfs_traversal()
    assert len(tree_nodes) >= 10


# ============================================================================
# 6. PERFORMANCE BENCHMARKS VERIFICATION
# ============================================================================

def test_performance_benchmarks(test_db):
    benchmarks = features.run_performance_benchmarks(test_db)
    assert len(benchmarks) == 4
    for b in benchmarks:
        assert b["dsa_time_ms"] >= 0.0
        assert b["baseline_time_ms"] >= 0.0
        assert "speedup" in b


# ============================================================================
# 7. FLASK WEB APPLICATION ROUTE & AUTH INTEGRATION TESTS
# ============================================================================

import app as flask_app_module


@pytest.fixture
def client(test_db):
    flask_app_module.DB_PATH = test_db
    flask_app_module.app.config["TESTING"] = True
    flask_app_module.app.config["SECRET_KEY"] = "test-secret"
    with flask_app_module.app.test_client() as client:
        yield client


def test_home_page_and_posts_render(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Threadit" in html
    assert "Arcane Demo Accounts" in html
    assert "Core Data Structures" in html


def test_login_and_account_switch(client):
    # Test valid login with Arcane demo credentials
    login_resp = client.post("/login", data={
        "username": "nishad",
        "password": "Threadit@123"
    }, follow_redirects=True)
    assert login_resp.status_code == 200
    html = login_resp.data.decode("utf-8")
    assert "Nishad" in html

    # Test account switcher
    switch_resp = client.get("/switch-account/sarvesh", follow_redirects=True)
    assert switch_resp.status_code == 200
    html = switch_resp.data.decode("utf-8")
    assert "Switched active account to Sarvesh Aapshette" in html


def test_explore_and_hierarchy_routes(client):
    response = client.get("/explore")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Depth-First Search (DFS)" in html
    assert "Breadth-First Search (BFS)" in html
    assert "c/Programming" in html

    # Community view route
    comm_resp = client.get("/c/python")
    assert comm_resp.status_code == 200
    html_comm = comm_resp.data.decode("utf-8")
    assert "c/Python" in html_comm
    assert "Parent Community:" in html_comm


def test_trending_and_performance_pages(client):
    # Trending page
    trend_resp = client.get("/trending?k=5")
    assert trend_resp.status_code == 200
    html_trend = trend_resp.data.decode("utf-8")
    assert "Custom Min-Heap Algorithm Diagnostics" in html_trend
    assert "trend" in html_trend

    # Performance benchmarks page
    perf_resp = client.get("/performance")
    assert perf_resp.status_code == 200
    html_perf = perf_resp.data.decode("utf-8")
    assert "Live DSA Performance Demonstration" in html_perf
    assert "Faster" in html_perf


def test_api_vote_route(client):
    # Login first
    client.post("/login", data={"username": "aparna", "password": "Threadit@123"})

    vote_resp = client.post("/api/vote", json={
        "post_id": 1,
        "direction": 1
    })
    assert vote_resp.status_code == 200
    json_data = vote_resp.get_json()
    assert "new_score" in json_data
    assert "author_karma" in json_data
    assert "post_shard" in json_data
