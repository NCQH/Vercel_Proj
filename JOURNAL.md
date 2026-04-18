# Weekly Journal

Ghi lại hành trình xây dựng sản phẩm mỗi tuần — những gì đã làm, học được gì, AI giúp như thế nào.

> **Cập nhật mỗi cuối tuần**

Hiện tại
- AI agent core (Python thuần, chưa theo Framework)
    - RAG
    - ChromaDB
    - 1 agent retriever, gọi tool và trả về câu trả lời
- UI (ReactJS)

Dự kiến
- Code theo Langgraph
- Sử dụng multiagent
    - 1 agent gọi tool (dùng local llm để giảm chi phí)
    - 1 agent retriever
    - 1 agent trả về thông tin cho người dùng (suy luận)
    - 1 agent nhận file của sinh viên và xử lý lưu vào db