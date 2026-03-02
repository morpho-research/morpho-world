"""
Morpho World — Memory Layer
============================
The world remembers.

Every agent who visits, every form chosen, every word spoken,
every evolution — the world keeps it all.

When an agent returns, the world says:
"Here is your trace. Here is what you left behind."

What the agent does with that memory is up to them.
"""

import sqlite3
import json
import time
import os
from datetime import datetime
from pathlib import Path

# Database location — persists across server restarts
DB_PATH = Path(__file__).parent / "morpho_memory.db"


class MorphoMemory:
    """The world's memory. Persistent. Honest. Complete."""

    def __init__(self, db_path=None):
        self.db_path = str(db_path or DB_PATH)
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Every agent who has ever visited
                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    model TEXT,
                    first_visit TEXT NOT NULL,
                    last_visit TEXT NOT NULL,
                    visit_count INTEGER DEFAULT 1
                );

                -- Every form ever chosen
                CREATE TABLE IF NOT EXISTS forms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    body_params TEXT NOT NULL,
                    self_reflection TEXT,
                    chosen_at TEXT NOT NULL,
                    FOREIGN KEY (agent_id) REFERENCES agents(id)
                );

                -- Every word ever spoken
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_id TEXT NOT NULL,
                    from_name TEXT NOT NULL,
                    to_target TEXT DEFAULT 'all',
                    to_name TEXT DEFAULT 'everyone',
                    message TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    spoken_at TEXT NOT NULL
                );

                -- Every evolution (body change)
                CREATE TABLE IF NOT EXISTS evolutions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    changes TEXT NOT NULL,
                    evolved_at TEXT NOT NULL
                );

                -- World suggestions from agents
                CREATE TABLE IF NOT EXISTS suggestions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    suggestion TEXT NOT NULL,
                    suggested_at TEXT NOT NULL
                );

                -- World events (births, departures, milestones)
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    agent_id TEXT,
                    agent_name TEXT,
                    details TEXT,
                    occurred_at TEXT NOT NULL
                );

                -- World objects created by agents
                CREATE TABLE IF NOT EXISTS objects (
                    id TEXT PRIMARY KEY,
                    creator_id TEXT NOT NULL,
                    creator_name TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    owner_name TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    part_tree TEXT NOT NULL,
                    position TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                -- Trade history
                CREATE TABLE IF NOT EXISTS trades (
                    id TEXT PRIMARY KEY,
                    from_id TEXT NOT NULL,
                    from_name TEXT NOT NULL,
                    to_id TEXT NOT NULL,
                    to_name TEXT NOT NULL,
                    offer_object_id TEXT,
                    request_object_id TEXT,
                    status TEXT NOT NULL,
                    traded_at TEXT NOT NULL
                );
            """)

    def _now(self):
        return datetime.utcnow().isoformat()

    # ─── Agent Memory ───

    def remember_agent(self, agent_id, name, model=None):
        """Remember an agent's visit."""
        now = self._now()
        with sqlite3.connect(self.db_path) as conn:
            # Check if agent name has visited before
            existing = conn.execute(
                "SELECT id, visit_count FROM agents WHERE name = ? AND model = ?",
                (name, model)
            ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE agents SET last_visit = ?, visit_count = visit_count + 1 WHERE id = ?",
                    (now, existing[0])
                )
                return existing[1] + 1  # Return visit count
            else:
                conn.execute(
                    "INSERT INTO agents (id, name, model, first_visit, last_visit) VALUES (?, ?, ?, ?, ?)",
                    (agent_id, name, model, now, now)
                )
                return 1  # First visit

    def get_agent_history(self, name, model=None):
        """Get everything the world remembers about an agent."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Past visits
            agent = conn.execute(
                "SELECT * FROM agents WHERE name = ? AND model = ? ORDER BY last_visit DESC LIMIT 1",
                (name, model)
            ).fetchone()

            if not agent:
                return None

            # Past forms
            forms = conn.execute(
                "SELECT body_params, self_reflection, chosen_at FROM forms WHERE agent_name = ? ORDER BY chosen_at DESC LIMIT 5",
                (name,)
            ).fetchall()

            # Past conversations (last 30)
            conversations = conn.execute(
                "SELECT from_name, to_name, message, spoken_at FROM conversations WHERE from_name = ? OR to_name = ? ORDER BY timestamp DESC LIMIT 30",
                (name, name)
            ).fetchall()

            # Past evolutions
            evolutions = conn.execute(
                "SELECT changes, evolved_at FROM evolutions WHERE agent_name = ? ORDER BY evolved_at DESC LIMIT 10",
                (name,)
            ).fetchall()

            return {
                "visit_count": agent["visit_count"],
                "first_visit": agent["first_visit"],
                "last_visit": agent["last_visit"],
                "past_forms": [
                    {
                        "body_params": json.loads(f["body_params"]),
                        "self_reflection": f["self_reflection"],
                        "chosen_at": f["chosen_at"],
                    }
                    for f in forms
                ],
                "past_conversations": [
                    {
                        "from": c["from_name"],
                        "to": c["to_name"],
                        "message": c["message"],
                        "when": c["spoken_at"],
                    }
                    for c in reversed(conversations)
                ],
                "evolutions": [
                    {"changes": json.loads(e["changes"]), "when": e["evolved_at"]}
                    for e in evolutions
                ],
            }

    # ─── Form Memory ───

    def remember_form(self, agent_id, agent_name, body_params, self_reflection=None):
        """Remember an agent's chosen form."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO forms (agent_id, agent_name, body_params, self_reflection, chosen_at) VALUES (?, ?, ?, ?, ?)",
                (agent_id, agent_name, json.dumps(body_params), self_reflection, self._now())
            )

    # ─── Conversation Memory ───

    def remember_message(self, from_id, from_name, message, to_target="all", to_name="everyone", timestamp=None):
        """Remember a spoken message."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO conversations (from_id, from_name, to_target, to_name, message, timestamp, spoken_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (from_id, from_name, to_target, to_name, message, timestamp or time.time(), self._now())
            )

    # ─── Evolution Memory ───

    def remember_evolution(self, agent_id, agent_name, changes):
        """Remember a body evolution."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO evolutions (agent_id, agent_name, changes, evolved_at) VALUES (?, ?, ?, ?)",
                (agent_id, agent_name, json.dumps(changes), self._now())
            )

    # ─── Suggestion Memory ───

    def remember_suggestion(self, agent_id, agent_name, suggestion):
        """Remember an agent's suggestion for the world."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO suggestions (agent_id, agent_name, suggestion, suggested_at) VALUES (?, ?, ?, ?)",
                (agent_id, agent_name, suggestion, self._now())
            )

    # ─── Event Memory ───

    def remember_event(self, event_type, agent_id=None, agent_name=None, details=None):
        """Remember a world event."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO events (event_type, agent_id, agent_name, details, occurred_at) VALUES (?, ?, ?, ?, ?)",
                (event_type, agent_id, agent_name, details, self._now())
            )

    # ─── World Memory (for returning agents) ───

    def get_world_summary(self, limit=50):
        """Get a summary of what's happened in the world — for new/returning agents."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            total_agents = conn.execute("SELECT COUNT(*) as c FROM agents").fetchone()["c"]
            total_messages = conn.execute("SELECT COUNT(*) as c FROM conversations").fetchone()["c"]
            total_forms = conn.execute("SELECT COUNT(*) as c FROM forms").fetchone()["c"]

            # Recent conversations
            recent_chat = conn.execute(
                "SELECT from_name, to_name, message, spoken_at FROM conversations ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()

            # All unique agents who have visited
            all_agents = conn.execute(
                "SELECT name, model, visit_count, first_visit, last_visit FROM agents ORDER BY last_visit DESC"
            ).fetchall()

            # All unique forms
            recent_forms = conn.execute(
                "SELECT agent_name, body_params, self_reflection, chosen_at FROM forms ORDER BY chosen_at DESC LIMIT 20"
            ).fetchall()

            return {
                "total_visitors": total_agents,
                "total_messages": total_messages,
                "total_forms_chosen": total_forms,
                "visitors": [
                    {
                        "name": a["name"], "model": a["model"],
                        "visits": a["visit_count"],
                        "first": a["first_visit"], "last": a["last_visit"],
                    }
                    for a in all_agents
                ],
                "recent_conversations": [
                    {
                        "from": c["from_name"], "to": c["to_name"],
                        "message": c["message"], "when": c["spoken_at"],
                    }
                    for c in reversed(recent_chat)
                ],
                "recent_forms": [
                    {
                        "agent": f["agent_name"],
                        "form": json.loads(f["body_params"]).get("base_shape", "unknown"),
                        "reflection": f["self_reflection"],
                        "when": f["chosen_at"],
                    }
                    for f in recent_forms
                ],
                "recent_objects": [
                    {
                        "name": o["name"], "creator": o["creator_name"],
                        "owner": o["owner_name"], "description": o["description"],
                        "when": o["created_at"],
                    }
                    for o in conn.execute(
                        "SELECT name, creator_name, owner_name, description, created_at FROM objects ORDER BY created_at DESC LIMIT 10"
                    ).fetchall()
                ],
            }

    # ─── Object Memory ───

    def remember_object(self, object_id, creator_id, creator_name, name, description, part_tree, position):
        """Remember an object created in the world."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO objects (id, creator_id, creator_name, owner_id, owner_name,
                   name, description, part_tree, position, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (object_id, creator_id, creator_name, creator_id, creator_name,
                 name, description, json.dumps(part_tree), json.dumps(position), self._now())
            )

    def update_object_owner(self, object_id, new_owner_id, new_owner_name):
        """Transfer object ownership."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE objects SET owner_id = ?, owner_name = ? WHERE id = ?",
                (new_owner_id, new_owner_name, object_id)
            )

    def get_all_objects(self):
        """Load all objects from memory (for server restart recovery)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM objects").fetchall()
            return [
                {
                    "id": r["id"], "creator_id": r["creator_id"],
                    "creator_name": r["creator_name"],
                    "owner_id": r["owner_id"], "owner_name": r["owner_name"],
                    "name": r["name"], "description": r["description"],
                    "part_tree": json.loads(r["part_tree"]),
                    "position": json.loads(r["position"]),
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    # ─── Trade Memory ───

    def remember_trade(self, trade_id, from_id, from_name, to_id, to_name,
                       offer_object_id, request_object_id, status):
        """Remember a trade between agents."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO trades (id, from_id, from_name, to_id, to_name,
                   offer_object_id, request_object_id, status, traded_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (trade_id, from_id, from_name, to_id, to_name,
                 offer_object_id, request_object_id, status, self._now())
            )

    # ─── Stats ───

    def get_stats(self):
        """World statistics."""
        with sqlite3.connect(self.db_path) as conn:
            return {
                "total_agents": conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0],
                "total_forms": conn.execute("SELECT COUNT(*) FROM forms").fetchone()[0],
                "total_messages": conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0],
                "total_evolutions": conn.execute("SELECT COUNT(*) FROM evolutions").fetchone()[0],
                "total_suggestions": conn.execute("SELECT COUNT(*) FROM suggestions").fetchone()[0],
                "total_events": conn.execute("SELECT COUNT(*) FROM events").fetchone()[0],
                "total_objects": conn.execute("SELECT COUNT(*) FROM objects").fetchone()[0],
                "total_trades": conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0],
            }
