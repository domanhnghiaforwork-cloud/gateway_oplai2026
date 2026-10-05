# Chạy system và chatbot trên một domain ngrok

Thư mục gateway trên Windows: `D:\nghia\oplai2026\system\gateway_oplai2026`. Trên Linux, ví dụ: `~/nghia/olpai2026/system/gateway_oplai2026`.

Đã build và chạy thử trên máy này ngày 05/10/2026: hai ứng dụng trả HTTP 200 qua domain public, API system và chatbot đi đúng backend, PostgreSQL/Redis sẵn sàng, SSE có xác thực truyền được qua Nginx. Hệ thống đang dùng authtoken chatbot hiện có trong `.env` riêng của gateway.

| Địa chỉ | Ứng dụng |
| --- | --- |
| `https://larcher-brecken-palynologically.ngrok-free.dev/` | System OLP AI |
| `https://larcher-brecken-palynologically.ngrok-free.dev/chatbot` | Chatbot |
| `http://localhost:8080/` | System qua gateway tại máy local |
| `http://localhost:8080/chatbot` | Chatbot qua gateway tại máy local |
| `http://localhost:3001/` | Frontend system trực tiếp |
| `http://localhost:3000/chatbot` | Frontend chatbot trực tiếp |
| `http://localhost:4040/` | Ngrok inspector |

## Chạy trên Linux (Ubuntu)

Các script `.ps1` chạy bằng PowerShell 7 trên Linux. Dùng lệnh `pwsh`, đường dẫn `./start.ps1` và không cần `-ExecutionPolicy Bypass`. Những ví dụ `powershell ... .\start.ps1` ở các mục bên dưới dành cho Windows.

### Chuẩn bị một lần

1. Cài và khởi động Docker Engine hoặc Docker Desktop. Docker Compose cần phiên bản >= 2.24.4 để đọc cấu hình override. Kiểm tra tài khoản hiện tại truy cập Docker được:

   ```bash
   docker info
   docker compose version
   ```

