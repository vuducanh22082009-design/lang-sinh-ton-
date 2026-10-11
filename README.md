# Làng Sinh Tồn — Discord Bot MVP

Bot mini game sinh tồn nhiều người chơi: mỗi Discord server có một làng và kho chung riêng; mỗi cặp `guild_id + user_id` có tiến trình riêng.

## Quyết định kỹ thuật

Repository ban đầu là Python/discord.py, vì vậy MVP giữ hệ sinh thái hiện tại thay vì chuyển đột ngột sang Node.js. Dữ liệu dùng **SQLite** để chạy local không cần dịch vụ ngoài; lớp `Database` dùng transaction `BEGIN IMMEDIATE`, khóa ngoại, CHECK quantity >= 0 và schema có thể chuyển sang PostgreSQL ở giai đoạn tiếp theo.

Mã bot cũ được giữ tại `legacy_bot.py` để có thể tham khảo hoặc rollback.

## Đã hoàn thành

- `/start` đăng ký nhân vật theo từng server, quà khởi đầu và chống đăng ký trùng.
- `/profile`, `/inventory`.
- `/gather` với 4 khu vực, năng lượng, random reward, XP và cooldown phía server.
- `/daily` với streak giới hạn 7 ngày, UTC và chống nhận hai lần.
- `/village` xem làng, kho chung và công trình.
- `/contribute` đóng góp tài nguyên bằng transaction, kiểm tra số dư và log.
- `/build` nâng cấp 6 loại công trình với chi phí từ config.
- `/leaderboard` theo server.
- `/craft`, `/equip` với recipe, vật phẩm, độ bền và trạng thái trang bị.
- `/quest` với nhiệm vụ cá nhân và phần thưởng vàng/XP.
- `/explore` với phần thưởng, túi vàng và bẫy, kèm cooldown.
- `/admin give`, `/admin logs`, `/admin village-reset` với kiểm tra quyền Administrator.
- Structured logging cơ bản, endpoint health `/`, xử lý lỗi thân thiện.
- Unit test cho đăng ký, cooldown, daily, tách server, đóng góp, race condition, craft và explore.

## Chạy local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# điền DISCORD_TOKEN; có thể điền DISCORD_GUILD_ID để sync command nhanh trong server test
python bot.py
```

Bot cần scope `bot` và `applications.commands`; permissions MVP có thể dùng `Send Messages`, `Embed Links`.

- `DISCORD_TOKEN`: token bot, không commit.
- `DISCORD_CLIENT_ID`: để quản lý cấu hình; không cần trong runtime hiện tại.
- `DISCORD_GUILD_ID`: tùy chọn, sync command tức thì cho một server test. Bỏ trống để sync global.
- `DATABASE_PATH`: mặc định `survival.db`.

## Kiểm thử

```bash
pytest -q
```

## Cách chơi nhanh

1. Mời bot vào server.
2. Dùng `/start name:An`.
3. Dùng `/gather` chọn Rừng/Mỏ đá/Đồng bằng/Hồ nước.
4. Dùng `/inventory`, `/profile`, `/daily`.
5. Dùng `/contribute resource:wood amount:10` để đưa tài nguyên vào kho làng.
6. Dùng `/village` và `/build building:house` để kiểm tra/nâng cấp.
7. Dùng `/leaderboard` xem xếp hạng riêng của server.

## Cấu trúc

```text
bot.py                    # Discord adapter và slash commands
survival_bot/config.py    # config gameplay, tên tài nguyên, chi phí
survival_bot/db.py        # SQLite schema và transaction
survival_bot/service.py   # nghiệp vụ game, không phụ thuộc Discord
tests/test_game.py        # unit tests
legacy_bot.py             # bot cũ từ repository trước MVP
```

## Chưa làm / hướng mở rộng

- PostgreSQL/Prisma tương đương cho production, Redis distributed cooldown.
- Combat, `/event` và các event server thời gian thực.
- Role admin cấu hình riêng, phân trang Button/Select Menu/Modal nâng cao.
- Hồi năng lượng theo thời gian, công thức level làng, nhiệm vụ và snapshot leaderboard.
- Deploy worker/health monitoring production và migration tool.

Các thao tác tài sản quan trọng đã đi qua transaction và server-side validation; không có tiền thật hoặc thanh toán.
