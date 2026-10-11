import random
import threading
from pathlib import Path

import pytest

from survival_bot.db import Database
from survival_bot.service import GameError, GameService


@pytest.fixture
def game(tmp_path: Path):
    return GameService(Database(str(tmp_path / "test.db")), random.Random(7))


def test_register_and_duplicate(game):
    p = game.register("guild-a", "user-a", "An")
    assert p["character_name"] == "An"
    with pytest.raises(GameError, match="đã có nhân vật"):
        game.register("guild-a", "user-a", "Khác")


def test_server_data_is_isolated(game):
    game.register("guild-a", "user-a", "A")
    game.register("guild-b", "user-a", "B")
    game.contribute("guild-a", "user-a", "wood", 5)
    assert game.profile("guild-a", "user-a")["village_contribution"] == 5
    assert game.profile("guild-b", "user-a")["village_contribution"] == 0


def test_gather_energy_and_cooldown(game):
    game.register("g", "u", "A")
    result = game.gather("g", "u", "forest", now=100)
    assert result["energy"] == 90
    with pytest.raises(GameError, match="chờ"):
        game.gather("g", "u", "forest", now=110)


def test_daily_once_per_day(game):
    game.register("g", "u", "A")
    first = game.daily("g", "u", now=1000)
    assert first["reward"] == 60
    with pytest.raises(GameError, match="Daily"):
        game.daily("g", "u", now=1001)


def test_contribution_cannot_exceed_inventory(game):
    game.register("g", "u", "A")
    with pytest.raises(GameError, match="không đủ"):
        game.contribute("g", "u", "wood", 999)
    game.contribute("g", "u", "wood", 20)
    assert game.inventory("g", "u")["wood"] == 0


def test_concurrent_contributions_do_not_make_negative_inventory(tmp_path):
    service = GameService(Database(str(tmp_path / "race.db")))
    service.register("g", "u", "A")
    results = []
    def worker():
        try: service.contribute("g", "u", "wood", 15); results.append("ok")
        except GameError: results.append("rejected")
    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert results.count("ok") == 1
    assert service.inventory("g", "u")["wood"] >= 0


def test_craft_equip_and_explore(game):
    game.register("g", "u", "A")
    crafted = game.craft("g", "u", "stone_axe")
    assert crafted["name"] == "Rìu đá"
    game.equip("g", "u", "stone_axe")
    assert game.items("g", "u")[0]["equipped"] == 1
    explored = game.explore("g", "u", "north", now=100)
    assert explored["zone"] == "Rừng phía Bắc"


def test_quest_progress_and_admin_give(game):
    game.register("g", "u", "A")
    game.admin_give("g", "u", "gold", 500)
    assert game.profile("g", "u")["gold"] == 600
    game.gather("g", "u", "forest", now=100)
    rows = game.quests("g", "u")
    assert rows[0]["progress"] >= 0


def test_hunt_has_server_cooldown_and_transaction(game):
    game.register("g", "u", "A")
    result = game.hunt("g", "u", "wolf", now=100)
    assert result["enemy"] == "Sói hoang"
    assert result["hp"] >= 1
    with pytest.raises(GameError, match="chờ"):
        game.hunt("g", "u", "wolf", now=101)


def test_boss_is_shared_and_does_not_respawn_on_view(game):
    game.register("g", "u1", "A")
    game.register("g", "u2", "B")
    first = game.boss_info("g")
    hit = game.attack_boss("g", "u1", now=100)
    assert hit["hp"] < first["max_hp"]
    second = game.boss_info("g")
    assert second["hp"] == hit["hp"]
    with pytest.raises(GameError, match="chờ"):
        game.attack_boss("g", "u1", now=101)
    # Another member can attack the same shared boss immediately.
    other_hit = game.attack_boss("g", "u2", now=101)
    assert other_hit["hp"] < second["hp"]


def test_admin_can_start_new_boss_after_defeat(game):
    game.register("g", "u", "A")
    game.start_boss("g")
    with game.db.transaction() as conn:
        conn.execute("UPDATE village_bosses SET hp=0, active=0 WHERE guild_id=?", ("g",))
    assert game.boss_info("g")["active"] is False
    assert game.start_boss("g")["active"] is True


def test_boss_defeat_pays_once_and_marks_inactive(game):
    game.register("g", "u", "A")
    game.boss_info("g")
    with game.db.transaction() as conn:
        conn.execute("UPDATE village_bosses SET hp=1 WHERE guild_id=?", ("g",))
    result = game.attack_boss("g", "u", now=100)
    assert result["defeated"] is True
    assert game.boss_info("g")["active"] is False
    with pytest.raises(GameError, match="Chưa có boss"):
        game.attack_boss("g", "u", now=200)


def test_pvp_requires_target_consent_and_has_shared_cooldown(game):
    game.register("g", "a", "A")
    game.register("g", "b", "B")
    game.pvp_challenge("g", "a", "b", now=100)
    with pytest.raises(GameError, match="Không tìm thấy lời mời"):
        game.pvp_accept("g", "a", "b", now=101)
    result = game.pvp_accept("g", "b", "a", now=101)
    assert result["winner_id"] in {"a", "b"}
    game.pvp_challenge("g", "a", "b", now=102)
    with pytest.raises(GameError, match="cooldown"):
        game.pvp_accept("g", "b", "a", now=103)


def test_pvp_invite_expires_and_decline_is_explicit(game):
    game.register("g", "a", "A")
    game.register("g", "b", "B")
    game.pvp_challenge("g", "a", "b", now=100)
    with pytest.raises(GameError, match="hết hạn"):
        game.pvp_accept("g", "b", "a", now=221)
    game.pvp_challenge("g", "a", "b", now=300)
    game.pvp_decline("g", "b", "a", now=301)
