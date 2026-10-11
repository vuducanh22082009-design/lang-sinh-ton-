from __future__ import annotations

import logging
import time
import threading
from flask import Flask
import discord
from discord import app_commands
from discord.ext import commands

from survival_bot.config import ADMIN_USER_IDS, BOSS, BUILDINGS, ENEMIES, EXPLORE_ZONES, GATHER_ZONES, RECIPES, RESOURCE_NAMES, SETTINGS
from survival_bot.db import Database
from survival_bot.service import GameError, GameService, xp_needed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("village-survival")

app = Flask(__name__)
STARTED_AT = time.time()
@app.get("/")
def health() -> str:
    return "Village Survival is alive"

@app.get("/health")
def health_details():
    try:
        with db.connect() as connection:
            connection.execute("SELECT 1")
        return {
            "status": "ok",
            "discord_ready": bot.is_ready(),
            "guild_count": len(bot.guilds),
            "uptime_seconds": int(time.time() - STARTED_AT),
        }, 200
    except Exception:
        log.exception("Health check failed")
        return {"status": "error"}, 503

def run_health() -> None:
    app.run(host="0.0.0.0", port=int(__import__("os").environ.get("PORT", "10000")), use_reloader=False)

db = Database(SETTINGS.database_path)
game = GameService(db)
intents = discord.Intents.default()
bot = commands.Bot(command_prefix=SETTINGS.command_prefix, intents=intents)


def guild_id(interaction: discord.Interaction) -> str:
    if interaction.guild_id is None:
        raise GameError("Lệnh này chỉ dùng được trong Discord server.")
    return str(interaction.guild_id)


def error_embed(message: str) -> discord.Embed:
    return discord.Embed(title="Không thể thực hiện", description=f"⚠️ {message}", color=0xE74C3C)


def resource_text(items: dict[str, int]) -> str:
    return " • ".join(f"{RESOURCE_NAMES.get(k, k)}: **{v}**" for k, v in items.items()) or "Chưa có"


@bot.event
async def on_ready() -> None:
    if SETTINGS.guild_id:
        guild = discord.Object(id=int(SETTINGS.guild_id))
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        log.info("Synced commands to guild %s", SETTINGS.guild_id)
    else:
        await bot.tree.sync()
    log.info("Logged in as %s", bot.user)


@bot.tree.command(name="start", description="Tạo nhân vật trong Làng Bình Minh")
@app_commands.describe(name="Tên nhân vật của bạn")
async def start(interaction: discord.Interaction, name: str) -> None:
    try:
        profile = game.register(guild_id(interaction), str(interaction.user.id), name)
        embed = discord.Embed(title="Chào mừng đến Làng Bình Minh", description=f"Nhân vật **{profile['character_name']}** đã sẵn sàng!", color=0x2ECC71)
        embed.add_field(name="Quà khởi đầu", value="🪵 Gỗ 20 • 🪨 Đá 10 • 🌾 Lương thực 10 • 💧 Nước 10 • 🪙 Vàng 100")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except GameError as e: await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)


