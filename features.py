"""
Threadit Feature Engine - DSA Integration Layer.
Integrates custom data structures:
1. Custom HashMap & Inverted Index (Search)
2. Custom N-ary Tree (Community Hierarchy)
3. Custom HashMaps & Simulated Distributed HashMap (Karma & Sharded State)
4. Custom Min-Heap / Priority Queue (Trending Posts Top-K)
"""

import re
import string
import time
from datetime import datetime
from structures.hashmap import HashMap
from structures.nary_tree import CommunityNaryTree
from structures.min_heap import select_top_k
from structures.distributed_hashmap import DistributedHashMap
import database


# ============================================================================
# FEATURE 1: REDDIT-STYLE SEARCH (INVERTED INDEX VIA CUSTOM HASHMAP)
# ============================================================================

def tokenize(text):
    """
    Normalize and tokenize text into lowercase word tokens.
    Removes punctuation and filters out empty strings and single characters.
    """
    if not text:
        return []
    # Lowercase and replace punctuation with spaces
    cleaned = re.sub(r'[^\w\s]', ' ', text.lower())
    tokens = [t.strip() for t in cleaned.split() if len(t.strip()) > 1]
    return tokens


class InvertedIndex:
    """
    Full-text Inverted Index implemented using custom HashMap.
    Maps term -> custom HashMap of {doc_id: doc_metadata}.
    Average Lookup Time: O(1) per term.
    """
    def __init__(self):
        # term -> HashMap(doc_key -> dict_info)
        self.index = HashMap()
        # Fast doc registry: doc_key -> original doc item
        self.doc_store = HashMap()

    def _make_key(self, doc_type, doc_id):
        return f"{doc_type}:{doc_id}"

    def index_document(self, doc_type, doc_id, text, payload):
        """
        Tokenize text and add document reference to term posting lists.
        doc_type: 'post', 'community', or 'user'
        """
        doc_key = self._make_key(doc_type, doc_id)
        self.doc_store.put(doc_key, payload)

        tokens = set(tokenize(text))
        for token in tokens:
            postings = self.index.get(token)
            if postings is None:
                postings = HashMap()
                self.index.put(token, postings)
            # Store doc_key in postings HashMap
            postings.put(doc_key, {"type": doc_type, "id": doc_id})

    def remove_document(self, doc_type, doc_id, text=None):
        """
        Remove document from doc_store and all postings lists.
        """
        doc_key = self._make_key(doc_type, doc_id)
        self.doc_store.delete(doc_key)

        if text:
            tokens = set(tokenize(text))
            for token in tokens:
                postings = self.index.get(token)
                if postings:
                    postings.delete(doc_key)
        else:
            # Full scan of index buckets to remove doc_key
            for term in self.index.keys():
                postings = self.index.get(term)
                if postings and postings.contains(doc_key):
                    postings.delete(doc_key)

    def search(self, query_string, filter_type=None):
        """
        Perform case-insensitive multi-word search using custom HashMap inverted index.
        Returns matching records ranked by hit frequency and relevance.
        Complexity: O(m) where m is number of query tokens.
        """
        start_time = time.perf_counter()
        tokens = tokenize(query_string)
        if not tokens:
            return {"results": [], "execution_time_ms": 0.0, "query": query_string, "tokens": []}

        # Count match frequency per document key using custom HashMap
        match_counts = HashMap()

        for token in tokens:
            postings = self.index.get(token)
            if postings is not None:
                for doc_key in postings.keys():
                    meta = postings.get(doc_key)
                    if filter_type and filter_type != "all" and meta["type"] != filter_type:
                        continue
                    current_count = match_counts.get(doc_key, 0)
                    match_counts.put(doc_key, current_count + 1)

        # Collect and rank results
        matched_items = []
        for doc_key in match_counts.keys():
            hits = match_counts.get(doc_key)
            doc_data = self.doc_store.get(doc_key)
            if doc_data:
                matched_items.append({
                    "doc_key": doc_key,
                    "type": doc_key.split(":")[0],
                    "hits": hits,
                    "data": doc_data
                })

        # Sort descending by match hits
        matched_items.sort(key=lambda x: x["hits"], reverse=True)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return {
            "results": matched_items,
            "execution_time_ms": round(elapsed_ms, 4),
            "query": query_string,
            "tokens": tokens,
            "total_matches": len(matched_items)
        }

    def clear(self):
        self.index.clear()
        self.doc_store.clear()


