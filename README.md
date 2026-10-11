# Làng Sinh Tồn — Discord Bot MVP

Bot mini game sinh tồn nhiều người chơi: mỗi Discord server có một làng và kho chung riêng; mỗi cặp `guild_id + user_id` có tiến trình riêng.

## Quyết định kỹ thuật

Repository ban đầu là Python/discord.py, vì vậy MVP giữ hệ sinh thái hiện tại thay vì chuyển đột ngột sang Node.js. Dữ liệu dùng **SQLite** để chạy local không cần dịch vụ ngoài; lớp `Database` dùng transaction `BEGIN IMMEDIATE`, khóa ngoại, CHECK quantity >= 0 và schema có thể chuyển sang PostgreSQL ở giai đoạn tiếp theo.

## Đã hoàn thành

- `/start` đăng ký nhân vật theo từng server, quà khởi đầu và chống đăng ký trùng.
- `/guide` hướng dẫn tân thủ bằng Embed tiếng Việt, hiển thị riêng tư.
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
- `/hunt` combat nhiều lượt với quái vật, sát thương, HP, XP, vàng, loot và độ bền vũ khí.
- `/boss`, `/boss-attack` boss chung theo server; toàn bộ người chơi cùng gây sát thương trong transaction.
- `/pvp challenge`, `/pvp accept`, `/pvp decline`; trận chỉ bắt đầu sau khi người được mời chủ động accept.
- `/admin give`, `/admin logs`, `/admin event-start`, `/admin village-reset` với kiểm tra quyền Administrator.
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
- `ADMIN_USER_IDS`: danh sách ID Discord admin, phân tách bằng dấu phẩy. Mặc định đã có `1026417896114630676`; admin ID này được dùng lệnh admin kể cả khi không có quyền Administrator trong server.

## Setup Discord bot lần đầu

1. Mở [Discord Developer Portal](https://discord.com/developers/applications) và chọn **New Application**.
2. Vào **Bot → Add Bot**, sau đó dùng **Reset Token** và lưu token ở nơi an toàn. Không gửi token vào chat hoặc commit vào Git.
3. Vào **OAuth2 → URL Generator**, chọn scopes `bot` và `applications.commands`.
4. Chọn quyền tối thiểu `View Channels`, `Send Messages` và `Embed Links`, mở URL được tạo rồi mời bot vào server.
5. Lấy **Application ID** làm `DISCORD_CLIENT_ID` và lấy **Server ID** làm `DISCORD_GUILD_ID` nếu muốn sync command nhanh trong server test.

## Deploy Render để bot chạy liên tục

Repository đã có [`render.yaml`](./render.yaml). File này cấu hình Docker web service, health check `/health` và volume `/app/data` để giữ SQLite database qua lần restart.

1. Push repository lên GitHub (đã hoàn thành).
2. Trong Render chọn **New → Blueprint**, kết nối repository `vuducanh22082009-design/lang-sinh-ton-`.
3. Kiểm tra service `village-survival-bot` được đọc từ `render.yaml`.
4. Khi Render hỏi secret, điền `DISCORD_TOKEN` trực tiếp trong ô secret của Render; không ghi vào `render.yaml`.
5. Điền `DISCORD_CLIENT_ID` và `DISCORD_GUILD_ID` nếu có. Giữ `DATABASE_PATH=/app/data/survival.db` để volume được sử dụng.
6. Deploy và kiểm tra log phải có `Logged in as ...`.
7. Kiểm tra health URL của service: `/health` phải trả JSON có `status: ok` và `discord_ready: true`.

Không đổi service sang loại không có volume nếu muốn giữ dữ liệu game. Khi chuyển sang PostgreSQL production, thay `Database` bằng repository PostgreSQL và dùng `DATABASE_URL` thay cho SQLite.

## Cấu hình UptimeRobot

UptimeRobot chỉ dùng để kiểm tra HTTP health endpoint; nó không thay thế Render và không khởi động bot nếu Render service đã dừng.

1. Trong Render, mở service và copy **Public URL**, ví dụ `https://village-survival-bot.onrender.com`.
2. Tạo monitor mới trên [UptimeRobot](https://uptimerobot.com/).
3. Chọn loại **HTTP(s)**.
4. Đặt URL monitor là:

```text
https://<ten-service>.onrender.com/health
```

5. Chọn chu kỳ kiểm tra phù hợp, ví dụ 5 phút, rồi lưu monitor.
6. Khi endpoint trả HTTP `200` và JSON có `"status": "ok"`, monitor sẽ báo UP.

Không đặt `DISCORD_TOKEN` vào UptimeRobot. Token chỉ được lưu trong Render Environment.

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
8. Dùng `/hunt enemy:Sói hoang` để chiến đấu; dùng `/boss` xem boss chung và `/boss-attack` để góp sát thương.
9. Khi boss bị hạ, admin có thể dùng `/admin event-start` để mở đợt boss mới.
10. PvP: dùng `/pvp challenge opponent:@NguoiChoi`; đối phương dùng `/pvp accept opponent:@Ban` để đồng ý, hoặc `/pvp decline` để từ chối.

## Cấu trúc

```text
bot.py                    # Discord adapter và slash commands
survival_bot/config.py    # config gameplay, tên tài nguyên, chi phí
survival_bot/db.py        # SQLite schema và transaction
survival_bot/service.py   # nghiệp vụ game, không phụ thuộc Discord
tests/test_game.py        # unit tests
```

## Chưa làm / hướng mở rộng

- PostgreSQL/Prisma tương đương cho production, Redis distributed cooldown.
- Các event server thời gian thực ngoài boss, combat PvE nâng cao và boss nhiều giai đoạn.
- Role admin cấu hình riêng, phân trang Button/Select Menu/Modal nâng cao.
- Hồi năng lượng theo thời gian, công thức level làng, nhiệm vụ và snapshot leaderboard.
- Deploy worker/health monitoring production và migration tool.

Các thao tác tài sản quan trọng đã đi qua transaction và server-side validation; không có tiền thật hoặc thanh toán.