@bot.tree.command(name="guide", description="Hướng dẫn tân thủ Làng Sinh Tồn")
async def guide(interaction: discord.Interaction) -> None:
    embed = discord.Embed(
        title="Hướng dẫn tân thủ — Làng Bình Minh",
        description="Chào mừng bạn đến với làng sinh tồn! Hãy làm theo các bước dưới đây để bắt đầu.",
        color=0x3498DB,
    )
    embed.add_field(
        name="1. Tạo nhân vật",
        value="Dùng `/start name:Tên_của_bạn` để nhận nhân vật và quà khởi đầu.",
        inline=False,
    )
    embed.add_field(
        name="2. Kiểm tra nhân vật",
        value="`/profile` xem level, XP, máu, năng lượng và vàng.\n`/inventory` xem tài nguyên và vật phẩm.",
        inline=False,
    )
    embed.add_field(
        name="3. Thu thập tài nguyên",
        value="Dùng `/gather` chọn Rừng, Mỏ đá, Đồng bằng hoặc Hồ nước. Mỗi lần thu thập tốn năng lượng và có cooldown.",
        inline=False,
    )
    embed.add_field(
        name="4. Phát triển làng",
        value="Dùng `/contribute` đưa tài nguyên vào kho chung, `/village` xem tiến trình và `/build` xây công trình.",
        inline=False,
    )
    embed.add_field(
        name="5. Nhận thưởng và nhiệm vụ",
        value="Dùng `/daily` mỗi ngày, `/quest` xem nhiệm vụ và `/explore` khám phá vùng hoang dã.",
        inline=False,
    )
    embed.add_field(
        name="6. Chế tạo và chiến đấu",
        value="Dùng `/craft` chế tạo, `/equip` trang bị, `/hunt` săn quái. Khi làng có boss, dùng `/boss` xem HP và `/boss-attack` cùng mọi người tấn công. PvP dùng `/pvp challenge`, nhưng trận chỉ bắt đầu khi đối phương `/pvp accept`.",
        inline=False,
    )
    embed.add_field(
        name="Mẹo quan trọng",
        value="Năng lượng và cooldown là giới hạn phía server. Hãy phối hợp đóng góp tài nguyên, không spam lệnh và xem `/leaderboard` để theo dõi thành tích.",
        inline=False,
    )
    embed.set_footer(text="Lệnh admin chỉ dành cho quản trị viên server.")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="profile", description="Xem hồ sơ nhân vật")
async def profile(interaction: discord.Interaction) -> None:
    try:
        p = game.profile(guild_id(interaction), str(interaction.user.id))
        embed = discord.Embed(title=f"Hồ sơ {p['character_name']}", color=0x3498DB)
        embed.add_field(name="Cấp độ", value=f"Level **{p['level']}** ({p['xp']}/{xp_needed(p['level'])} XP)")
        embed.add_field(name="Sinh tồn", value=f"Năng lượng **{p['energy']}/{p['max_energy']}**\nMáu **{p['hp']}/{p['max_hp']}**")
        embed.add_field(name="Tài sản", value=f"🪙 {p['gold']} vàng\n📦 Đã thu thập: {p['total_gathered']}\n🤝 Đóng góp làng: {p['village_contribution']}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except GameError as e: await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)


@bot.tree.command(name="inventory", description="Xem kho đồ")
async def inventory(interaction: discord.Interaction) -> None:
    try: await interaction.response.send_message(embed=discord.Embed(title="Kho đồ", description=resource_text(game.inventory(guild_id(interaction), str(interaction.user.id))), color=0xF1C40F), ephemeral=True)
    except GameError as e: await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)


@bot.tree.command(name="gather", description="Thu thập tài nguyên")
@app_commands.choices(zone=[app_commands.Choice(name=v["name"], value=k) for k, v in GATHER_ZONES.items()])
async def gather(interaction: discord.Interaction, zone: app_commands.Choice[str]) -> None:
    try:
        result = game.gather(guild_id(interaction), str(interaction.user.id), zone.value)
        embed = discord.Embed(title=f"Thu thập tại {result['zone']}", description=f"{resource_text(result['rewards'])}\n\n✨ +{result['xp']} XP\n⚡ Năng lượng còn lại: **{result['energy']}/100**", color=0x2ECC71)
        await interaction.response.send_message(embed=embed)
    except GameError as e: await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)


@bot.tree.command(name="daily", description="Nhận phần thưởng hằng ngày")
async def daily(interaction: discord.Interaction) -> None:
    try:
        r = game.daily(guild_id(interaction), str(interaction.user.id)); await interaction.response.send_message(embed=discord.Embed(title="Daily reward", description=f"🪙 Bạn nhận **{r['reward']} vàng**\n🔥 Chuỗi đăng nhập: **{r['streak']} ngày**", color=0xF1C40F), ephemeral=True)
    except GameError as e: await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)


@bot.tree.command(name="village", description="Xem thông tin làng")
async def village(interaction: discord.Interaction) -> None:
    try:
        v = game.village(guild_id(interaction)); b = " • ".join(f"{BUILDINGS[k]['name']}: cấp {level}" for k, level in v["buildings"].items() if level)
        embed = discord.Embed(title=v["name"], description=f"Cấp làng **{v['level']}** • XP **{v['xp']}** • Thành viên **{v['members']}**\n\nKho chung: {resource_text(v['storage'])}\n\nCông trình: {b or 'Chưa xây dựng'}", color=0x3498DB)
        await interaction.response.send_message(embed=embed)
    except GameError as e: await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)