2. Cài PowerShell qua Snap và kiểm tra phiên bản:

   ```bash
   sudo snap install powershell --classic
   pwsh --version
   ```

   Nếu Snap báo `classic confinement`, cần thêm `--classic` như lệnh trên. Tùy chọn này cho phép PowerShell hoạt động ngoài sandbox mặc định của Snap. Xem [hướng dẫn cài PowerShell của Microsoft](https://learn.microsoft.com/en-us/powershell/scripting/install/alternate-install-methods?view=powershell-7.6#installation-via-snap).

3. Vào thư mục gateway và mở cấu hình. Chỉ chép file example nếu chưa có `.env`:

   ```bash
   cd ~/nghia/olpai2026/system/gateway_oplai2026
   if [ ! -f .env ]; then
       cp .env.example .env
   fi
   nano .env
   ```

   Điền `NGROK_DOMAIN` và `NGROK_AUTHTOKEN` để dùng domain public. Domain không có `https://` hoặc dấu `/`. Đồng thời chuẩn bị `.env` và `backend/.env` của chatbot theo các file example; giữ thông tin PostgreSQL khớp với dữ liệu hiện có. Để `CHATBOT_SSO_SECRET` trống khi thiết lập mới: `start.ps1` tự tạo, lưu vào `.env` gateway và truyền cùng khóa cho hai backend.

### Khởi động, kiểm tra và dừng

Chạy các lệnh sau từ thư mục gateway trong terminal Linux:

| Thao tác | Lệnh |
| --- | --- |
| Chạy lần đầu hoặc sau khi sửa mã nguồn | `pwsh -NoProfile -File ./start.ps1 -Build` |
| Chạy lại bằng image đã build | `pwsh -NoProfile -File ./start.ps1` |
| Chạy local, không mở ngrok | `pwsh -NoProfile -File ./start.ps1 -Build -LocalOnly` |
| Xem trạng thái | `pwsh -NoProfile -File ./status.ps1` |
| Nhập tài khoản chatbot hiện có sang system | `pwsh -NoProfile -File ./sync-accounts.ps1` |
| Dừng toàn bộ, giữ dữ liệu | `pwsh -NoProfile -File ./stop.ps1` |

Chế độ local mở tại `http://localhost:8080/` và `http://localhost:8080/chatbot` (nếu giữ `GATEWAY_PORT=8080`). Chạy public bằng lệnh không có `-LocalOnly`. Việc tự tạo tài khoản chatbot từ system và SSO dùng chung cấu hình gateway trên cả Windows và Linux.

Xem log Nginx/ngrok:

```bash
docker compose --profile tunnel logs --tail 100 nginx ngrok
```

Xem log chatbot:

```bash
docker compose --project-directory ../chatbot_oplai2026/chat_bot_allforn --env-file ../chatbot_oplai2026/chat_bot_allforn/.env -f ../chatbot_oplai2026/chat_bot_allforn/compose.yaml -f ./chatbot.override.yaml logs --tail 100 frontend backend worker
```

Xem log system:

```bash
docker compose --project-directory ../system_olpai2026 -p system_olpai2026 -f ../system_olpai2026/docker-compose.yml -f ./system.override.yaml logs --tail 100 frontend backend
```

Thêm `-f` ngay sau `logs` để theo dõi liên tục; nhấn `Ctrl+C` để thoát theo dõi mà không dừng ứng dụng.

### Kiểm tra tài khoản và SSO

Sau khi khởi động hai ứng dụng và nhập tài khoản chatbot sang system, kiểm tra SSO bằng Python 3 trên máy host. Lệnh dưới đặt alias `python` thành `python3` trong phiên PowerShell vì `verify-sso.ps1` gọi `python`:

```bash
pwsh -NoProfile -Command 'Set-Alias python python3; & ./verify-sso.ps1'
```

Kiểm thử cơ chế tự tạo tài khoản trên database tạm, không cần Docker hoặc khóa thật (Python đã cài dependencies xác thực của hai backend và `aiosqlite`):

```bash
python3 ./test_account_sync.py
```

## Chuẩn bị một lần trên Windows

1. Mở Docker Desktop, đợi Docker Engine sẵn sàng. Cần Docker Compose >= 2.24.4 (cấu hình override cổng); máy hiện tại đã có phiên bản phù hợp.
2. Mở PowerShell và vào thư mục gateway:

   ```powershell
   cd D:\nghia\oplai2026\system\gateway_oplai2026
   ```

3. Mở cấu hình ngrok:

   ```powershell
   notepad .env
   ```

   File `.env` đã được chuẩn bị tại máy này. Kiểm tra `NGROK_DOMAIN` đúng static domain và `NGROK_AUTHTOKEN` là authtoken của tài khoản sở hữu domain đó. Domain viết không có `https://` hoặc dấu `/`. Không cần chạy ngrok riêng ở terminal.

   Nếu chuyển sang máy mới và chưa có file này:

   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```

   Đồng thời cấu hình `.env` và `backend/.env` của chatbot theo các file example. Giữ thông tin PostgreSQL khớp với database hiện có. Không cần chép `.env` của system sang chatbot.

## Chạy lần đầu hoặc sau khi sửa mã nguồn

Tại thư mục gateway_oplai2026:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1 -Build
```

Lệnh này:

- Kiểm tra Docker và cấu hình Compose.
- Tạo mạng dùng chung `oplai_gateway` và mạng đồng bộ backend `oplai_accounts` nếu chưa có.
- Dừng ngrok cũ trong project chatbot để tránh chiếm domain/cổng 4040.
- Build image và chạy system, chatbot cùng PostgreSQL, Redis, worker; bước migrate của chatbot chạy theo compose hiện có.
- Chạy Nginx, đợi API hai ứng dụng sẵn sàng.
- Chạy một ngrok tunnel trỏ vào Nginx và xác nhận tunnel đã mở đúng domain.

`-ExecutionPolicy Bypass` chỉ áp dụng cho tiến trình PowerShell của lệnh này. `-Build` cần ở lần chạy đầu để chatbot được build với `/chatbot`.

Sau khi script báo thành công, mở hai địa chỉ public ở bảng trên. Hai ứng dụng giữ phiên đăng nhập riêng; gateway bật SSO và tự tạo tài khoản chatbot cho tài khoản mới được tạo trong system như mô tả ở mục **Tài khoản dùng chung và mở Chatbot**.

Nếu ngrok hiện trang xác nhận lần đầu, bấm **Visit Site** để vào ứng dụng. Đã kiểm tra trang đăng nhập chatbot và giao diện system bằng trình duyệt qua domain public sau bước này.

## Chạy những lần sau

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1
```

Khởi động bằng image đã build, nhanh hơn. Nếu sửa mã nguồn hoặc cấu hình build của chatbot, dùng lại `-Build`.

Chỉ kiểm tra trên máy local, chưa mở ngrok:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1 -Build -LocalOnly
```

Mở `http://localhost:8080/` và `http://localhost:8080/chatbot`. Để chuyển từ local sang public, chạy `start.ps1` không có `-LocalOnly`.

## Kiểm tra trạng thái và log

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\status.ps1
```

Hiển thị trạng thái của cả hai project và gateway. Container `migrate` của chatbot kết thúc với mã `0` là bình thường.

Log Nginx/ngrok:

```powershell
docker compose --profile tunnel logs --tail 100 nginx ngrok
```

Log chatbot:

```powershell
docker compose --project-directory ..\chatbot_oplai2026\chat_bot_allforn --env-file ..\chatbot_oplai2026\chat_bot_allforn\.env -f ..\chatbot_oplai2026\chat_bot_allforn\compose.yaml -f .\chatbot.override.yaml logs --tail 100 frontend backend worker
```

Log system:

```powershell
docker compose --project-directory ..\system_olpai2026 -p system_olpai2026 -f ..\system_olpai2026\docker-compose.yml -f .\system.override.yaml logs --tail 100 frontend backend
```

Thêm `-f` ngay sau `logs` để theo dõi liên tục; nhấn `Ctrl+C` để thoát theo dõi mà không dừng ứng dụng.

## Dừng toàn bộ

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\stop.ps1
```

Dừng system, chatbot và gateway; giữ container và volume dữ liệu để lần sau khởi động lại.

## Cách cấu hình hoạt động

Nginx chuyển `/chatbot` và `/chatbot/...` tới `chatbot-web:3000`, giữ nguyên tiền tố. Các đường dẫn còn lại tới `system-web:3000`. Hai frontend tự chuyển API tới backend trong mạng riêng. SSE của chatbot đi qua Nginx với buffering tắt; Nginx cho phép request body tối đa 100 MB (ứng dụng phía sau có thể có giới hạn riêng).

Các file `system.override.yaml` và `chatbot.override.yaml` chỉ áp dụng khi chạy bằng các script ở đây. Chúng thay thế cổng host của system thành `3001`, chatbot thành `3000`, và kết nối hai frontend vào mạng gateway. Hai backend có thêm mạng nội bộ `oplai_accounts` để đồng bộ tài khoản trực tiếp; PostgreSQL, Redis và worker vẫn ở mạng riêng của chatbot. Cấu hình Compose gốc vẫn dùng để chạy từng repo độc lập. Trong chế độ chạy chung, luôn dùng script để giữ đúng các override.

Script giữ tên project system là `system_olpai2026`; chatbot dùng `COMPOSE_PROJECT_NAME` từ `.env` hiện có (`chatbot-v42`). Vì vậy các volume `system_olpai2026_backend_data`, `chatbot-v42_postgres-data` và `chatbot-v42_redis-data` được dùng lại. Khi di chuyển thư mục, giữ nguyên tên project để tiếp tục dùng đúng dữ liệu.

Chatbot hỗ trợ `NEXT_PUBLIC_BASE_PATH` khi build. Chạy chung: `/chatbot`; chạy độc lập theo compose gốc: để `CHATBOT_BASE_PATH` trống và build lại frontend. Local development: để `NEXT_PUBLIC_BASE_PATH` trống trong `frontend/.env.local`. Đổi base path cần build lại, không chỉ restart container.

Trong lần triển khai này, database SQLite trong volume system cũ thiếu `problems.category` và `problems.pdf_filename`. Backend đã được bổ sung migration tự động trước bước seed; đề có mã `NLP-*` được gán nhóm `NLP`, các đề còn lại mặc định `CV`. Bản sao database trước khi bổ sung hai cột nằm trong `system_olpai2026/backups/pre-gateway-20261005-144530/`. Migration chỉ thêm các cột còn thiếu và có thể chạy lại.

Nếu ngrok không mở được domain, xem log ngrok và kiểm tra domain/authtoken trong `.env`. Dừng các tiến trình ngrok khác đang chiếm domain. Nếu thấy `port is already allocated`, kiểm tra `docker ps` và tiến trình đang dùng cổng `3000`, `3001`, `8080` hoặc `4040`. Đổi `GATEWAY_PORT`/`NGROK_INSPECTOR_PORT` trong `.env` khi cần; hai cổng frontend được đặt trong các file override.

## Tài khoản dùng chung và mở Chatbot

Trong PowerShell, vào thư mục gateway rồi dựng và chạy cả hai ứng dụng:

```powershell
cd D:\nghia\oplai2026\system\gateway_oplai2026
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1 -Build
```

`-Build` dựng lại image để cài hỗ trợ mật khẩu Argon2 cho system và cập nhật trang đăng nhập liên kết của chatbot. Những lần chạy sau, bỏ `-Build` nếu mã nguồn không thay đổi.

Khi chạy chung qua gateway, tạo tài khoản trong trang quản trị system (đơn lẻ hoặc hàng loạt) tự động lưu yêu cầu tạo tài khoản chatbot trong cùng giao dịch SQLite. Backend system xử lý yêu cầu ở nền khoảng mỗi 2 giây, tối đa 25 tài khoản mỗi lượt. Không cần bấm biểu tượng Chatbot để kích hoạt. Tài khoản mới bên chatbot dùng email chuẩn hóa chữ thường, mật khẩu được cấp ở system và quyền admin/user tương ứng; chatbot đăng nhập bằng **email**, không phải username system. Chỉ hash Argon2 được gửi qua API nội bộ với vé ký có hạn 60 giây; API này không cấp token đăng nhập.

Nếu chatbot chưa chạy hoặc mất kết nối, thao tác tạo tài khoản system vẫn thành công. Yêu cầu còn trong bảng `chatbot_provision_jobs` và được thử lại với thời gian chờ tăng dần từ 5 giây đến tối đa 5 phút, kể cả sau khi khởi động lại backend system. Khi chatbot hoạt động trở lại, các yêu cầu được xử lý tiếp. `attempts`, `next_attempt_at` và `last_error` giúp theo dõi yêu cầu chưa hoàn thành; mã lỗi không chứa mật khẩu hoặc nội dung vé.

Nếu email đã có trong chatbot, giữ nguyên mật khẩu và quyền hiện tại, không ghi đè. Đồng bộ lặp lại không tạo tài khoản trùng. Cơ chế này chỉ áp dụng cho tài khoản **mới được tạo** qua quản trị system sau khi bật; không nhập tự động tài khoản system cũ, không đồng bộ thao tác sửa mật khẩu/email/quyền hoặc xóa tài khoản. Nếu xóa tài khoản system trước khi gửi yêu cầu thì yêu cầu chờ cũng bị xóa.

Đồng bộ chỉ bật khi cả hai backend nhận `CHATBOT_ACCOUNT_SYNC_ENABLED=true` và khóa `CHATBOT_SSO_SECRET` đủ dài; system còn cần `CHATBOT_INTERNAL_URL` (gateway cấu hình `http://chatbot-api:8000`). Compose gốc không bật cơ chế này. Khi chạy độc lập, không có tác vụ đồng bộ hoặc yêu cầu gọi hệ thống còn lại; đăng nhập thông thường và SSO hiện có giữ nguyên hành vi.

Đăng nhập chatbot kiểm tra mật khẩu đã cấp, hỗ trợ cả mật khẩu system ngắn hơn 8 ký tự hoặc dài hơn 128 ký tự. Đăng ký tài khoản mới trực tiếp trên chatbot vẫn yêu cầu mật khẩu từ 8 đến 128 ký tự.

Đồng bộ toàn bộ tài khoản chatbot hiện có sang system:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\sync-accounts.ps1
```

Lệnh này giữ email, mật khẩu và quyền admin/user cho tài khoản mới. Mật khẩu được sao chép dưới dạng hash, không có mật khẩu thô trong log hay file trên máy host. Đăng nhập system bằng email và mật khẩu đang dùng ở chatbot; script cũng hiển thị username system được tạo. Tài khoản system trùng email được giữ nguyên cả mật khẩu và quyền. Chạy lại script sẽ bỏ qua các email đã có. Script sao lưu SQLite vào `pre-chatbot-sync-*.db` trong volume backend trước mỗi lần nhập; thông báo cuối lệnh ghi đường dẫn bản sao.

Mở `https://larcher-brecken-palynologically.ngrok-free.dev/`, đăng nhập system rồi bấm **Chatbot** ở góc phải. Tab mới sẽ:

- Đăng nhập bằng email của tài khoản system hiện tại, thay thế phiên chatbot cũ kể cả khi phiên đó còn hợp lệ. Các tab chatbot khác trong cùng trình duyệt cập nhật theo tài khoản mới.
- Nếu email system chưa có trong chatbot (ví dụ tài khoản system cũ chưa được đồng bộ), SSO vẫn tạo tài khoản chatbot tương ứng với quyền từ system. Tài khoản tạo theo luồng SSO dự phòng này có mật khẩu ngẫu nhiên không được cung cấp. Nếu tài khoản đã được tạo bởi đồng bộ nền, mật khẩu được cấp ở system vẫn được giữ nguyên. Với các tài khoản được sao chép từ chatbot, mật khẩu chatbot hiện tại vẫn giữ nguyên.
- Khi system chưa đăng nhập, mở chatbot như trước để người dùng đăng nhập trực tiếp.

`start.ps1` tự tạo khóa SSO riêng trong `.env` của gateway và truyền cùng khóa cho hai backend qua các override. Vé do backend system cấp có hạn 60 giây, dùng một lần, kiểm tra chữ ký, mục đích, bên cấp và bên nhận. Vé đi trong fragment `#ticket=...`, được xóa ngay khi trang nhận tải, không truyền mật khẩu hoặc token phiên system qua URL. Không chia sẻ `.env` hoặc khóa này.

Khi chạy chung qua gateway, đăng xuất system sẽ xóa phiên chatbot trong cùng trình duyệt và chuyển các tab chatbot đang mở về trang đăng nhập. Đăng nhập hoặc chuyển sang tài khoản system khác cũng xóa phiên chatbot cũ; lần bấm **Chatbot** tiếp theo đăng nhập đúng tài khoản system mới. Khi SSO đang chờ phản hồi mà người dùng đăng xuất, phản hồi đến muộn không khôi phục phiên đã xóa. Đăng xuất riêng ở chatbot không đăng xuất system.

Trên domain gateway, hai ứng dụng dùng sự kiện thay đổi browser storage để cập nhật giữa các tab. Trong chế độ `-LocalOnly`, system và chatbot ở hai cổng khác nhau nên system dùng iframe `/chatbot/session-bridge` và `postMessage` để yêu cầu xóa phiên. Bridge chỉ nhận yêu cầu từ trang cha có origin được cấu hình trong `SYSTEM_SSO_ORIGINS`; `start.ps1` tự truyền domain public, cổng gateway và cổng frontend system local vào biến runtime của frontend chatbot. Chỉ thông báo xóa phiên được gửi qua bridge, không có mật khẩu hoặc token. Bridge không bật khi chạy chatbot bằng Compose gốc.

Nếu đang ở chế độ `-LocalOnly`, nút Chatbot mở `http://localhost:3000/chatbot` và SSO cũng hoạt động giữa các cổng khác nhau. Sau khi cập nhật cơ chế đồng bộ phiên, chạy `start.ps1 -Build` và tải lại các tab system/chatbot đang mở để dùng mã frontend mới. Đăng nhập riêng khi chạy từng hệ thống độc lập vẫn hoạt động như trước.

Compose gốc của mỗi repo không bật SSO. Các tài khoản được nhập vẫn đăng nhập system độc lập bằng email và mật khẩu chatbot. Khi chuyển chatbot từ gateway sang chạy độc lập, dựng lại frontend với `CHATBOT_BASE_PATH` trống như hướng dẫn ở trên.

Kiểm tra lại tích hợp SSO sau khi chạy và đồng bộ (cần Python 3 trên Windows):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\verify-sso.ps1
```

Lệnh kiểm tra tài khoản đã nhập, mật khẩu Argon2/PBKDF2/cũ, từ chối yêu cầu chưa đăng nhập, vé sai chữ ký/mục đích/bên cấp/bên nhận/hết hạn, vé dùng lại và đổi vé đồng thời. Nó không đổi mật khẩu hoặc tạo tài khoản thử trong database đang chạy. Token kiểm tra chỉ giữ trong bộ nhớ, không in ra terminal.

Kiểm thử đồng bộ tài khoản trên cơ sở dữ liệu tạm, không cần Docker hoặc khóa thật (Python đã cài dependencies xác thực của hai backend và `aiosqlite`):

```powershell
python .\test_account_sync.py
```

Các bài kiểm thử gọi API thật qua ASGI ở hai tiến trình riêng: tạo đơn lẻ/hàng loạt, đăng nhập bằng mật khẩu chung, tác vụ nền, mất kết nối/khởi động lại, mất phản hồi sau khi chatbot đã tạo tài khoản, giữ nguyên tài khoản chatbot cũ, giao dịch rollback/xóa, chạy độc lập và kiểm tra chữ ký/mục đích/hạn dùng của vé.

Kiểm thử đổi tài khoản và đăng xuất giữa các tab nằm trong `test_session_sync.cjs`, với API fixture `test_session_backend.py`. Các fixture dùng database và khóa tạm; không dùng dữ liệu đang chạy. Script trình duyệt cần Playwright, TypeScript của frontend system và frontend chatbot test chạy ở cổng 4130; xem phần đầu hai file để cấu hình các cổng và dependencies. Nó kiểm tra SSO thay phiên cũ, logout qua hai cổng/cùng origin, đổi tài khoản và các phản hồi SSO/401 đến muộn.

cấu trúc thư mục
system
   chatbot_oplai2026
      chat_bot_allforn
   gateway_oplai2026
   system_oplai2026