# ============================================================================
# FEATURE 2: COMMUNITY HIERARCHY (N-ARY TREE VIA CUSTOM HASHMAP)
# ============================================================================

class CommunityHierarchyManager:
    """Manages the in-memory N-ary tree representation of communities."""
    def __init__(self):
        self.tree = CommunityNaryTree()

    def build_from_db(self, db_path=None):
        """Populate tree nodes from SQLite records."""
        self.tree.clear()
        comms = database.get_all_communities(db_path)

        # First pass: add all nodes
        for c in comms:
            self.tree.add_node(
                community_id=c["id"],
                name=c["name"],
                parent_id=None,
                metadata={"slug": c["slug"], "description": c["description"]}
            )

        # Second pass: establish parent-child relationships
        for c in comms:
            if c["parent_id"] is not None:
                try:
                    self.tree.move_node(c["id"], c["parent_id"])
                except Exception:
                    pass

    def add_community(self, community_id, name, slug, description, parent_id=None):
        return self.tree.add_node(
            community_id=community_id,
            name=name,
            parent_id=parent_id,
            metadata={"slug": slug, "description": description}
        )

    def get_breadcrumbs(self, community_id):
        return self.tree.generate_breadcrumbs(community_id)

    def get_children(self, community_id):
        nodes = self.tree.get_children(community_id)
        return [{"id": n.community_id, "name": n.name, "metadata": n.metadata} for n in nodes]

    def get_parent(self, community_id):
        p = self.tree.get_parent(community_id)
        return {"id": p.community_id, "name": p.name, "metadata": p.metadata} if p else None

    def get_dfs_order(self):
        return [{"id": n.community_id, "name": n.name, "depth": len(self.tree.generate_breadcrumbs(n.community_id)) - 1}
                for n in self.tree.dfs_traversal()]

    def get_bfs_order(self):
        return [{"id": n.community_id, "name": n.name, "depth": len(self.tree.generate_breadcrumbs(n.community_id)) - 1}
                for n in self.tree.bfs_traversal()]

    def get_hierarchy_tree(self):
        return self.tree.get_full_hierarchy()


# ============================================================================
# FEATURE 3: KARMA SYSTEM & SIMULATED DISTRIBUTED HASHMAP
# ============================================================================