@bot.tree.command(name="contribute", description="Đóng góp tài nguyên cho làng")
@app_commands.describe(resource="wood/stone/iron/food/water/herb/hide", amount="Số lượng")
async def contribute(interaction: discord.Interaction, resource: str, amount: app_commands.Range[int, 1, 10000]) -> None:
    try:
        r = game.contribute(guild_id(interaction), str(interaction.user.id), resource.lower(), amount); await interaction.response.send_message(f"🤝 Đã đóng góp **{r['amount']} {RESOURCE_NAMES[r['resource']]}** cho làng.")
    except GameError as e: await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)


@bot.tree.command(name="build", description="Xây hoặc nâng cấp công trình")
@app_commands.describe(building="house/storage/farm/workshop/wall/townhall")
async def build(interaction: discord.Interaction, building: str) -> None:
    try:
        r = game.build(guild_id(interaction), str(interaction.user.id), building.lower()); await interaction.response.send_message(embed=discord.Embed(title=f"Đã nâng cấp {r['name']}", description=f"Cấp mới: **{r['level']}**\nHiệu ứng: {r['effect']}", color=0x95A5A6))
    except GameError as e: await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)


@bot.tree.command(name="leaderboard", description="Xem bảng xếp hạng của server")
@app_commands.choices(metric=[app_commands.Choice(name="Level", value="level"), app_commands.Choice(name="Vàng", value="gold"), app_commands.Choice(name="Đóng góp làng", value="contribution"), app_commands.Choice(name="Thu thập", value="gathered")])
async def leaderboard(interaction: discord.Interaction, metric: app_commands.Choice[str] | None = None) -> None:
    try:
        rows = game.leaderboard(guild_id(interaction), metric.value if metric else "level")
        desc = "\n".join(f"**{i}.** {r['character_name']} — level {r['level']} • 🪙 {r['gold']} • 🤝 {r['village_contribution']}" for i, r in enumerate(rows, 1)) or "Chưa có người chơi."
        await interaction.response.send_message(embed=discord.Embed(title="Bảng xếp hạng server", description=desc, color=0x9B59B6))
    except GameError as e: await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)


@bot.tree.command(name="craft", description="Chế tạo vật phẩm")
@app_commands.describe(recipe="stone_axe/stone_pickaxe/iron_sword/health_potion")
async def craft(interaction: discord.Interaction, recipe: str) -> None:
    try:
        r = game.craft(guild_id(interaction), str(interaction.user.id), recipe.lower())
        await interaction.response.send_message(embed=discord.Embed(title=f"Đã chế tạo {r['name']}", description=f"Độ bền: **{r['durability']}**", color=0x95A5A6), ephemeral=True)
    except GameError as e: await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)


@bot.tree.command(name="equip", description="Trang bị một vật phẩm đã chế tạo")
@app_commands.describe(item="Mã vật phẩm, ví dụ stone_axe")
async def equip(interaction: discord.Interaction, item: str) -> None:
    try:
        game.equip(guild_id(interaction), str(interaction.user.id), item.lower())
        await interaction.response.send_message(f"🛡️ Đã trang bị **{item.lower()}**.", ephemeral=True)
    except GameError as e: await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)


@bot.tree.command(name="quest", description="Xem hoặc nhận nhiệm vụ")
@app_commands.describe(claim="Mã nhiệm vụ cần nhận thưởng, bỏ trống để xem danh sách")
async def quest(interaction: discord.Interaction, claim: str | None = None) -> None:
    try:
        if claim:
            r = game.claim_quest(guild_id(interaction), str(interaction.user.id), claim.lower())
            await interaction.response.send_message(f"🎯 Hoàn thành **{r['name']}** — nhận **{r['gold']} vàng** và **{r['xp']} XP**.", ephemeral=True)
            return
        rows = game.quests(guild_id(interaction), str(interaction.user.id))
        description = "\n".join(f"`{r['key']}` — {r['name']}: **{r['progress']}/{r['target']}** {'✅' if r['completed'] else ''}" for r in rows)
        await interaction.response.send_message(embed=discord.Embed(title="Nhiệm vụ", description=description, color=0x3498DB), ephemeral=True)
    except GameError as e: await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)


