# Kết quả kiểm tra ngày 05/10/2026

## Đồng bộ đăng xuất và đổi tài khoản (06/10/2026)

- `test_session_sync.cjs`: PASS cho SSO thay thế phiên chatbot còn hợp lệ của tài khoản khác; các tab chatbot khác cập nhật theo tài khoản mới.
- Đăng xuất system chuyển hai tab chatbot đang mở về login và xóa phiên; đăng nhập system bằng tài khoản B rồi mở chatbot nhận đúng tài khoản B. Đã kiểm tra cả browser storage cùng origin và bridge giữa hai cổng localhost.
- Logout trong lúc SSO đang chờ không cho phản hồi đến muộn khôi phục phiên. Phản hồi 401 bị trì hoãn của tài khoản A không xóa phiên mới của tài khoản B.
- Chế độ độc lập không kích hoạt reset; route bridge trả 404 khi không có `SYSTEM_SSO_ORIGINS`. Bridge ở chế độ tích hợp kiểm tra origin trang cha, có CSP `frame-ancestors` và response `no-store`; không có lỗi JavaScript trong các bài kiểm thử trình duyệt.
- Kiểm thử chạy frontend chatbot thật với harness sử dụng trực tiếp mã API/session của frontend system, hai API xác thực thật trên SQLite tạm và replay guard Redis giả trong fixture. Không dùng dữ liệu, khóa hoặc container đang chạy. Agent Browser xác nhận trang login chatbot hiển thị, có các trường/button và không có error overlay. Chưa kiểm tra lại giao diện system đầy đủ hoặc mạng/container Docker trong lần này.
- TypeScript của cả hai frontend, Compose merge và cú pháp `start.ps1` PASS; ESLint module đồng bộ và Navbar không có lỗi, còn ba cảnh báo unused có sẵn trong Navbar.
- Cần chạy `start.ps1 -Build` rồi tải lại các tab đang mở để áp dụng. Trên Linux: `pwsh -NoProfile -File ./start.ps1 -Build`.

## Tự tạo tài khoản chatbot khi tạo tài khoản system (bổ sung)

- `test_account_sync.py`: 11 bài kiểm thử PASS bằng API ASGI ở hai tiến trình, dữ liệu SQLite tạm; không dùng database hoặc khóa thật.
- Xác nhận tạo đơn lẻ/hàng loạt và tác vụ nền tự tạo tài khoản chatbot với email, mật khẩu và quyền tương ứng; đăng nhập trực tiếp thành công. Kiểm tra cả mật khẩu 6 ký tự do system sinh và mật khẩu trên 128 ký tự; đăng ký chatbot vẫn giữ giới hạn 8–128.
- Xác nhận chatbot mất kết nối không làm hỏng tài khoản system; yêu cầu còn sau khi đóng/mở lại database và tiến trình nhận. Mất phản hồi sau khi chatbot đã tạo tài khoản rồi thử lại không tạo trùng hoặc thay mật khẩu.
- Xác nhận giữ nguyên mật khẩu/quyền của tài khoản chatbot trùng email; rollback, tạo trùng và xóa tài khoản system chưa gửi không để lại yêu cầu sai.
- Xác nhận chế độ độc lập không tạo yêu cầu hoặc gọi chatbot, không chạy tác vụ đồng bộ; đăng ký/đăng nhập chatbot vẫn hoạt động khi API đồng bộ bị tắt. Thiếu khóa SSO không bật đồng bộ.
- Vé sai chữ ký, issuer, audience, loại, quyền, email, hash mật khẩu, jti hoặc hạn dùng bị từ chối. Vé đồng bộ không đổi được phiên SSO và không xác thực được `/users/me`.
- TypeScript frontend chatbot, kiểm tra dependencies Python và cấu hình Compose merge với override đều PASS; cú pháp PowerShell của `start.ps1` hợp lệ.
- Docker Desktop chưa chạy trong lần kiểm tra bổ sung này; chưa build/restart container hoặc kiểm tra mạng Docker trực tiếp. Cần bật Docker Desktop và chạy `start.ps1 -Build` để áp dụng.

## Đồng bộ tài khoản và SSO (bổ sung)