class KarmaManager:
    """
    In-memory state and simulated sharded storage for user karma and post scores.
    Uses custom HashMap for fast local lookups and DistributedHashMap for logical sharding.
    """
    def __init__(self, num_shards=4):
        self.post_scores = HashMap()     # post_id -> score
        self.user_karma = HashMap()      # user_id -> karma
        self.vote_cache = HashMap()      # "user_id:post_id" -> vote_type (-1 or 1)
        self.distributed_store = DistributedHashMap(num_shards=num_shards)

    def build_from_db(self, db_path=None):
        """Synchronize in-memory structures with persistent SQLite records."""
        self.post_scores.clear()
        self.user_karma.clear()
        self.vote_cache.clear()
        self.distributed_store.clear()

        conn = database.get_db_connection(db_path)

        # Load users karma
        users = conn.execute("SELECT id, karma FROM users").fetchall()
        for u in users:
            uid = u["id"]
            k = u["karma"]
            self.user_karma.put(uid, k)
            self.distributed_store.put(f"user:{uid}", k)

        # Load post scores
        posts = conn.execute("SELECT id, score FROM posts").fetchall()
        for p in posts:
            pid = p["id"]
            s = p["score"]
            self.post_scores.put(pid, s)
            self.distributed_store.put(f"post:{pid}", s)

        # Load votes
        votes = conn.execute("SELECT user_id, post_id, vote_type FROM votes").fetchall()
        for v in votes:
            self.vote_cache.put(f"{v['user_id']}:{v['post_id']}", v["vote_type"])

        conn.close()

    def apply_vote(self, user_id, post_id, vote_direction, db_path=None):
        """
        Record vote via atomic database transaction and update in-memory state.
        Maintains consistency across SQLite, custom HashMaps, and DistributedHashMap.
        """
        res = database.record_vote(user_id, post_id, vote_direction, db_path)
        if not res:
            return None

        # Update in-memory HashMaps
        key = f"{user_id}:{post_id}"
        if res["user_vote"] == 0:
            self.vote_cache.delete(key)
        else:
            self.vote_cache.put(key, res["user_vote"])

        self.post_scores.put(post_id, res["new_score"])
        self.user_karma.put(res["author_id"], res["author_karma"])

        # Update Distributed HashMap shards
        post_shard = self.distributed_store.put(f"post:{post_id}", res["new_score"])
        user_shard = self.distributed_store.put(f"user:{res['author_id']}", res["author_karma"])

        res["post_shard"] = post_shard
        res["user_shard"] = user_shard
        return res

    def get_user_karma(self, user_id):
        return self.user_karma.get(user_id, 0)

    def get_post_score(self, post_id):
        return self.post_scores.get(post_id, 0)

    def get_user_vote(self, user_id, post_id):
        return self.vote_cache.get(f"{user_id}:{post_id}", 0)

    def get_sharding_diagnostics(self, sample_user_id=None, sample_post_id=None):
        """Return diagnostic metrics from the DistributedHashMap simulation."""
        stats = self.distributed_store.get_distribution_stats()
        samples = {}
        if sample_user_id is not None:
            samples[f"user:{sample_user_id}"] = self.distributed_store.get_shard_id(f"user:{sample_user_id}")
        if sample_post_id is not None:
            samples[f"post:{sample_post_id}"] = self.distributed_store.get_shard_id(f"post:{sample_post_id}")
        stats["sample_routing"] = samples
        return stats


# ============================================================================
# FEATURE 4: TRENDING POSTS (MIN-HEAP TOP-K PRIORITY QUEUE)
# ============================================================================

def calculate_trending_score(score, upvotes, downvotes, created_at_str):
    """
    Deterministic and reproducible Trending Score Formula:
    Combines net score with time decay based on post age.
    Formula:
        age_in_hours = max(0.1, (now - created_at) in hours)
        gravity = 1.2
        trending_score = (score + 5) / (age_in_hours + 2)^gravity * 100
    Higher scores for recent posts with high net positive engagement.
    """
    try:
        if isinstance(created_at_str, str):
            created_dt = datetime.strptime(created_at_str.split(".")[0], "%Y-%m-%d %H:%M:%S")
        else:
            created_dt = created_at_str
        age_hours = max(0.1, (datetime.now() - created_dt).total_seconds() / 3600.0)
    except Exception:
        age_hours = 1.0

    # Ensure score base is non-negative for logarithm/gravity scaling
    base = max(0, score + 5)
    gravity = 1.2
    trending_score = (base / ((age_hours + 2.0) ** gravity)) * 100.0
    return round(trending_score, 2)


