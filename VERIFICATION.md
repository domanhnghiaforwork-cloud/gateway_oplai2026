# Kết quả kiểm tra ngày 05/10/2026

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
