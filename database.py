"""
SQLite Database Connection, Schema, and Seed Logic.
Individual College DSA Project - Threadit.
"""

import os
import sqlite3
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "threadit.db")


def get_db_connection(db_path=None):
    """Create and return a configured SQLite database connection."""
    path = db_path or DEFAULT_DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path=None):
    """Initialize database tables, foreign keys, and indexes."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        display_name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        karma INTEGER DEFAULT 0,
        bio TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS communities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        description TEXT DEFAULT '',
        parent_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parent_id) REFERENCES communities (id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        author_id INTEGER NOT NULL,
        community_id INTEGER NOT NULL,
        score INTEGER DEFAULT 0,
        upvotes INTEGER DEFAULT 0,
        downvotes INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (author_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (community_id) REFERENCES communities (id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        post_id INTEGER NOT NULL,
        vote_type INTEGER NOT NULL CHECK (vote_type IN (-1, 1)),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (user_id, post_id),
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_posts_community ON posts (community_id);
    CREATE INDEX IF NOT EXISTS idx_posts_author ON posts (author_id);
    CREATE INDEX IF NOT EXISTS idx_votes_user_post ON votes (user_id, post_id);
    CREATE INDEX IF NOT EXISTS idx_communities_parent ON communities (parent_id);
    """)

    conn.commit()
    conn.close()


# 8 Ready-made Arcane Demo Accounts
DEMO_ACCOUNTS = [
    {"display_name": "Nishad Remane", "username": "nishad", "bio": "Software architect & systems enthusiast. Exploring algorithms."},
    {"display_name": "Sarvesh Aapshette", "username": "sarvesh", "bio": "Competitive programmer & Python developer."},
    {"display_name": "Aparna Patre", "username": "aparna", "bio": "Data science and AI researcher. Building intelligent models."},
    {"display_name": "Saurav Nikam", "username": "saurav", "bio": "Cybersecurity researcher & ethical hacker."},
    {"display_name": "Alok Hibare", "username": "alok", "bio": "Full-stack developer & open-source contributor."},
    {"display_name": "Vedika Patil", "username": "vedika", "bio": "Digital forensics investigator & security analyst."},
    {"display_name": "Athravsingh Ingle", "username": "athravsingh", "bio": "Cloud and distributed systems engineer."},
    {"display_name": "Kusum Choudhary", "username": "kusum", "bio": "Machine learning engineer & NLP enthusiast."}
]

DEMO_PASSWORD = "Threadit@123"