@bot.tree.command(name="explore", description="Khám phá vùng hoang dã")
@app_commands.choices(zone=[app_commands.Choice(name=name, value=key) for key, name in EXPLORE_ZONES.items()])
async def explore(interaction: discord.Interaction, zone: app_commands.Choice[str]) -> None:
    try:
        r = game.explore(guild_id(interaction), str(interaction.user.id), zone.value)
        await interaction.response.send_message(embed=discord.Embed(title=f"Khám phá {r['zone']}", description=f"🧭 {r['message']}", color=0x3498DB))
    except GameError as e: await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)


@bot.tree.command(name="hunt", description="Săn quái vật và nhận phần thưởng")
@app_commands.choices(enemy=[app_commands.Choice(name=v["name"], value=k) for k, v in ENEMIES.items()])
async def hunt(interaction: discord.Interaction, enemy: app_commands.Choice[str] | None = None) -> None:
    try:
        r = game.hunt(guild_id(interaction), str(interaction.user.id), enemy.value if enemy else None)
        title = "Chiến thắng!" if r["won"] else "Bạn đã thất bại"
        description = f"⚔️ {r['enemy']}\n**{r['rounds']} lượt** • Gây **{r['damage']}** sát thương • Nhận **{r['incoming']}** sát thương\n❤️ Máu còn: **{r['hp']}**"
        if r["won"]: description += f"\n\n🎁 Nhận **{r['reward_gold']} vàng** và XP chiến đấu."
        await interaction.response.send_message(embed=discord.Embed(title=title, description=description, color=0x2ECC71 if r["won"] else 0xE74C3C))
    except GameError as e: await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)


@bot.tree.command(name="boss", description="Xem boss chung của làng")
async def boss(interaction: discord.Interaction) -> None:
    try:
        r = game.boss_info(guild_id(interaction))
        status = "Cả server hãy dùng `/boss-attack` để cùng hạ boss!" if r["active"] else "Boss đã bị hạ. Admin có thể dùng `/admin event-start` để mở đợt mới."
        await interaction.response.send_message(embed=discord.Embed(title=f"Boss: {r['name']}", description=f"❤️ HP: **{r['hp']}/{r['max_hp']}**\n\n{status}\nPhần thưởng hạ gục: **{BOSS['reward_gold']} vàng** + tài nguyên hiếm.", color=0xE74C3C))
    except GameError as e: await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)


@bot.tree.command(name="boss-attack", description="Tấn công boss chung của làng")
async def boss_attack(interaction: discord.Interaction) -> None:
    try:
        r = game.attack_boss(guild_id(interaction), str(interaction.user.id))
        description = f"⚔️ Bạn gây **{r['damage']}** sát thương và nhận **{r['incoming']}** sát thương.\n❤️ Boss còn: **{r['hp']}/{BOSS['max_hp']}**"
        if r["defeated"]: description += f"\n\n🏆 **Boss đã bị đánh bại!** Bạn nhận **{r['reward_gold']} vàng**."
        await interaction.response.send_message(embed=discord.Embed(title="Đánh boss", description=description, color=0xF1C40F if r["defeated"] else 0xE74C3C))
    except GameError as e: await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)


pvp = app_commands.Group(name="pvp", description="Đấu PvP có sự đồng ý của cả hai người chơi")
bot.tree.add_command(pvp)


@pvp.command(name="challenge", description="Gửi lời mời PvP")
async def pvp_challenge(interaction: discord.Interaction, opponent: discord.Member) -> None:
    try:
        r = game.pvp_challenge(guild_id(interaction), str(interaction.user.id), str(opponent.id))
        await interaction.response.send_message(f"⚔️ {opponent.mention}, **{r['challenger_name']}** đã mời bạn PvP. Hai bên chỉ đấu khi bạn dùng `/pvp accept opponent:{interaction.user.mention}` trong vòng 120 giây.")
    except GameError as e: await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)