class TrendingEngine:
    """
    Finds top trending posts using custom Min-Heap Top-K selection.
    Time Complexity: O(N log K)
    """
    def __init__(self):
        pass

    def get_trending_posts(self, k=10, db_path=None):
        """
        Process all eligible posts, calculate trending scores, and select Top-K
        using Min-Heap priority queue.
        """
        start_time = time.perf_counter()
        posts = database.get_all_posts(db_path)

        # Compute trending score for each candidate
        candidates = []
        for p in posts:
            score = p["score"]
            t_score = calculate_trending_score(score, p["upvotes"], p["downvotes"], p["created_at"])
            candidate = dict(p)
            candidate["trending_score"] = t_score
            candidates.append(candidate)

        # Execute Top-K selection via custom Min-Heap
        top_k_posts = select_top_k(candidates, k=k, key_func=lambda x: x["trending_score"])

        # Add ranking attribute
        for rank, post in enumerate(top_k_posts, start=1):
            post["rank"] = rank

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return {
            "posts": top_k_posts,
            "k": k,
            "total_candidates": len(candidates),
            "execution_time_ms": round(elapsed_ms, 4)
        }


# ============================================================================
# PERFORMANCE BENCHMARKING ENGINE
# ============================================================================

def run_performance_benchmarks(db_path=None):
    """
    Conduct live benchmarks comparing custom DSA implementations against baseline linear scans.
    Measures execution time with time.perf_counter().
    """
    results = []

    # 1. Inverted Index Search vs Full Text Linear Scan
    posts = database.get_all_posts(db_path)
    search_term = "python"

    # Inverted Index Lookup
    t0 = time.perf_counter()
    index_res = search_engine.search(search_term, filter_type="posts")
    t1 = time.perf_counter()
    index_time_ms = (t1 - t0) * 1000.0

    # Linear Scan baseline
    t0 = time.perf_counter()
    linear_matches = []
    for p in posts:
        if search_term in (p["title"] + " " + p["content"]).lower():
            linear_matches.append(p["id"])
    t1 = time.perf_counter()
    linear_time_ms = (t1 - t0) * 1000.0

    results.append({
        "name": "Full-Text Search (Inverted Index vs Linear Scan)",
        "dataset_size": len(posts),
        "dsa_operation": "Inverted Index (Custom HashMap)",
        "dsa_complexity": "O(m) where m = query tokens (Average O(1) per term)",
        "dsa_time_ms": round(index_time_ms, 5),
        "baseline_operation": "Sequential Linear Scan across all posts",
        "baseline_complexity": "O(N * L) where N = posts, L = text length",
        "baseline_time_ms": round(linear_time_ms, 5),
        "speedup": round(linear_time_ms / max(0.00001, index_time_ms), 2)
    })

    # 2. Custom HashMap Lookup vs Linear Array Search
    test_keys = [f"key_{i}" for i in range(1000)]
    hm = HashMap()
    arr = []
    for k in test_keys:
        hm.put(k, f"val_{k}")
        arr.append((k, f"val_{k}"))

    target_key = "key_888"

    # HashMap lookup
    t0 = time.perf_counter()
    for _ in range(100):
        _ = hm.get(target_key)
    t1 = time.perf_counter()
    hm_time_ms = ((t1 - t0) / 100.0) * 1000.0

    # Linear array search
    t0 = time.perf_counter()
    for _ in range(100):
        for k, v in arr:
            if k == target_key:
                break
    t1 = time.perf_counter()
    linear_arr_ms = ((t1 - t0) / 100.0) * 1000.0

    results.append({
        "name": "Key-Value Retrieval (Custom HashMap vs Linear Array Scan)",
        "dataset_size": 1000,
        "dsa_operation": "Custom HashMap Separate Chaining Lookup",
        "dsa_complexity": "Average O(1), Worst O(n)",
        "dsa_time_ms": round(hm_time_ms, 5),
        "baseline_operation": "Sequential Array Traversal",
        "baseline_complexity": "O(n)",
        "baseline_time_ms": round(linear_arr_ms, 5),
        "speedup": round(linear_arr_ms / max(0.00001, hm_time_ms), 2)
    })

    # 3. Community ID Lookup (HashMap O(1) vs Tree Traversal O(V))
    target_id = 10
    # HashMap lookup in tree node map
    t0 = time.perf_counter()
    for _ in range(100):
        _ = hierarchy_manager.tree.find_node(target_id)
    t1 = time.perf_counter()
    tree_hash_ms = ((t1 - t0) / 100.0) * 1000.0

    # DFS traversal search
    t0 = time.perf_counter()
    for _ in range(100):
        for node in hierarchy_manager.tree.dfs_traversal():
            if node.community_id == target_id:
                break
    t1 = time.perf_counter()
    tree_dfs_ms = ((t1 - t0) / 100.0) * 1000.0

    results.append({
        "name": "Community Node Resolution (HashMap vs Tree DFS Traversal)",
        "dataset_size": len(hierarchy_manager.tree.node_map),
        "dsa_operation": "HashMap Node Index Lookup",
        "dsa_complexity": "O(1)",
        "dsa_time_ms": round(tree_hash_ms, 5),
        "baseline_operation": "DFS Tree Traversal Search",
        "baseline_complexity": "O(V + E)",
        "baseline_time_ms": round(tree_dfs_ms, 5),
        "speedup": round(tree_dfs_ms / max(0.00001, tree_hash_ms), 2)
    })

    # 4. Top-K Selection: Min-Heap vs Full Sorting
    k = 5
    simulated_candidates = [{"id": i, "score": (i * 37) % 500} for i in range(2000)]

    # Min-Heap Top-K
    t0 = time.perf_counter()
    _ = select_top_k(simulated_candidates, k=k, key_func=lambda x: x["score"])
    t1 = time.perf_counter()
    heap_time_ms = (t1 - t0) * 1000.0

    # Full Sort
    t0 = time.perf_counter()
    sorted_all = sorted(simulated_candidates, key=lambda x: x["score"], reverse=True)[:k]
    t1 = time.perf_counter()
    sort_time_ms = (t1 - t0) * 1000.0

    results.append({
        "name": f"Top-{k} Selection from 2,000 Candidates (Min-Heap vs Full Sort)",
        "dataset_size": 2000,
        "dsa_operation": "Custom Min-Heap Top-K Selection",
        "dsa_complexity": "O(N log K) + O(K log K)",
        "dsa_time_ms": round(heap_time_ms, 5),
        "baseline_operation": "Full In-Memory Sort of all N elements",
        "baseline_complexity": "O(N log N)",
        "baseline_time_ms": round(sort_time_ms, 5),
        "speedup": round(sort_time_ms / max(0.00001, heap_time_ms), 2)
    })

    return results