def seed_db(db_path=None):
    """
    Idempotent database seeding.
    Inserts demo users, community hierarchy, sample posts, and initial votes.
    Running multiple times will not duplicate records.
    """
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # 1. Seed Demo Accounts
    password_hash = generate_password_hash(DEMO_PASSWORD)
    user_map = {}  # username -> id

    for acc in DEMO_ACCOUNTS:
        cursor.execute("SELECT id FROM users WHERE username = ?", (acc["username"],))
        row = cursor.fetchone()
        if row:
            user_map[acc["username"]] = row["id"]
        else:
            cursor.execute(
                "INSERT INTO users (username, display_name, password_hash, bio) VALUES (?, ?, ?, ?)",
                (acc["username"], acc["display_name"], password_hash, acc["bio"])
            )
            user_map[acc["username"]] = cursor.lastrowid

    # 2. Seed Communities Hierarchy
    # Technology
    # ├── Programming
    # │   ├── Python
    # │   ├── Java
    # │   └── C++
    # ├── Cybersecurity
    # │   ├── EthicalHacking
    # │   └── DigitalForensics
    # └── ArtificialIntelligence
    #     ├── MachineLearning
    #     └── GenerativeAI
    # OpenSource (Root)
    communities_spec = [
        # Root communities
        {"name": "Technology", "slug": "technology", "description": "General technology discussions, gadgets, and computing.", "parent_slug": None},
        {"name": "OpenSource", "slug": "opensource", "description": "Free and open-source software, projects, and collaboration.", "parent_slug": None},
        # Children of Technology
        {"name": "Programming", "slug": "programming", "description": "Computer programming languages, software engineering, and best practices.", "parent_slug": "technology"},
        {"name": "Cybersecurity", "slug": "cybersecurity", "description": "Infosec, vulnerability research, and defense strategies.", "parent_slug": "technology"},
        {"name": "ArtificialIntelligence", "slug": "artificialintelligence", "description": "AI architectures, research, neural nets, and cognition.", "parent_slug": "technology"},
        # Grandchildren under Programming
        {"name": "Python", "slug": "python", "description": "Everything Python: Flask, Django, data structures, and scripting.", "parent_slug": "programming"},
        {"name": "Java", "slug": "java", "description": "Enterprise Java, JVM tuning, Spring framework, and Android.", "parent_slug": "programming"},
        {"name": "C++", "slug": "cpp", "description": "Modern C++ (C++20/23), low latency systems, and memory management.", "parent_slug": "programming"},
        # Grandchildren under Cybersecurity
        {"name": "EthicalHacking", "slug": "ethicalhacking", "description": "Penetration testing, bug bounties, and capture-the-flag (CTF).", "parent_slug": "cybersecurity"},
        {"name": "DigitalForensics", "slug": "digitalforensics", "description": "Incident response, packet analysis, and memory extraction.", "parent_slug": "cybersecurity"},
        # Grandchildren under ArtificialIntelligence
        {"name": "MachineLearning", "slug": "machinelearning", "description": "Supervised, unsupervised learning, gradient boosting, and PyTorch.", "parent_slug": "artificialintelligence"},
        {"name": "GenerativeAI", "slug": "generativeai", "description": "LLMs, diffusion models, transformers, and prompt engineering.", "parent_slug": "artificialintelligence"},
    ]

    comm_map = {}  # slug -> id

    for c in communities_spec:
        cursor.execute("SELECT id FROM communities WHERE slug = ?", (c["slug"],))
        row = cursor.fetchone()
        if row:
            comm_map[c["slug"]] = row["id"]
        else:
            parent_id = comm_map.get(c["parent_slug"]) if c["parent_slug"] else None
            cursor.execute(
                "INSERT INTO communities (name, slug, description, parent_id) VALUES (?, ?, ?, ?)",
                (c["name"], c["slug"], c["description"], parent_id)
            )
            comm_map[c["slug"]] = cursor.lastrowid

    # 3. Seed Posts (At least 20 sample posts with varied timestamps)
    now = datetime.now()
    sample_posts = [
        {
            "title": "Implementing a Custom HashMap from Scratch in Python",
            "content": "Why rely on built-in dicts when you can build separate chaining with linked list nodes? It provides deep insight into hash distributions and dynamic resizing.",
            "author": "nishad", "comm": "python", "hours_ago": 2
        },
        {
            "title": "Optimizing Top-K Selection with Min-Heap vs Full Sorting",
            "content": "Sorting an entire list of N elements costs O(N log N). By maintaining a Min-Heap of size K, we reduce the complexity to O(N log K), saving huge memory and compute.",
            "author": "sarvesh", "comm": "programming", "hours_ago": 4
        },
        {
            "title": "Attention Is All You Need: Transformer Architecture Deep Dive",
            "content": "Exploring self-attention mechanisms, multi-head projections, and positional encodings in modern large language models.",
            "author": "aparna", "comm": "generativeai", "hours_ago": 6
        },
        {
            "title": "Memory Dump Analysis in Digital Forensics Using Volatility",
            "content": "Step-by-step methodology for extracting process trees, network sockets, and suspicious injected DLLs from raw Windows RAM captures.",
            "author": "vedika", "comm": "digitalforensics", "hours_ago": 8
        },
        {
            "title": "Kernel-Level Privilege Escalation Defense Strategies",
            "content": "Analyzing common ring 0 privilege escalation vectors and modern mitigations including SMEP, SMAP, and virtualization-based security (VBS).",
            "author": "saurav", "comm": "ethicalhacking", "hours_ago": 12
        },
        {
            "title": "High-Throughput Distributed Hash Table Design Patterns",
            "content": "Simulating key partitioning across logical shards using deterministic hashing. How logical sharding models real-world cluster routing.",
            "author": "athravsingh", "comm": "technology", "hours_ago": 14
        },
        {
            "title": "Evaluating Fine-Tuned LLMs with LoRA and QLoRA",
            "content": "Low-Rank Adaptation allows fine-tuning multi-billion parameter foundation models on modest consumer hardware with minimal degradation.",
            "author": "kusum", "comm": "machinelearning", "hours_ago": 16
        },
        {
            "title": "Contributing to Open Source: Navigating Large Codebases",
            "content": "Tips for first-time contributors: building an inverted index of codebase documentation, finding good-first-issues, and drafting clean PRs.",
            "author": "alok", "comm": "opensource", "hours_ago": 18
        },
        {
            "title": "Modern C++20 Concepts and Metaprogramming",
            "content": "Concepts replace ugly SFINAE constructs with clean constraints on template arguments, dramatically improving compiler diagnostics.",
            "author": "nishad", "comm": "cpp", "hours_ago": 20
        },
        {
            "title": "Garbage Collection Algorithms in Modern JVMs (ZGC & Shenandoah)",
            "content": "How concurrent mark-and-compact garbage collectors achieve sub-millisecond pause times even with terabyte-sized heaps.",
            "author": "sarvesh", "comm": "java", "hours_ago": 24
        },
        {
            "title": "Hierarchical Data Representation: N-ary Trees vs Flat Tables",
            "content": "Why tree structures with O(1) hash indexing excel for nested category trees, breadcrumbs, and permission inheritance.",
            "author": "aparna", "comm": "programming", "hours_ago": 28
        },
        {
            "title": "Reverse Engineering Binaries: Ghidra vs IDA Pro",
            "content": "An overview of NSA's open-source Ghidra decompiler vs IDA Pro. Practical tips for decompiling stripped ELF and PE binaries.",
            "author": "saurav", "comm": "ethicalhacking", "hours_ago": 32
        },
        {
            "title": "Building Inverted Indexes for Sub-Millisecond Full-Text Search",
            "content": "Mapping tokenized n-grams to posting lists using a custom HashMap. Demonstrating speedups over linear scans.",
            "author": "nishad", "comm": "python", "hours_ago": 36
        },
        {
            "title": "Network Packet Carving with Wireshark and TShark",
            "content": "Extracting transmitted files and SSL/TLS session indicators from packet captures during forensic triage.",
            "author": "vedika", "comm": "digitalforensics", "hours_ago": 40
        },
        {
            "title": "Federated Learning: Training AI Without Moving Raw Data",
            "content": "Decentralized machine learning where model updates are aggregated securely, keeping private user data on-device.",
            "author": "kusum", "comm": "machinelearning", "hours_ago": 44
        },
        {
            "title": "Microservices vs Modular Monolith: Real Tradeoffs",
            "content": "Distributed systems introduce network partitions, latency, and operational complexity. When a modular monolith is the superior architecture.",
            "author": "athravsingh", "comm": "technology", "hours_ago": 48
        },
        {
            "title": "Effective Open Source Community Governance",
            "content": "Benevolent Dictator For Life vs Steering Committees. How successful open source projects manage roadmap and contributor consensus.",
            "author": "alok", "comm": "opensource", "hours_ago": 52
        },
        {
            "title": "Understanding Python's GIL and Free-Threaded Python 3.13",
            "content": "A comprehensive look at PEP 703 and how removing the Global Interpreter Lock affects multi-threaded scientific computing.",
            "author": "sarvesh", "comm": "python", "hours_ago": 56
        },
        {
            "title": "Automated Penetration Testing Pipelines with CI/CD",
            "content": "Integrating dynamic application security testing (DAST) and static analysis (SAST) into automated deployment workflows.",
            "author": "saurav", "comm": "cybersecurity", "hours_ago": 60
        },
        {
            "title": "Zero-Knowledge Proofs (ZK-SNARKs) in Modern Cryptography",
            "content": "How cryptographic proofs allow one party to prove a statement is true without revealing any underlying private data.",
            "author": "athravsingh", "comm": "cybersecurity", "hours_ago": 64
        },
        {
            "title": "Retrieval-Augmented Generation (RAG) Architecture Best Practices",
            "content": "Combining vector similarity searches, hybrid keyword inverted indexes, and reranking models for grounded LLM responses.",
            "author": "aparna", "comm": "generativeai", "hours_ago": 70
        },
        {
            "title": "Memory Safety in Systems Programming: Rust vs Modern C++",
            "content": "Comparing borrow checker semantics with smart pointers and RAII. Will safe C++ subsets bridge the gap?",
            "author": "nishad", "comm": "cpp", "hours_ago": 76
        }
    ]

    post_ids = []
    for p in sample_posts:
        cursor.execute("SELECT id FROM posts WHERE title = ?", (p["title"],))
        row = cursor.fetchone()
        if row:
            post_ids.append(row["id"])
        else:
            post_time = (now - timedelta(hours=p["hours_ago"])).strftime("%Y-%m-%d %H:%M:%S")
            author_id = user_map[p["author"]]
            comm_id = comm_map[p["comm"]]
            cursor.execute(
                """INSERT INTO posts (title, content, author_id, community_id, score, upvotes, downvotes, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 0, 0, 0, ?, ?)""",
                (p["title"], p["content"], author_id, comm_id, post_time, post_time)
            )
            post_ids.append(cursor.lastrowid)

    # 4. Seed Votes (Simulate realistic community engagement across Arcane accounts)
    # Ensure voting is idempotent: check if votes already exist
    cursor.execute("SELECT COUNT(*) as cnt FROM votes")
    existing_votes = cursor.fetchone()["cnt"]

    if existing_votes == 0:
        # Predefined voting matrix to create realistic scores and karma
        # User accounts vote on various posts
        users_list = list(user_map.values())
        # Let's seed specific votes for posts
        # First post (Nishad's Custom HashMap): upvoted by sarvesh, aparna, saurav, alok, vedika, athravsingh, kusum
        vote_plan = [
            (post_ids[0], [("sarvesh", 1), ("aparna", 1), ("saurav", 1), ("alok", 1), ("vedika", 1), ("athravsingh", 1), ("kusum", 1)]),
            (post_ids[1], [("nishad", 1), ("aparna", 1), ("saurav", 1), ("alok", 1), ("vedika", 1), ("athravsingh", 1)]),
            (post_ids[2], [("nishad", 1), ("sarvesh", 1), ("saurav", 1), ("kusum", 1), ("alok", 1)]),
            (post_ids[3], [("nishad", 1), ("saurav", 1), ("athravsingh", 1), ("kusum", 1)]),
            (post_ids[4], [("nishad", 1), ("vedika", 1), ("sarvesh", 1), ("alok", 1), ("kusum", 1)]),
            (post_ids[5], [("nishad", 1), ("sarvesh", 1), ("aparna", 1), ("vedika", 1)]),
            (post_ids[6], [("aparna", 1), ("sarvesh", 1), ("nishad", 1), ("athravsingh", 1)]),
            (post_ids[7], [("nishad", 1), ("sarvesh", 1), ("aparna", 1)]),
            (post_ids[8], [("sarvesh", 1), ("athravsingh", 1), ("saurav", -1)]),
            (post_ids[9], [("nishad", 1), ("alok", 1)]),
            (post_ids[10], [("nishad", 1), ("sarvesh", 1), ("vedika", 1), ("kusum", 1)]),
            (post_ids[12], [("sarvesh", 1), ("aparna", 1), ("saurav", 1), ("athravsingh", 1), ("vedika", 1)]),
            (post_ids[20], [("nishad", 1), ("sarvesh", 1), ("kusum", 1), ("athravsingh", 1)]),
        ]

        for pid, votes in vote_plan:
            for voter_uname, vtype in votes:
                voter_id = user_map[voter_uname]
                cursor.execute(
                    "INSERT OR IGNORE INTO votes (user_id, post_id, vote_type) VALUES (?, ?, ?)",
                    (voter_id, pid, vtype)
                )

        # Recalculate post scores, upvotes, downvotes
        cursor.execute("""
            UPDATE posts SET
                upvotes = (SELECT COUNT(*) FROM votes WHERE votes.post_id = posts.id AND vote_type = 1),
                downvotes = (SELECT COUNT(*) FROM votes WHERE votes.post_id = posts.id AND vote_type = -1),
                score = (SELECT COALESCE(SUM(vote_type), 0) FROM votes WHERE votes.post_id = posts.id)
        """)

        # Recalculate user karma from posts
        cursor.execute("""
            UPDATE users SET karma = (
                SELECT COALESCE(SUM(score), 0) FROM posts WHERE posts.author_id = users.id
            )
        """)

    conn.commit()
    conn.close()


