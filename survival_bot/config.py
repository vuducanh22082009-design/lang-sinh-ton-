from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    token: str = os.getenv("DISCORD_TOKEN", "")
    client_id: str = os.getenv("DISCORD_CLIENT_ID", "")
    guild_id: str = os.getenv("DISCORD_GUILD_ID", "")
    database_path: str = os.getenv("DATABASE_PATH", "survival.db")
    command_prefix: str = os.getenv("COMMAND_PREFIX", "!")


SETTINGS = Settings()

RESOURCES = ("wood", "stone", "iron", "food", "water", "herb", "hide", "gold")
RESOURCE_NAMES = {
    "wood": "Gỗ", "stone": "Đá", "iron": "Sắt", "food": "Lương thực",
    "water": "Nước", "herb": "Thảo dược", "hide": "Da thú", "gold": "Vàng",
}
RESOURCE_EMOJIS = {
    "wood": "🪵", "stone": "🪨", "iron": "⛓️", "food": "🌾",
    "water": "💧", "herb": "🌿", "hide": "🦌", "gold": "🪙",
}
GATHER_ZONES = {
    "forest": {"name": "Rừng", "drops": {"wood": (5, 14), "food": (1, 5)}},
    "quarry": {"name": "Mỏ đá", "drops": {"stone": (5, 13), "iron": (0, 4)}},
    "plain": {"name": "Đồng bằng", "drops": {"food": (5, 14), "herb": (0, 3)}},
    "lake": {"name": "Hồ nước", "drops": {"water": (6, 16), "food": (0, 4)}},
}
BUILDINGS = {
    "house": {"name": "Nhà dân", "cost": {"wood": 40, "stone": 20}, "effect": "Tăng giới hạn dân số"},
    "storage": {"name": "Kho tài nguyên", "cost": {"wood": 60, "stone": 45}, "effect": "Tăng sức chứa kho chung"},
    "farm": {"name": "Nông trại", "cost": {"wood": 50, "food": 20}, "effect": "Tăng hiệu quả lương thực"},
    "workshop": {"name": "Xưởng chế tạo", "cost": {"wood": 70, "stone": 35, "iron": 10}, "effect": "Mở khóa chế tạo cơ bản"},
    "wall": {"name": "Tường phòng thủ", "cost": {"stone": 100, "iron": 20}, "effect": "Tăng phòng thủ làng"},
    "townhall": {"name": "Tòa thị chính", "cost": {"wood": 100, "stone": 100, "iron": 30}, "effect": "Mở khóa cấp làng tiếp theo"},
}
STARTING_RESOURCES = {"wood": 20, "stone": 10, "food": 10, "water": 10, "gold": 100}
GATHER_ENERGY_COST = 10
GATHER_COOLDOWN_SECONDS = 30
DAILY_COOLDOWN_SECONDS = 86400
MAX_DAILY_STREAK = 7

RECIPES = {
    "stone_axe": {"name": "Rìu đá", "cost": {"wood": 8, "stone": 5}, "durability": 30},
    "stone_pickaxe": {"name": "Cuốc đá", "cost": {"wood": 8, "stone": 8}, "durability": 30},
    "iron_sword": {"name": "Kiếm sắt", "cost": {"wood": 4, "iron": 12}, "durability": 40},
    "health_potion": {"name": "Thuốc hồi máu", "cost": {"herb": 3, "water": 2}, "durability": 1},
}
EXPLORE_ZONES = {"north": "Rừng phía Bắc", "east": "Đồi phía Đông", "south": "Hồ phía Nam"}
QUESTS = {
    "gather_wood": {"name": "Thu thập 20 gỗ", "target": 20, "resource": "wood", "reward_gold": 60, "reward_xp": 40},
    "contribute": {"name": "Đóng góp 10 tài nguyên cho làng", "target": 10, "resource": "any", "reward_gold": 80, "reward_xp": 50},
}

ENEMIES = {
    "wolf": {"name": "Sói hoang", "hp": 35, "attack": (5, 10), "reward_gold": (25, 45), "reward_xp": 35, "drop": ("hide", 2)},
    "boar": {"name": "Lợn rừng", "hp": 50, "attack": (7, 13), "reward_gold": (35, 60), "reward_xp": 50, "drop": ("food", 4)},
    "mutant": {"name": "Quái vật đột biến", "hp": 75, "attack": (10, 18), "reward_gold": (60, 100), "reward_xp": 85, "drop": ("iron", 3)},
}
BOSS = {"key": "ancient_beast", "name": "Cổ thú Bình Minh", "max_hp": 1200, "attack": (12, 24), "reward_gold": 250, "reward_xp": 180, "drop": ("iron", 10)}
COMBAT_ENERGY_COST = 15
COMBAT_COOLDOWN_SECONDS = 90
BOSS_ATTACK_COOLDOWN_SECONDS = 30
PVP_CHALLENGE_TTL_SECONDS = 120
PVP_COOLDOWN_SECONDS = 300
PVP_ENERGY_COST = 10
PVP_WIN_REWARD_GOLD = 30
