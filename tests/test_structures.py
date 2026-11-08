"""
Automated Unit Tests for Custom Data Structures.
Individual College DSA Project - Threadit.
"""

import pytest
from structures.hashmap import HashMap
from structures.nary_tree import CommunityNaryTree, CommunityNode
from structures.min_heap import MinHeap, HeapElement, select_top_k
from structures.distributed_hashmap import DistributedHashMap


# ============================================================================
# 1. CUSTOM HASHMAP TESTS
# ============================================================================

def test_hashmap_basic_operations():
    hm = HashMap(initial_capacity=4)
    assert hm.length() == 0
    assert not hm.contains("key1")

    hm.put("key1", "value1")
    assert hm.length() == 1
    assert hm.get("key1") == "value1"
    assert hm.contains("key1")

    # Update existing key
    hm.put("key1", "updated_value")
    assert hm.length() == 1
    assert hm.get("key1") == "updated_value"

    # Default value on missing key
    assert hm.get("non_existent", "default") == "default"


def test_hashmap_collision_and_resizing():
    # Small capacity to force collisions and dynamic resizing
    hm = HashMap(initial_capacity=4)

    # Insert 10 items (load factor 10/4 = 2.5 > 0.75, should trigger resizing)
    for i in range(10):
        hm.put(f"key_{i}", f"val_{i}")

    assert hm.length() == 10
    assert hm.capacity > 4  # Confirms dynamic resizing occurred

    for i in range(10):
        assert hm.get(f"key_{i}") == f"val_{i}"


def test_hashmap_deletion():
    hm = HashMap(initial_capacity=4)
    hm.put("a", 100)
    hm.put("b", 200)
    hm.put("c", 300)

    assert hm.delete("b") == 200
    assert hm.get("b") is None
    assert hm.length() == 2

    # Deleting missing key returns None
    assert hm.delete("non_existent") is None


def test_hashmap_keys_values_items():
    hm = HashMap()
    data = {"alpha": 1, "beta": 2, "gamma": 3}
    for k, v in data.items():
        hm.put(k, v)

    keys = sorted(hm.keys())
    values = sorted(hm.values())
    items = sorted(hm.items(), key=lambda x: x[0])

    assert keys == ["alpha", "beta", "gamma"]
    assert values == [1, 2, 3]
    assert items == [("alpha", 1), ("beta", 2), ("gamma", 3)]


# ============================================================================
# 2. CUSTOM N-ARY TREE TESTS
# ============================================================================

def test_nary_tree_hierarchy_and_breadcrumbs():
    tree = CommunityNaryTree()

    # Add Technology -> Programming -> Python
    tree.add_node(1, "Technology")
    tree.add_node(2, "Programming", parent_id=1)
    tree.add_node(3, "Python", parent_id=2)

    # Fast O(1) node lookup
    python_node = tree.find_node(3)
    assert python_node is not None
    assert python_node.name == "Python"
    assert python_node.parent.name == "Programming"
    assert python_node.parent.parent.name == "Technology"

    # Breadcrumbs
    crumbs = tree.generate_breadcrumbs(3)
    assert len(crumbs) == 3
    assert [c["name"] for c in crumbs] == ["Technology", "Programming", "Python"]


def test_nary_tree_traversals():
    tree = CommunityNaryTree()
    # Tree shape:
    #       1 (Tech)
    #      /        \
    #   2 (Prog)   3 (AI)
    #    /
    #  4 (Python)
    tree.add_node(1, "Tech")
    tree.add_node(2, "Prog", parent_id=1)
    tree.add_node(3, "AI", parent_id=1)
    tree.add_node(4, "Python", parent_id=2)

    dfs_names = [n.name for n in tree.dfs_traversal()]
    # DFS pre-order: Tech, Prog, Python, AI
    assert dfs_names == ["Tech", "Prog", "Python", "AI"]

    bfs_names = [n.name for n in tree.bfs_traversal()]
    # BFS level-order: Tech, Prog, AI, Python
    assert bfs_names == ["Tech", "Prog", "AI", "Python"]


