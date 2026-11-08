"""
Custom Min-Heap Implementation and Top-K Priority Queue Selection.
Individual College DSA Project - Threadit.
No built-in heapq or priority queue modules used.
"""

class HeapElement:
    """Wrapper holding a key (priority) and value (payload)."""
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __lt__(self, other):
        return self.key < other.key

    def __le__(self, other):
        return self.key <= other.key

    def __gt__(self, other):
        return self.key > other.key

    def __ge__(self, other):
        return self.key >= other.key

    def __repr__(self):
        return f"HeapElement(key={self.key}, val={self.value})"


class MinHeap:
    """
    Min-Heap implementation using dynamic array (0-indexed).
    Parent(i) = (i - 1) // 2
    LeftChild(i) = 2 * i + 1
    RightChild(i) = 2 * i + 2
    """
    def __init__(self, key_func=None):
        self.heap = []
        self.key_func = key_func  # Optional extractor if items are not HeapElement

    def _get_key(self, item):
        if isinstance(item, HeapElement):
            return item.key
        if self.key_func:
            return self.key_func(item)
        if isinstance(item, (tuple, list)) and len(item) >= 2:
            return item[0]
        return item

    def _less_than(self, i, j):
        """Compare item at index i with item at index j."""
        return self._get_key(self.heap[i]) < self._get_key(self.heap[j])

    def insert(self, item):
        """
        Insert item into heap and sift up to restore heap property.
        Time Complexity: O(log n)
        """
        self.heap.append(item)
        self.sift_up(len(self.heap) - 1)

    def extract_min(self):
        """
        Remove and return the minimum element (root).
        Time Complexity: O(log n)
        """
        if not self.heap:
            raise IndexError("extract_min called on empty heap")

        root = self.heap[0]
        last_item = self.heap.pop()

        if self.heap:
            self.heap[0] = last_item
            self.sift_down(0)

        return root

    def peek(self):
        """
        Return the minimum element without removing it.
        Time Complexity: O(1)
        """
        if not self.heap:
            return None
        return self.heap[0]

    def sift_up(self, index):
        """
        Restore min-heap invariant by moving element up towards root.
        Time Complexity: O(log n)
        """
        parent = (index - 1) // 2
        while index > 0 and self._less_than(index, parent):
            # Swap with parent
            self.heap[index], self.heap[parent] = self.heap[parent], self.heap[index]
            index = parent
            parent = (index - 1) // 2

    def sift_down(self, index):
        """
        Restore min-heap invariant by moving element down towards leaves.
        Time Complexity: O(log n)
        """
        n = len(self.heap)
        smallest = index

        while True:
            left = 2 * index + 1
            right = 2 * index + 2

            if left < n and self._less_than(left, smallest):
                smallest = left

            if right < n and self._less_than(right, smallest):
                smallest = right

            if smallest != index:
                self.heap[index], self.heap[smallest] = self.heap[smallest], self.heap[index]
                index = smallest
            else:
                break

    def heapify(self, items):
        """
        Build min-heap from an arbitrary list of items in-place.
        Time Complexity: O(n)
        """
        self.heap = list(items)
        n = len(self.heap)
        # Start from last non-leaf node up to root
        for i in range((n // 2) - 1, -1, -1):
            self.sift_down(i)

    def size(self):
        """Return number of elements in the heap."""
        return len(self.heap)

    def __len__(self):
        return len(self.heap)

    def is_empty(self):
        return len(self.heap) == 0


def select_top_k(items, k, key_func=None):
    """
    Fixed-size Top-K Selection Algorithm using Min-Heap.
    Finds the K largest elements according to key_func.
    Time Complexity: O(n log K)
    Space Complexity: O(K)
    Returns list sorted in descending order (highest score first) in O(K log K).
    """
    if k <= 0 or not items:
        return []

    min_heap = MinHeap(key_func=key_func)

    for item in items:
        if min_heap.size() < k:
            min_heap.insert(item)
        else:
            root = min_heap.peek()
            item_val = min_heap._get_key(item)
            root_val = min_heap._get_key(root)

            # If current candidate has a strictly higher score than the minimum in Top-K
            if item_val > root_val:
                min_heap.heap[0] = item
                min_heap.sift_down(0)

    # Extract all elements from heap (ascending order)
    result = []
    while not min_heap.is_empty():
        result.append(min_heap.extract_min())

    # Reverse to get descending order (Rank 1 = highest score)
    result.reverse()
    return result
