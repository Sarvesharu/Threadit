"""
Custom HashMap Implementation with Separate Chaining.
Individual College DSA Project - Threadit.
"""

class HashMapNode:
    """Node for separate chaining collision resolution in HashMap."""
    def __init__(self, key, value, next_node=None):
        self.key = key
        self.value = value
        self.next = next_node

    def __repr__(self):
        return f"Node({self.key}: {self.value})"


class HashMap:
    """
    Custom HashMap using an array of buckets and separate chaining (linked list).
    Supports dynamic resizing when load factor exceeds threshold.
    """
    INITIAL_CAPACITY = 16
    LOAD_FACTOR_THRESHOLD = 0.75

    def __init__(self, initial_capacity=None):
        self.capacity = initial_capacity if initial_capacity and initial_capacity > 0 else self.INITIAL_CAPACITY
        self.buckets = [None] * self.capacity
        self.count = 0  # Number of stored key-value pairs

    def _hash(self, key):
        """Compute bucket index using standard hash modulo capacity."""
        return abs(hash(key)) % self.capacity

    def put(self, key, value):
        """
        Insert or update a key-value pair.
        Average Time Complexity: O(1)
        Worst-case Time Complexity: O(n) (hash collisions)
        """
        # Check load factor and resize if needed before insertion
        if (self.count + 1) / self.capacity > self.LOAD_FACTOR_THRESHOLD:
            self.resize(self.capacity * 2)

        index = self._hash(key)
        current = self.buckets[index]

        # Traverse linked list at bucket
        while current is not None:
            if current.key == key:
                current.value = value  # Update existing key
                return
            current = current.next

        # Key not found; insert new node at the head of the chain (O(1))
        new_node = HashMapNode(key, value, next_node=self.buckets[index])
        self.buckets[index] = new_node
        self.count += 1

    def get(self, key, default=None):
        """
        Retrieve value associated with key.
        Average Time Complexity: O(1)
        Worst-case Time Complexity: O(n)
        """
        index = self._hash(key)
        current = self.buckets[index]

        while current is not None:
            if current.key == key:
                return current.value
            current = current.next

        return default

    def delete(self, key):
        """
        Remove key-value pair from map. Returns deleted value, or None if not found.
        Average Time Complexity: O(1)
        Worst-case Time Complexity: O(n)
        """
        index = self._hash(key)
        current = self.buckets[index]
        prev = None

        while current is not None:
            if current.key == key:
                if prev is None:
                    # Removing head node
                    self.buckets[index] = current.next
                else:
                    prev.next = current.next
                self.count -= 1
                return current.value
            prev = current
            current = current.next

        return None

    def contains(self, key):
        """
        Check if key exists in the HashMap.
        Average Time Complexity: O(1)
        """
        return self.get(key, default=None) is not None or self._key_exists(key)

    def _key_exists(self, key):
        """Distinguish between key with None value and missing key."""
        index = self._hash(key)
        current = self.buckets[index]
        while current is not None:
            if current.key == key:
                return True
            current = current.next
        return False

    def resize(self, new_capacity=None):
        """
        Resize bucket array and rehash all existing keys.
        Time Complexity: O(n)
        """
        if new_capacity is None or new_capacity <= self.count:
            new_capacity = max(self.capacity * 2, self.INITIAL_CAPACITY)

        old_buckets = self.buckets
        self.capacity = new_capacity
        self.buckets = [None] * self.capacity
        self.count = 0  # Will be recalculated as we re-insert

        for head in old_buckets:
            current = head
            while current is not None:
                self.put(current.key, current.value)
                current = current.next

    def length(self):
        """Return total number of key-value pairs stored."""
        return self.count

    def __len__(self):
        return self.count

    def __getitem__(self, key):
        val = self.get(key)
        if val is None and not self._key_exists(key):
            raise KeyError(f"Key '{key}' not found in HashMap")
        return val

    def __setitem__(self, key, value):
        self.put(key, value)

    def __delitem__(self, key):
        if not self._key_exists(key):
            raise KeyError(f"Key '{key}' not found in HashMap")
        self.delete(key)

    def __contains__(self, key):
        return self._key_exists(key)

    def keys(self):
        """Return list of all keys in the HashMap."""
        result = []
        for head in self.buckets:
            current = head
            while current is not None:
                result.append(current.key)
                current = current.next
        return result

    def values(self):
        """Return list of all values in the HashMap."""
        result = []
        for head in self.buckets:
            current = head
            while current is not None:
                result.append(current.value)
                current = current.next
        return result

    def items(self):
        """Return list of (key, value) tuples."""
        result = []
        for head in self.buckets:
            current = head
            while current is not None:
                result.append((current.key, current.value))
                current = current.next
        return result

    def clear(self):
        """Reset the HashMap."""
        self.buckets = [None] * self.capacity
        self.count = 0