def test_nary_tree_cycle_prevention():
    tree = CommunityNaryTree()
    tree.add_node(1, "Root")
    tree.add_node(2, "Child", parent_id=1)
    tree.add_node(3, "GrandChild", parent_id=2)

    # Attempting to move Root (1) under GrandChild (3) should raise ValueError for cycle
    with pytest.raises(ValueError, match="cycle"):
        tree.move_node(1, 3)

    # Moving with non-existent parent
    with pytest.raises(ValueError, match="Target parent"):
        tree.move_node(2, 999)

    assert tree._would_create_cycle(3, 1) is True
    assert tree._would_create_cycle(1, 3) is False


def test_nary_tree_remove_node():
    tree = CommunityNaryTree()
    tree.add_node(1, "Parent")
    tree.add_node(2, "Middle", parent_id=1)
    tree.add_node(3, "Leaf", parent_id=2)

    # Removing "Middle" should re-parent "Leaf" to "Parent"
    tree.remove_node(2)
    assert tree.find_node(2) is None
    leaf = tree.find_node(3)
    assert leaf.parent.community_id == 1


# ============================================================================
# 3. CUSTOM MIN-HEAP & TOP-K TESTS
# ============================================================================

def test_min_heap_operations():
    heap = MinHeap()
    assert heap.size() == 0
    assert heap.peek() is None

    values = [45, 12, 85, 32, 89, 5, 23]
    for v in values:
        heap.insert(v)

    assert heap.size() == 7
    assert heap.peek() == 5

    # Extraction must yield sorted ascending sequence
    extracted = []
    while not heap.is_empty():
        extracted.append(heap.extract_min())

    assert extracted == sorted(values)


def test_min_heap_heapify():
    raw = [50, 30, 20, 15, 10, 8, 16]
    heap = MinHeap()
    heap.heapify(raw)

    extracted = []
    while not heap.is_empty():
        extracted.append(heap.extract_min())

    assert extracted == sorted(raw)


def test_top_k_selection():
    posts = [
        {"id": 1, "score": 10},
        {"id": 2, "score": 95},
        {"id": 3, "score": 45},
        {"id": 4, "score": 80},
        {"id": 5, "score": 15},
        {"id": 6, "score": 60},
        {"id": 7, "score": 100},
    ]

    top_3 = select_top_k(posts, k=3, key_func=lambda p: p["score"])
    assert len(top_3) == 3
    # Descending order verification
    assert [p["score"] for p in top_3] == [100, 95, 80]
    assert [p["id"] for p in top_3] == [7, 2, 4]


# ============================================================================
# 4. SIMULATED DISTRIBUTED HASHMAP TESTS
# ============================================================================

def test_distributed_hashmap_sharding():
    dhm = DistributedHashMap(num_shards=4)
    assert len(dhm) == 0

    # Insert several keys
    for i in range(20):
        dhm.put(f"user_{i}", f"karma_{i * 10}")

    assert len(dhm) == 20

    for i in range(20):
        assert dhm.get(f"user_{i}") == f"karma_{i * 10}"

    # Shard routing is deterministic
    shard_id1 = dhm.get_shard_id("user_0")
    shard_id2 = dhm.get_shard_id("user_0")
    assert shard_id1 == shard_id2
    assert 0 <= shard_id1 < 4

    # Deletion
    dhm.delete("user_0")
    assert dhm.get("user_0") is None
    assert len(dhm) == 19

    # Verify distribution stats
    stats = dhm.get_distribution_stats()
    assert stats["total_shards"] == 4
    assert stats["total_items"] == 19
    # Verify each shard contains some items
    total_in_shards = sum(s["item_count"] for s in stats["shards"])
    assert total_in_shards == 19
