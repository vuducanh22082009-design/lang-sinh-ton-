from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS villages (
  guild_id TEXT PRIMARY KEY, name TEXT NOT NULL DEFAULT 'Làng Bình Minh', level INTEGER NOT NULL DEFAULT 1,
  xp INTEGER NOT NULL DEFAULT 0, defense INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS players (
  guild_id TEXT NOT NULL, user_id TEXT NOT NULL, character_name TEXT NOT NULL, level INTEGER NOT NULL DEFAULT 1,
  xp INTEGER NOT NULL DEFAULT 0, gold INTEGER NOT NULL DEFAULT 100, energy INTEGER NOT NULL DEFAULT 100,
  max_energy INTEGER NOT NULL DEFAULT 100, hp INTEGER NOT NULL DEFAULT 100, max_hp INTEGER NOT NULL DEFAULT 100,
  total_gathered INTEGER NOT NULL DEFAULT 0, village_contribution INTEGER NOT NULL DEFAULT 0,
  quests_completed INTEGER NOT NULL DEFAULT 0, daily_streak INTEGER NOT NULL DEFAULT 0,
  last_daily_at TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (guild_id, user_id), FOREIGN KEY (guild_id) REFERENCES villages(guild_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS inventory (
  guild_id TEXT NOT NULL, user_id TEXT NOT NULL, resource TEXT NOT NULL, quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
  PRIMARY KEY (guild_id, user_id, resource), FOREIGN KEY (guild_id, user_id) REFERENCES players(guild_id, user_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS village_storage (
  guild_id TEXT NOT NULL, resource TEXT NOT NULL, quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
  PRIMARY KEY (guild_id, resource), FOREIGN KEY (guild_id) REFERENCES villages(guild_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS buildings (
  guild_id TEXT NOT NULL, building_key TEXT NOT NULL, level INTEGER NOT NULL DEFAULT 0 CHECK(level >= 0),
  PRIMARY KEY (guild_id, building_key), FOREIGN KEY (guild_id) REFERENCES villages(guild_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS cooldowns (
  guild_id TEXT NOT NULL, user_id TEXT NOT NULL, action TEXT NOT NULL, available_at REAL NOT NULL,
  PRIMARY KEY (guild_id, user_id, action)
);
CREATE TABLE IF NOT EXISTS transaction_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT NOT NULL, user_id TEXT, action TEXT NOT NULL,
  resource TEXT, amount INTEGER, details TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS item_inventory (
  guild_id TEXT NOT NULL, user_id TEXT NOT NULL, item_key TEXT NOT NULL, quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
  durability INTEGER NOT NULL DEFAULT 0 CHECK(durability >= 0), equipped INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (guild_id, user_id, item_key), FOREIGN KEY (guild_id, user_id) REFERENCES players(guild_id, user_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS player_quests (
  guild_id TEXT NOT NULL, user_id TEXT NOT NULL, quest_key TEXT NOT NULL, progress INTEGER NOT NULL DEFAULT 0 CHECK(progress >= 0),
  completed INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (guild_id, user_id, quest_key), FOREIGN KEY (guild_id, user_id) REFERENCES players(guild_id, user_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS village_bosses (
  guild_id TEXT PRIMARY KEY, boss_key TEXT NOT NULL, hp INTEGER NOT NULL CHECK(hp >= 0), max_hp INTEGER NOT NULL CHECK(max_hp > 0),
  active INTEGER NOT NULL DEFAULT 1, spawned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (guild_id) REFERENCES villages(guild_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_players_level ON players(guild_id, level DESC, xp DESC);
CREATE INDEX IF NOT EXISTS idx_players_gold ON players(guild_id, gold DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_guild ON transaction_log(guild_id, created_at DESC);
"""


class Database:
    def __init__(self, path: str = "survival.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 10000")
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def close(self) -> None:
        pass
