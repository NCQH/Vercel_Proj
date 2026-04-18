# Phân tích Tính năng: Trang Mock Login (Gateway Phân quyền)

## 1. Vai trò của giao diện trong hệ thống

Trang Xác thực (Mock Login) hiện tại đóng vai trò là **Cửa ngõ phân luồng (Routing Gateway)** cho nền tảng Trợ giảng AI. Thay vì tập trung vào bảo mật (auth) ở giai đoạn MVP, trang này giải quyết bài toán cốt lõi đầu tiên: **Phân định rõ ràng hai nhóm người dùng (Student và Lecturer)** để điều hướng họ vào đúng không gian làm việc với các tính năng chuyên biệt.

## 2. Phân tích các tính năng cốt lõi được thể hiện

### 2.1. Chức năng Phân quyền (Role-Based Access Control - RBAC)

Giao diện định nghĩa và bóc tách rõ ràng hai luồng quyền hạn. Bằng cách yêu cầu người dùng chọn vai trò ngay từ đầu, hệ thống thiết lập ngữ cảnh cho các tính năng họ sắp trải nghiệm:

- **Không gian Sinh viên (Student Workspace):** Hướng tới việc tiêu thụ kiến thức và hỗ trợ học tập cá nhân hóa.
- **Không gian Giảng viên (Lecturer Workspace):** Hướng tới việc quản trị dữ liệu đầu vào (cho RAG) và theo dõi chất lượng học tập của lớp.

### 2.2. Khái quát cụm tính năng của Sinh viên (Student Features)

Thông qua mô tả trên giao diện, hệ thống xác nhận 3 tính năng chính mà sinh viên sẽ sử dụng sau khi đăng nhập:

- **Hỏi đáp (Ask questions):** Tương tác với chatbot AI để giải đáp thắc mắc về môn học.
- **Kiểm chứng thông tin (Review citations):** Xem các trích dẫn nguồn (slide, trang, timestamp) được AI trích xuất từ tài liệu của giảng viên, đảm bảo tính chính xác và chống hallucination.
- **Lộ trình cá nhân hóa (Personalized study roadmap):** Nhận các gợi ý ôn tập dựa trên lịch sử hỏi đáp và lỗ hổng kiến thức (knowledge gaps) của chính mình.

### 2.3. Khái quát cụm tính năng của Giảng viên (Lecturer Features)

Tương tự, giao diện phác thảo 3 quyền năng quản trị dành cho giảng viên:

- **Quản lý học liệu (Manage materials):** Khả năng tải lên và index các tài liệu (PDF, slide, video) vào vector database để xây dựng knowledge base cho chatbot.
- **Theo dõi lỗ hổng kiến thức (Monitor class gaps):** Xem các báo cáo tổng hợp về những phần kiến thức mà sinh viên trong lớp đang hỏi nhiều nhất hoặc hiểu sai nhiều nhất.
- **Đánh giá thống kê (Review analytics):** Theo dõi các chỉ số về hiệu suất của hệ thống (số câu hỏi đã đáp, thời lượng tiết kiệm được, v.v.).

## 3. Luồng tương tác người dùng (User Flow)

Giao diện thiết kế một luồng thao tác 3 bước chặt chẽ để giảm thiểu rủi ro điều hướng nhầm:

1.  **Lựa chọn (Selection):** Người dùng click chọn một trong hai thẻ vai trò. Hệ thống lưu trạng thái (state) này ở bộ nhớ tạm.
2.  **Xác nhận (Confirmation):** Phần dưới cùng của màn hình hiển thị rành mạch dòng chữ "Selected role: Student/Lecturer", hoạt động như một bước checkpoint để người dùng tự kiểm tra lại trước khi đi tiếp.
3.  **Điều hướng (Navigation):** Nút "Continue" sẽ thực thi lệnh chuyển trang (push router) dựa trên trạng thái đã chọn (`/student/chat` hoặc `/lecturer/dashboard`), hoàn tất quá trình đăng nhập mô phỏng.