- Dựng lại và chạy toàn bộ Docker thành công; frontend/backend chatbot, PostgreSQL, Redis và Nginx healthy; domain public đang mở.
- Chatbot có 1 tài khoản: `admin@gmail.com`, quyền admin. Đã tạo trong system với username `admin_7932b2e1` để tránh trùng username `admin`. Giữ nguyên hash mật khẩu Argon2 và quyền; 5 tài khoản system cũ không đổi bất kỳ giá trị nào. SQLite integrity check: `ok`.
- Sao lưu trước khi nhập tại `/app/data/pre-chatbot-sync-20261005-085512-220420.db` trong volume backend system. Chạy đồng bộ lần hai: tạo 0, giữ nguyên 1 tài khoản trùng email.
- TypeScript hai frontend và Docker production build chatbot thành công. Navbar không có lỗi ESLint mới; ba cảnh báo unused đã có sẵn. File API system còn hai lỗi `any` có sẵn từ HEAD.
- Kiểm tra importer trên database riêng: giữ tài khoản/email/mật khẩu/quyền đã có; xử lý username trùng; mật khẩu nhập đăng nhập được qua hàm endpoint login; mật khẩu sai bị từ chối; chạy lại không tạo trùng; dữ liệu quyền không hợp lệ bị từ chối trước khi ghi.
- `verify-sso.ps1` PASS: SSO cho tài khoản đã nhập, endpoint cấp vé yêu cầu đăng nhập, kiểm tra chữ ký/issuer/audience/type/role/expiry, từ chối vé dùng lại, hai worker đổi cùng vé chỉ một yêu cầu thành công, vé SSO không dùng được như JWT chatbot, tương thích mật khẩu Argon2/PBKDF2/cũ.
- Kiểm tra quyền độc lập: tài khoản chatbot đã có quyền user không bị nâng lên admin từ vé system; không cấu hình khóa SSO thì hai backend từ chối SSO, JWT thông thường vẫn hoạt động.
- Trình duyệt trên domain public: bấm menu Chatbot tạo tab mới, tự đăng nhập `admin@gmail.com` và đến `/chatbot/admin`. Fragment đã xóa, `window.opener` là null; không có lỗi JavaScript.
- Hành vi cũ, trước bản sửa ngày 06/10/2026: khi system đang đăng nhập `an.nv@student.actvn.edu.vn` và chatbot là `admin@gmail.com`, bấm Chatbot giữ email, quyền và JWT chatbot hiện tại. Hành vi này đã được thay thế: SSO luôn chọn tài khoản system hiện tại.
- Trình duyệt: thay JWT chatbot bằng JWT thực sự đã hết hạn, bấm Chatbot từ system khôi phục phiên hợp lệ của `admin@gmail.com`.
- Ảnh giao diện sau SSO: `verification/screenshot-1791190656500.png` (thư mục verification được bỏ qua bởi Git).

- Các script PowerShell parse thành công; `status.ps1` chạy được.
- Ba cấu hình Compose hợp lệ. Khi merge override, system chỉ dùng cổng frontend host 3001, chatbot chỉ dùng 3000. Frontend có mạng riêng và mạng gateway; backend không tham gia mạng gateway.
- TypeScript chatbot: `npm run typecheck` thành công. Docker build frontend chatbot với base path `/chatbot` thành công.
- Nginx: `nginx -t` thành công; container healthy.
- Qua `localhost:8080`, system và các trang chatbot `/chatbot`, `/chatbot/login`, `/chatbot/chat`, `/chatbot/admin`, `/chatbot/register` trả HTML 200. Tài nguyên chatbot dùng `/chatbot/_next/`.
- API `/api/problems` của system và `/chatbot/api/health/ready` của chatbot hoạt động qua gateway. Readiness của chatbot xác nhận PostgreSQL và Redis sẵn sàng.
- Đăng nhập tài khoản system được seed sẵn và gọi API với Bearer token thành công. Chatbot nhận Bearer token và trả hồ sơ đúng qua `/chatbot/api/users/me`.
- SSE có xác thực qua Nginx: dùng một generation đã kết thúc trong database hiện có, nhận `text/event-stream` và dòng stream đầu tiên sau khoảng 17 giây (heartbeat backend mỗi 15 giây). Không tạo lượt gọi model AI mới trong kiểm tra này.
- Domain public `larcher-brecken-palynologically.ngrok-free.dev`: `/`, `/chatbot/login`, `/api/problems`, `/chatbot/api/health/ready` đều trả HTTP 200.
- Trình duyệt: system hiển thị giao diện; chatbot chuyển từ `/chatbot` sang `/chatbot/login`; truy cập `/chatbot/admin` khi chưa đăng nhập chuyển đúng về trang login. Ảnh nền chatbot tải qua tiền tố `/chatbot`. Không phát hiện lỗi JavaScript của trang trong các lần kiểm tra sau khi ứng dụng sẵn sàng.
- SQLite system: sao lưu database cũ trước khi thêm hai cột còn thiếu. Kiểm tra migration trên bản sao có schema cũ: hai lần startup thành công, integrity check `ok`, mọi giá trị của các cột và dòng có trước migration được giữ nguyên.

Các kiểm tra này xác nhận định tuyến, giao diện, xác thực API và truyền SSE qua gateway. Không thực hiện lượt tạo nội dung AI mới hoặc nộp bài để chấm điểm trong phiên kiểm tra.
