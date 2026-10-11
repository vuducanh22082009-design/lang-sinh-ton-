from __future__ import annotations

import random
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any

from .config import BUILDINGS, DAILY_COOLDOWN_SECONDS, GATHER_COOLDOWN_SECONDS, GATHER_ENERGY_COST, GATHER_ZONES, MAX_DAILY_STREAK, RESOURCE_NAMES, STARTING_RESOURCES
from .db import Database


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def xp_needed(level: int) -> int:
    return 100 * level


class GameError(Exception):
    pass


class GameService:
    def __init__(self, db: Database, rng: random.Random | None = None) -> None:
        self.db = db
        self.rng = rng or random.Random()

    def ensure_village(self, guild_id: str, name: str | None = None) -> None:
        with self.db.transaction() as c:
            c.execute("INSERT OR IGNORE INTO villages(guild_id, name) VALUES (?, ?)", (guild_id, name or "Làng Bình Minh"))
            for key in BUILDINGS:
                c.execute("INSERT OR IGNORE INTO buildings(guild_id, building_key) VALUES (?, ?)", (guild_id, key))

    def register(self, guild_id: str, user_id: str, name: str) -> dict[str, Any]:
        self.ensure_village(guild_id)
        safe_name = name.strip()[:32]
        if not safe_name:
            raise GameError("Tên nhân vật không được để trống.")
        with self.db.transaction() as c:
            try:
                c.execute("INSERT INTO players(guild_id, user_id, character_name) VALUES (?, ?, ?)", (guild_id, user_id, safe_name))
            except sqlite3.IntegrityError:
                raise GameError("Bạn đã có nhân vật trong server này rồi.")
            for resource, amount in STARTING_RESOURCES.items():
                c.execute("INSERT INTO inventory(guild_id, user_id, resource, quantity) VALUES (?, ?, ?, ?)", (guild_id, user_id, resource, amount))
            c.execute("INSERT INTO transaction_log(guild_id, user_id, action, details) VALUES (?, ?, 'register', ?)", (guild_id, user_id, safe_name))
        return self.profile(guild_id, user_id)

    def _player(self, c: sqlite3.Connection, guild_id: str, user_id: str) -> sqlite3.Row:
        row = c.execute("SELECT * FROM players WHERE guild_id=? AND user_id=?", (guild_id, user_id)).fetchone()
        if row is None:
            raise GameError("Bạn chưa có nhân vật. Hãy dùng /start trước.")
        return row

    def profile(self, guild_id: str, user_id: str) -> dict[str, Any]:
        with self.db.connect() as c:
            row = self._player(c, guild_id, user_id)
            return dict(row)

    def inventory(self, guild_id: str, user_id: str) -> dict[str, int]:
        with self.db.connect() as c:
            self._player(c, guild_id, user_id)
            return {r["resource"]: r["quantity"] for r in c.execute("SELECT resource, quantity FROM inventory WHERE guild_id=? AND user_id=? ORDER BY resource", (guild_id, user_id))}

    def _add_xp(self, c: sqlite3.Connection, guild_id: str, user_id: str, xp: int) -> None:
        row = self._player(c, guild_id, user_id)
        level, total = row["level"], row["xp"] + xp
        while total >= xp_needed(level):
            total -= xp_needed(level)
            level += 1
        c.execute("UPDATE players SET xp=?, level=?, updated_at=? WHERE guild_id=? AND user_id=?", (total, level, now_iso(), guild_id, user_id))

    def gather(self, guild_id: str, user_id: str, zone_key: str, now: float | None = None) -> dict[str, Any]:
        if zone_key not in GATHER_ZONES:
            raise GameError("Khu vực không hợp lệ. Chọn forest, quarry, plain hoặc lake.")
        now = now if now is not None else time.time()
        zone = GATHER_ZONES[zone_key]
        with self.db.transaction() as c:
            player = self._player(c, guild_id, user_id)
            cd = c.execute("SELECT available_at FROM cooldowns WHERE guild_id=? AND user_id=? AND action='gather'", (guild_id, user_id)).fetchone()
            if cd and cd["available_at"] > now:
                raise GameError(f"Bạn còn phải chờ {int(cd['available_at'] - now) + 1} giây.")
            if player["energy"] < GATHER_ENERGY_COST:
                raise GameError("Bạn không đủ năng lượng. Hãy quay lại sau hoặc chờ hồi năng lượng.")
            rewards = {resource: self.rng.randint(bounds[0], bounds[1]) for resource, bounds in zone["drops"].items()}
            rewards = {resource: amount for resource, amount in rewards.items() if amount > 0}
            for resource, amount in rewards.items():
                c.execute("UPDATE inventory SET quantity=quantity+? WHERE guild_id=? AND user_id=? AND resource=?", (amount, guild_id, user_id, resource))
            xp = sum(rewards.values()) * 2
            c.execute("UPDATE players SET energy=energy-?, total_gathered=total_gathered+?, updated_at=? WHERE guild_id=? AND user_id=?", (GATHER_ENERGY_COST, sum(rewards.values()), now_iso(), guild_id, user_id))
            self._add_xp(c, guild_id, user_id, xp)
            c.execute("INSERT OR REPLACE INTO cooldowns VALUES (?, ?, 'gather', ?)", (guild_id, user_id, now + GATHER_COOLDOWN_SECONDS))
            c.execute("INSERT INTO transaction_log(guild_id,user_id,action,details) VALUES (?,?, 'gather', ?)", (guild_id, user_id, zone_key))
            current = c.execute("SELECT energy FROM players WHERE guild_id=? AND user_id=?", (guild_id, user_id)).fetchone()[0]
        return {"zone": zone["name"], "rewards": rewards, "xp": xp, "energy": current}

    def daily(self, guild_id: str, user_id: str, now: float | None = None) -> dict[str, Any]:
        now = now if now is not None else time.time()
        with self.db.transaction() as c:
            player = self._player(c, guild_id, user_id)
            last = datetime.fromisoformat(player["last_daily_at"]).timestamp() if player["last_daily_at"] else 0
            if last and now - last < DAILY_COOLDOWN_SECONDS:
                raise GameError(f"Daily đã nhận. Còn khoảng {int(DAILY_COOLDOWN_SECONDS - (now-last))//3600} giờ.")
            streak = min(player["daily_streak"] + 1, MAX_DAILY_STREAK) if last and now - last < DAILY_COOLDOWN_SECONDS * 2 else 1
            reward = 50 + streak * 10
            c.execute("UPDATE players SET gold=gold+?, daily_streak=?, last_daily_at=?, updated_at=? WHERE guild_id=? AND user_id=?", (reward, streak, datetime.fromtimestamp(now, timezone.utc).isoformat(), now_iso(), guild_id, user_id))
            c.execute("INSERT INTO transaction_log(guild_id,user_id,action,resource,amount) VALUES (?,?, 'daily','gold',?)", (guild_id, user_id, reward))
        return {"reward": reward, "streak": streak}

    def contribute(self, guild_id: str, user_id: str, resource: str, amount: int) -> dict[str, Any]:
        if resource not in ("wood", "stone", "iron", "food", "water", "herb", "hide") or amount <= 0 or amount > 10000:
            raise GameError("Tài nguyên hoặc số lượng không hợp lệ.")
        with self.db.transaction() as c:
            self._player(c, guild_id, user_id)
            owned = c.execute("SELECT quantity FROM inventory WHERE guild_id=? AND user_id=? AND resource=?", (guild_id, user_id, resource)).fetchone()
            if not owned or owned[0] < amount:
                raise GameError(f"Bạn không đủ {RESOURCE_NAMES[resource]}.")
            c.execute("UPDATE inventory SET quantity=quantity-? WHERE guild_id=? AND user_id=? AND resource=?", (amount, guild_id, user_id, resource))
            c.execute("INSERT OR IGNORE INTO village_storage(guild_id,resource,quantity) VALUES (?,?,0)", (guild_id, resource))
            c.execute("UPDATE village_storage SET quantity=quantity+? WHERE guild_id=? AND resource=?", (amount, guild_id, resource))
            c.execute("UPDATE players SET village_contribution=village_contribution+?, updated_at=? WHERE guild_id=? AND user_id=?", (amount, now_iso(), guild_id, user_id))
            c.execute("UPDATE villages SET xp=xp+?, updated_at=? WHERE guild_id=?", (amount, now_iso(), guild_id))
            c.execute("INSERT INTO transaction_log(guild_id,user_id,action,resource,amount) VALUES (?,?, 'contribute',?,?)", (guild_id, user_id, resource, amount))
        return {"resource": resource, "amount": amount}

    def build(self, guild_id: str, user_id: str, building_key: str) -> dict[str, Any]:
        if building_key not in BUILDINGS:
            raise GameError("Công trình không hợp lệ.")
        spec = BUILDINGS[building_key]
        with self.db.transaction() as c:
            self._player(c, guild_id, user_id)
            level = c.execute("SELECT level FROM buildings WHERE guild_id=? AND building_key=?", (guild_id, building_key)).fetchone()[0]
            if level >= 5:
                raise GameError("Công trình đã đạt cấp tối đa trong MVP.")
            multiplier = level + 1
            for resource, base in spec["cost"].items():
                row = c.execute("SELECT quantity FROM village_storage WHERE guild_id=? AND resource=?", (guild_id, resource)).fetchone()
                if not row or row[0] < base * multiplier:
                    raise GameError(f"Kho làng không đủ {RESOURCE_NAMES[resource]} (cần {base * multiplier}).")
            for resource, base in spec["cost"].items():
                c.execute("UPDATE village_storage SET quantity=quantity-? WHERE guild_id=? AND resource=?", (base * multiplier, guild_id, resource))
            c.execute("UPDATE buildings SET level=level+1 WHERE guild_id=? AND building_key=?", (guild_id, building_key))
            c.execute("UPDATE villages SET xp=xp+?, updated_at=? WHERE guild_id=?", (sum(spec["cost"].values()), now_iso(), guild_id))
            c.execute("INSERT INTO transaction_log(guild_id,user_id,action,details) VALUES (?,?, 'build', ?)", (guild_id, user_id, building_key))
        return {"name": spec["name"], "level": level + 1, "effect": spec["effect"]}

    def village(self, guild_id: str) -> dict[str, Any]:
        self.ensure_village(guild_id)
        with self.db.connect() as c:
            village = dict(c.execute("SELECT * FROM villages WHERE guild_id=?", (guild_id,)).fetchone())
            storage = {r["resource"]: r["quantity"] for r in c.execute("SELECT resource,quantity FROM village_storage WHERE guild_id=?", (guild_id,))}
            buildings = {r["building_key"]: r["level"] for r in c.execute("SELECT building_key,level FROM buildings WHERE guild_id=?", (guild_id,))}
            village.update(storage=storage, buildings=buildings, members=c.execute("SELECT COUNT(*) FROM players WHERE guild_id=?", (guild_id,)).fetchone()[0])
            return village

    def leaderboard(self, guild_id: str, metric: str = "level", limit: int = 10) -> list[dict[str, Any]]:
        columns = {"level": "level DESC, xp DESC", "gold": "gold DESC", "contribution": "village_contribution DESC", "gathered": "total_gathered DESC", "quests": "quests_completed DESC"}
        order = columns.get(metric, columns["level"])
        with self.db.connect() as c:
            return [dict(r) for r in c.execute(f"SELECT character_name, level, gold, village_contribution, total_gathered, quests_completed FROM players WHERE guild_id=? ORDER BY {order} LIMIT ?", (guild_id, limit))]
