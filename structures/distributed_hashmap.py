"""
Simulated Distributed HashMap with Logical Sharding.
Individual College DSA Project - Threadit.

NOTE ON LOGICAL SHARDING VS DISTRIBUTED INFRASTRUCTURE:
This module simulates distributed key partitioning in a single process.
In a real production distributed system (e.g., Redis Cluster, Cassandra, DynamoDB),
each shard resides on separate physical/virtual server nodes communicating via RPC
over a network, utilizing consistent hashing rings, active replication, data rebalancing,
and consensus protocols (Paxos/Raft).
This simulation cleanly models the key partitioning, hash-based shard routing, and isolated
shard storage semantics without requiring multi-node deployment.
"""

from structures.hashmap import HashMap


class DistributedHashMap:
    """
    Simulated Distributed Key-Value Store.
    Partitions keys across N logical shards, where each shard is an isolated
    instance of our custom HashMap.
    """
    def __init__(self, num_shards=4):
        if num_shards < 1:
            raise ValueError("Number of shards must be at least 1")
        self.num_shards = num_shards
        # Each shard is an independent custom HashMap
        self.shards = [HashMap() for _ in range(num_shards)]

    def get_shard_id(self, key):
        """
        Deterministic shard routing function.
        Determines which logical shard owns the given key.
        Time Complexity: O(1)
        """
        return abs(hash(str(key))) % self.num_shards

    def _get_shard(self, key):
        """Internal helper returning shard ID and shard instance."""
        shard_id = self.get_shard_id(key)
        return shard_id, self.shards[shard_id]

    def put(self, key, value):
        """
        Store a key-value pair in its routed shard.
        Time Complexity: O(1) average
        """
        shard_id, shard = self._get_shard(key)
        shard.put(key, value)
        return shard_id

    def get(self, key, default=None):
        """
        Retrieve value from the responsible shard.
        Time Complexity: O(1) average
        """
        _, shard = self._get_shard(key)
        return shard.get(key, default)

    def delete(self, key):
        """
        Remove key-value pair from its shard.
        Time Complexity: O(1) average
        """
        _, shard = self._get_shard(key)
        return shard.delete(key)

    def contains(self, key):
        """Check if key exists in its shard."""
        _, shard = self._get_shard(key)
        return shard.contains(key)

    def length(self):
        """Total number of items across all shards."""
        return sum(shard.length() for shard in self.shards)

    def __len__(self):
        return self.length()

    def get_distribution_stats(self):
        """
        Diagnostic report showing key distribution across all shards.
        Useful for demonstrating partition balance and hash uniformity.
        """
        total = self.length()
        stats = []
        for i, shard in enumerate(self.shards):
            count = shard.length()
            pct = (count / total * 100.0) if total > 0 else 0.0
            stats.append({
                "shard_id": i,
                "item_count": count,
                "percentage": round(pct, 2),
                "keys_sample": shard.keys()[:5]  # first few keys as preview
            })
        return {
            "total_shards": self.num_shards,
            "total_items": total,
            "shards": stats
        }

    def clear(self):
        """Reset all shards."""
        for shard in self.shards:
            shard.clear()