# Database access helper functions
def get_user_by_username(username, db_path=None):
    conn = get_db_connection(db_path)
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return user


def get_user_by_id(user_id, db_path=None):
    conn = get_db_connection(db_path)
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user


def create_user(username, display_name, password, bio="", db_path=None):
    conn = get_db_connection(db_path)
    pwd_hash = generate_password_hash(password)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, display_name, password_hash, bio) VALUES (?, ?, ?, ?)",
            (username.lower().strip(), display_name.strip(), pwd_hash, bio.strip())
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        conn.close()
        return None


def get_all_communities(db_path=None):
    conn = get_db_connection(db_path)
    comms = conn.execute("SELECT * FROM communities ORDER BY name ASC").fetchall()
    conn.close()
    return [dict(c) for c in comms]


def get_community_by_slug(slug, db_path=None):
    conn = get_db_connection(db_path)
    comm = conn.execute("SELECT * FROM communities WHERE slug = ?", (slug,)).fetchone()
    conn.close()
    return dict(comm) if comm else None


def get_community_by_id(comm_id, db_path=None):
    conn = get_db_connection(db_path)
    comm = conn.execute("SELECT * FROM communities WHERE id = ?", (comm_id,)).fetchone()
    conn.close()
    return dict(comm) if comm else None


def create_community(name, slug, description, parent_id=None, db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO communities (name, slug, description, parent_id) VALUES (?, ?, ?, ?)",
            (name.strip(), slug.strip().lower(), description.strip(), parent_id)
        )
        conn.commit()
        comm_id = cursor.lastrowid
        conn.close()
        return comm_id
    except sqlite3.IntegrityError:
        conn.close()
        return None


