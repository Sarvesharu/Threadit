"""
Custom N-ary Tree Implementation for Community Hierarchy.
Individual College DSA Project - Threadit.
"""

from structures.hashmap import HashMap


class CommunityNode:
    """Represents a community node in the N-ary tree."""
    def __init__(self, community_id, name, parent=None, metadata=None):
        self.community_id = community_id
        self.name = name
        self.parent = parent  # Reference to parent CommunityNode
        self.children = []    # List of child CommunityNodes
        self.metadata = metadata if metadata is not None else {}

    def add_child(self, child_node):
        """Link a child node to this node."""
        child_node.parent = self
        self.children.append(child_node)

    def remove_child(self, child_id):
        """Remove a child by its community ID."""
        for i, child in enumerate(self.children):
            if child.community_id == child_id:
                child.parent = None
                return self.children.pop(i)
        return None

    def to_dict(self):
        """Serialize node structure for UI rendering and hierarchy display."""
        return {
            "id": self.community_id,
            "name": self.name,
            "metadata": self.metadata,
            "children": [child.to_dict() for child in self.children]
        }

    def __repr__(self):
        return f"CommunityNode(id={self.community_id}, name='{self.name}', children={len(self.children)})"


class CommunityNaryTree:
    """
    N-ary Tree managing the hierarchical community structure.
    Uses a custom HashMap to provide O(1) node lookup by community ID.
    Supports DFS, BFS, breadcrumb generation, and cycle prevention.
    """
    def __init__(self):
        self.roots = []  # List of root CommunityNodes (communities without parents)
        self.node_map = HashMap()  # community_id -> CommunityNode for O(1) lookup

    def add_node(self, community_id, name, parent_id=None, metadata=None):
        """
        Add a community node to the tree.
        If parent_id is None, it becomes a root node.
        Includes cycle prevention if parent is specified.
        Average Time Complexity: O(1) with HashMap lookup.
        """
        # Check if node already exists
        existing = self.node_map.get(community_id)
        if existing:
            # Update metadata/name
            existing.name = name
            if metadata:
                existing.metadata.update(metadata)
            return existing

        # Cycle prevention check if parent_id is given
        if parent_id is not None:
            if not self.node_map.contains(parent_id):
                raise ValueError(f"Parent community ID {parent_id} does not exist.")
            if self._would_create_cycle(parent_id, community_id):
                raise ValueError(f"Adding community {community_id} under {parent_id} would create a cycle.")

        node = CommunityNode(community_id, name, metadata=metadata)
        self.node_map.put(community_id, node)

        if parent_id is None:
            self.roots.append(node)
        else:
            parent_node = self.node_map.get(parent_id)
            parent_node.add_child(node)

        return node

    def add_child(self, parent_id, child_node):
        """Direct method to add a child node to an existing parent."""
        if self._would_create_cycle(parent_id, child_node.community_id):
            raise ValueError("Adding this child would introduce a cycle.")

        parent_node = self.find_node(parent_id)
        if not parent_node:
            raise ValueError(f"Parent with ID {parent_id} not found.")

        parent_node.add_child(child_node)
        self.node_map.put(child_node.community_id, child_node)
        if child_node in self.roots:
            self.roots.remove(child_node)

    def move_node(self, node_id, new_parent_id):
        """
        Move an existing node to a new parent, with cycle detection.
        Time Complexity: O(h)
        """
        node = self.find_node(node_id)
        if not node:
            raise ValueError(f"Node {node_id} does not exist.")

        if new_parent_id is not None:
            new_parent = self.find_node(new_parent_id)
            if not new_parent:
                raise ValueError(f"Target parent {new_parent_id} does not exist.")
            if self._would_create_cycle(new_parent_id, node_id):
                raise ValueError(f"Moving node {node_id} under {new_parent_id} would create a cycle.")

        # Detach from current parent or roots
        if node.parent:
            node.parent.remove_child(node_id)
        elif node in self.roots:
            self.roots.remove(node)

        # Attach to new parent or roots
        if new_parent_id is None:
            node.parent = None
            self.roots.append(node)
        else:
            new_parent = self.find_node(new_parent_id)
            new_parent.add_child(node)
        return node

    def find_node(self, community_id):
        """
        Retrieve community node in O(1) average time via custom HashMap.
        """
        return self.node_map.get(community_id)

    def get_parent(self, community_id):
        """Return parent CommunityNode of specified community ID, or None."""
        node = self.find_node(community_id)
        return node.parent if node else None

    def get_children(self, community_id):
        """Return list of child CommunityNodes."""
        node = self.find_node(community_id)
        return node.children if node else []

    def remove_node(self, community_id):
        """
        Remove a community node and re-parent its children to the node's parent (or roots).
        """
        node = self.find_node(community_id)
        if not node:
            return None

        parent = node.parent
        # Re-attach children to parent or roots
        if parent:
            parent.remove_child(community_id)
            for child in node.children:
                parent.add_child(child)
        else:
            if node in self.roots:
                self.roots.remove(node)
            for child in node.children:
                child.parent = None
                self.roots.append(child)

        self.node_map.delete(community_id)
        return node

    def _would_create_cycle(self, candidate_parent_id, node_id):
        """
        Cycle check: verifies candidate_parent is not a descendant of node_id.
        Time Complexity: O(h) where h is tree height.
        """
        curr_id = candidate_parent_id
        while curr_id is not None:
            if curr_id == node_id:
                return True
            parent_node = self.get_parent(curr_id)
            curr_id = parent_node.community_id if parent_node else None
        return False

    def generate_breadcrumbs(self, community_id):
        """
        Generate path from root to current community.
        Returns list of (id, name) tuples.
        Time Complexity: O(h) where h is tree depth.
        """
        node = self.find_node(community_id)
        if not node:
            return []

        path = []
        curr = node
        while curr is not None:
            path.append({"id": curr.community_id, "name": curr.name})
            curr = curr.parent

        path.reverse()  # from root to target node
        return path

    def dfs_traversal(self, start_id=None):
        """
        Depth-First Search traversal.
        Yields CommunityNode objects in pre-order.
        Time Complexity: O(V + E)
        """
        result = []

        def _dfs(node):
            result.append(node)
            for child in node.children:
                _dfs(child)

        if start_id is not None:
            start_node = self.find_node(start_id)
            if start_node:
                _dfs(start_node)
        else:
            for root in self.roots:
                _dfs(root)

        return result

    def bfs_traversal(self, start_id=None):
        """
        Breadth-First Search traversal (level-order).
        Yields CommunityNode objects level by level.
        Time Complexity: O(V + E)
        """
        result = []
        queue = []

        if start_id is not None:
            start_node = self.find_node(start_id)
            if start_node:
                queue.append(start_node)
        else:
            for root in self.roots:
                queue.append(root)

        head = 0
        while head < len(queue):
            current = queue[head]
            head += 1
            result.append(current)
            for child in current.children:
                queue.append(child)

        return result

    def get_full_hierarchy(self):
        """Return serialized list of all root trees for UI display."""
        return [root.to_dict() for root in self.roots]

    def clear(self):
        """Clear all nodes from the tree."""
        self.roots = []
        self.node_map.clear()