# Global singleton feature engines
search_engine = InvertedIndex()
hierarchy_manager = CommunityHierarchyManager()
karma_manager = KarmaManager(num_shards=4)
trending_engine = TrendingEngine()


def init_features(db_path=None):
    """
    Initialize all in-memory custom data structures from the SQLite database.
    Called on Flask application boot.
    """
    # 1. Initialize SQLite database and seed demo data if needed
    database.seed_db(db_path)

    # 2. Build Inverted Index
    search_engine.clear()
    posts = database.get_all_posts(db_path)
    for p in posts:
        search_engine.index_document(
            doc_type="post",
            doc_id=p["id"],
            text=f"{p['title']} {p['content']}",
            payload=p
        )

    communities = database.get_all_communities(db_path)
    for c in communities:
        search_engine.index_document(
            doc_type="community",
            doc_id=c["id"],
            text=f"{c['name']} {c['description']} {c['slug']}",
            payload=c
        )

    conn = database.get_db_connection(db_path)
    users = conn.execute("SELECT id, username, display_name, bio FROM users").fetchall()
    for u in users:
        u_dict = dict(u)
        search_engine.index_document(
            doc_type="user",
            doc_id=u_dict["id"],
            text=f"{u_dict['username']} {u_dict['display_name']} {u_dict['bio']}",
            payload=u_dict
        )
    conn.close()

    # 3. Build Community Hierarchy Tree
    hierarchy_manager.build_from_db(db_path)

    # 4. Build Karma & Distributed HashMaps
    karma_manager.build_from_db(db_path)