def get_all_posts(db_path=None):
    conn = get_db_connection(db_path)
    posts = conn.execute("""
        SELECT p.*, u.username as author_username, u.display_name as author_display_name,
               c.name as community_name, c.slug as community_slug
        FROM posts p
        JOIN users u ON p.author_id = u.id
        JOIN communities c ON p.community_id = c.id
        ORDER BY p.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(p) for p in posts]


def get_post_by_id(post_id, db_path=None):
    conn = get_db_connection(db_path)
    post = conn.execute("""
        SELECT p.*, u.username as author_username, u.display_name as author_display_name,
               c.name as community_name, c.slug as community_slug
        FROM posts p
        JOIN users u ON p.author_id = u.id
        JOIN communities c ON p.community_id = c.id
        WHERE p.id = ?
    """, (post_id,)).fetchone()
    conn.close()
    return dict(post) if post else None


def create_post(title, content, author_id, community_id, db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO posts (title, content, author_id, community_id, score, upvotes, downvotes)
        VALUES (?, ?, ?, ?, 0, 0, 0)
    """, (title.strip(), content.strip(), author_id, community_id))
    conn.commit()
    post_id = cursor.lastrowid
    conn.close()
    return post_id


def update_post(post_id, title, content, author_id, db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE posts
        SET title = ?, content = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND author_id = ?
    """, (title.strip(), content.strip(), post_id, author_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def delete_post(post_id, author_id, db_path=None):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    # Decrement author karma by post score before deleting
    post = conn.execute("SELECT author_id, score FROM posts WHERE id = ? AND author_id = ?", (post_id, author_id)).fetchone()
    if not post:
        conn.close()
        return False

    cursor.execute("DELETE FROM posts WHERE id = ? AND author_id = ?", (post_id, author_id))
    cursor.execute("UPDATE users SET karma = karma - ? WHERE id = ?", (post["score"], author_id))
    conn.commit()
    conn.close()
    return True


def get_user_vote(user_id, post_id, db_path=None):
    conn = get_db_connection(db_path)
    vote = conn.execute("SELECT vote_type FROM votes WHERE user_id = ? AND post_id = ?", (user_id, post_id)).fetchone()
    conn.close()
    return vote["vote_type"] if vote else 0


def record_vote(user_id, post_id, desired_direction, db_path=None):
    """
    Executes a vote transaction adhering strictly to scoring rules:
    - New upvote: +1
    - New downvote: -1
    - Remove upvote: -1
    - Remove downvote: +1
    - Change upvote to downvote: -2
    - Change downvote to upvote: +2
    Atomic in SQLite and prevents duplicate voting.
    Returns: dict with updated score, author_karma, and new vote_status.
    """
    if desired_direction not in (-1, 0, 1):
        raise ValueError("Invalid vote direction")

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    try:
        # Fetch current post & author
        cursor.execute("SELECT author_id, score, upvotes, downvotes FROM posts WHERE id = ?", (post_id,))
        post = cursor.fetchone()
        if not post:
            conn.close()
            return None

        author_id = post["author_id"]

        # Fetch existing vote
        cursor.execute("SELECT vote_type FROM votes WHERE user_id = ? AND post_id = ?", (user_id, post_id))
        existing_vote_row = cursor.fetchone()
        current_vote = existing_vote_row["vote_type"] if existing_vote_row else 0

        # Calculate delta based on specification table
        score_delta = 0
        upvote_delta = 0
        downvote_delta = 0
        final_vote = desired_direction

        # If user clicks the same vote direction they already have, it unvotes (toggles)
        if current_vote == desired_direction:
            final_vote = 0

        if current_vote == 0 and final_vote == 1:
            score_delta = +1
            upvote_delta = +1
        elif current_vote == 0 and final_vote == -1:
            score_delta = -1
            downvote_delta = +1
        elif current_vote == 1 and final_vote == 0:
            score_delta = -1
            upvote_delta = -1
        elif current_vote == -1 and final_vote == 0:
            score_delta = +1
            downvote_delta = -1
        elif current_vote == 1 and final_vote == -1:
            score_delta = -2
            upvote_delta = -1
            downvote_delta = +1
        elif current_vote == -1 and final_vote == 1:
            score_delta = +2
            downvote_delta = -1
            upvote_delta = +1
        else:
            # No change
            score_delta = 0

        if score_delta != 0 or current_vote != final_vote:
            # Update votes table
            if final_vote == 0:
                cursor.execute("DELETE FROM votes WHERE user_id = ? AND post_id = ?", (user_id, post_id))
            else:
                cursor.execute("""
                    INSERT INTO votes (user_id, post_id, vote_type)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id, post_id) DO UPDATE SET vote_type = excluded.vote_type
                """, (user_id, post_id, final_vote))

            # Update post score and counters
            cursor.execute("""
                UPDATE posts
                SET score = score + ?,
                    upvotes = upvotes + ?,
                    downvotes = downvotes + ?
                WHERE id = ?
            """, (score_delta, upvote_delta, downvote_delta, post_id))

            # Update author karma
            cursor.execute("""
                UPDATE users
                SET karma = karma + ?
                WHERE id = ?
            """, (score_delta, author_id))

        conn.commit()

        # Fetch updated values
        cursor.execute("SELECT score FROM posts WHERE id = ?", (post_id,))
        new_score = cursor.fetchone()["score"]

        cursor.execute("SELECT karma FROM users WHERE id = ?", (author_id,))
        new_karma = cursor.fetchone()["karma"]

        conn.close()
        return {
            "post_id": post_id,
            "new_score": new_score,
            "author_id": author_id,
            "author_karma": new_karma,
            "user_vote": final_vote,
            "score_delta": score_delta
        }
    except Exception as e:
        conn.rollback()
        conn.close()
        raise e