@pvp.command(name="accept", description="Đồng ý lời mời PvP và bắt đầu trận")
async def pvp_accept(interaction: discord.Interaction, opponent: discord.Member) -> None:
    try:
        r = game.pvp_accept(guild_id(interaction), str(interaction.user.id), str(opponent.id))
        await interaction.response.send_message(embed=discord.Embed(title="Kết quả PvP", description=f"⚔️ **{r['challenger_name']}** vs **{r['challenged_name']}**\n🏆 Người thắng: **{r['winner_name']}**\n🔁 Số lượt: **{r['rounds']}**\n🎁 Phần thưởng người thắng: **{r['reward_gold']} vàng**", color=0x9B59B6))
    except GameError as e: await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)


@pvp.command(name="decline", description="Từ chối lời mời PvP")
async def pvp_decline(interaction: discord.Interaction, opponent: discord.Member) -> None:
    try:
        game.pvp_decline(guild_id(interaction), str(interaction.user.id), str(opponent.id))
        await interaction.response.send_message("✅ Đã từ chối lời mời PvP.", ephemeral=True)
    except GameError as e: await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)


admin = app_commands.Group(name="admin", description="Công cụ quản trị Làng Sinh Tồn")
bot.tree.add_command(admin)


def require_admin(interaction: discord.Interaction) -> None:
    if str(interaction.user.id) in ADMIN_USER_IDS:
        return
    if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.administrator:
        raise GameError("Bạn cần quyền Administrator để dùng lệnh này.")


@admin.command(name="give", description="Cộng tài nguyên cho người chơi")
@app_commands.describe(user="Người nhận", resource="wood/stone/iron/food/water/herb/hide/gold", amount="Số lượng")
async def admin_give(interaction: discord.Interaction, user: discord.Member, resource: str, amount: app_commands.Range[int, 1, 1000000]) -> None:
    try:
        require_admin(interaction); game.admin_give(guild_id(interaction), str(user.id), resource.lower(), amount)
        await interaction.response.send_message(f"✅ Đã cộng **{amount} {RESOURCE_NAMES.get(resource.lower(), resource)}** cho {user.mention}.", ephemeral=True)
    except GameError as e: await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)


@admin.command(name="logs", description="Xem log giao dịch gần nhất")
async def admin_logs(interaction: discord.Interaction) -> None:
    try:
        require_admin(interaction); rows = game.admin_logs(guild_id(interaction))
        description = "\n".join(f"`{r['created_at']}` {r['action']} {r['resource'] or ''} {r['amount'] or ''}" for r in rows) or "Chưa có log."
        await interaction.response.send_message(embed=discord.Embed(title="Transaction logs", description=description, color=0x7F8C8D), ephemeral=True)
    except GameError as e: await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)


@admin.command(name="event-start", description="Bắt đầu lại sự kiện boss của làng")
async def admin_event_start(interaction: discord.Interaction) -> None:
    try:
        require_admin(interaction); r = game.start_boss(guild_id(interaction))
        await interaction.response.send_message(f"📣 Đã triệu hồi **{r['name']}** với **{r['max_hp']} HP**.", ephemeral=True)
    except GameError as e: await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)


@admin.command(name="village-reset", description="Reset dữ liệu làng của server")
async def admin_village_reset(interaction: discord.Interaction) -> None:
    try:
        require_admin(interaction); game.admin_reset(guild_id(interaction))
        await interaction.response.send_message("⚠️ Đã reset làng và toàn bộ nhân vật trong server.", ephemeral=True)
    except GameError as e: await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)


@bot.tree.error
async def on_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    log.exception("Command error", exc_info=error)
    message = "Đã xảy ra lỗi hệ thống. Vui lòng thử lại sau."
    if not interaction.response.is_done(): await interaction.response.send_message(embed=error_embed(message), ephemeral=True)

if __name__ == "__main__":
    if not SETTINGS.token: raise RuntimeError("Thiếu DISCORD_TOKEN trong file .env")
    threading.Thread(target=run_health, daemon=True).start()
    bot.run(SETTINGS.token)
