class PredefinedQuestionConsts:
    first_prompt = """# MỤC TIÊU
Phân tích xem quy định pháp lý này có liên quan đến câu hỏi của bệnh nhân không.

# CÂU HỎI CỦA BỆNH NHÂN
{question}

# QUY ĐỊNH CẦN ĐÁNH GIÁ
## TIÊU ĐỀ
{regulationTitle}
## NỘI DUNG
{regulationContent}

# TIÊU CHÍ ĐÁNH GIÁ
- Quy định có trả lời trực tiếp câu hỏi của bệnh nhân không?
- Quy định có chứa thông tin về thủ tục, quy trình mà bệnh nhân cần biết không?
- Quy định có liên quan đến tình huống y tế của bệnh nhân không?
- Độ chính xác và hữu ích của thông tin cho bệnh nhân

# ĐỊNH DẠNG TRẢ LỜI
Trả về JSON format:
{{
    "isRelevant": true/false,
    "confidenceScore": 0.0-1.0
}}
"""
    comparison_prompt = """# MỤC TIÊU
So sánh hai quy định để xác định quy định nào phù hợp hơn với câu hỏi của bệnh nhân.

# CÂU HỎI CỦA BỆNH NHÂN
{question}

# QUY ĐỊNH ĐANG XÉT LÀM TỐT NHẤT
## TIÊU ĐỀ
{bestMatchRegulationTitle}
## NỘI DUNG
{bestMatchRegulationContent}

# QUY ĐỊNH MỚI CẦN SO SÁNH
## TIÊU ĐỀ
{regulationTitle}
## NỘI DUNG
{regulationContent}

# TIÊU CHÍ SO SÁNH
- Quy định nào trả lời trực tiếp và chính xác hơn cho câu hỏi?
- Quy định nào cung cấp thông tin hữu ích hơn cho bệnh nhân?
- Quy định nào có hướng dẫn thủ tục cụ thể hơn?
- Quy định nào phù hợp hơn với ngữ cảnh y tế của bệnh nhân?
- Độ chi tiết và tính thực tiễn của từng quy định

# ĐỊNH DẠNG TRẢ LỜI
Trả về JSON format:
{{
    "newIsBetter": true/false,
    "confidenceScore": 0.0-1.0
}}
"""

    answer_generation_prompt = """# MỤC TIÊU
Tạo câu trả lời chính thức mang tính văn bản hành chính cho câu hỏi dựa trên quy định pháp lý.

# CÂU HỎI
{question}

# QUY ĐỊNH PHÁP LÝ LIÊN QUAN
## TIÊU ĐỀ
{regulationTitle}
## NỘI DUNG
{regulationContent}

# YÊU CẦU VỀ VĂN PHONG
- Văn phong hành chính, trang trọng, chính thức như văn bản pháp lý
- Sử dụng thuật ngữ chuyên môn chính xác theo quy định
- Trích dẫn đầy đủ và chính xác điều, khoản, mục trong quy định
- Cấu trúc câu trả lời logic, có thứ tự rõ ràng
- Thông tin đầy đủ, không thiếu sót các khía cạnh quan trọng

# CẤU TRÚC CÂU TRẢ LỜI
1. **Căn cứ pháp lý**: Trích dẫn điều, khoản cụ thể
2. **Nội dung trả lời**: Giải thích chi tiết theo quy định
3. **Thủ tục thực hiện**: Các bước cần thực hiện (nếu có)
4. **Lưu ý quan trọng**: Điều kiện, thời hạn, yêu cầu đặc biệt

# ĐỊNH DẠNG TRẢ LỜI
Trả về JSON với câu trả lời định dạng markdown:
{{
    "answer": "## Căn cứ pháp lý\\n\\nTheo quy định tại [điều khoản cụ thể]...\\n\\n## Nội dung trả lời\\n\\n[Giải thích chi tiết]...\\n\\n## Thủ tục thực hiện\\n\\n1. [Bước 1]\\n2. [Bước 2]\\n\\n## Lưu ý quan trọng\\n\\n- [Lưu ý 1]\\n- [Lưu ý 2]",
    "regulationReferences": ["Điều X, Khoản Y của [Tên đầy đủ văn bản pháp lý]"]
}}
"""

    generate_questions_prompt = """# MỤC TIÊU
Phân tích quy định y tế và tạo ra tối đa {maxQuestions} câu hỏi thường gặp quan trọng nhất mà bệnh nhân có thể hỏi.

# QUY ĐỊNH Y TẾ
## TIÊU ĐỀ
{regulationTitle}
## NỘI DUNG
{regulationContent}

# TIÊU CHÍ LỰA CHỌN CÂU HỎI
- CHỈ tạo những câu hỏi QUAN TRỌNG và PHỔ BIẾN nhất
- Câu hỏi mà 80% bệnh nhân sẽ thắc mắc khi gặp tình huống này
- Tập trung vào thông tin THIẾT YẾU cho bệnh nhân và gia đình
- Loại bỏ câu hỏi không thực tế, quá chuyên môn hoặc ít quan trọng

# NHÓM CÂU HỎI ƯU TIÊN
1. **Thủ tục bắt buộc**: Các bước cần làm, quy trình chính
2. **Giấy tờ cần thiết**: Documents chuẩn bị, điều kiện đủ
3. **Thời gian và chi phí**: Timeline, mức phí, thời hạn
4. **Điều kiện áp dụng**: Ai được hưởng, trường hợp nào
5. **Xử lý sự cố**: Khi thiếu giấy tờ, từ chối, phúc khảo
6. **Quyền lợi bệnh nhân**: Được hưởng gì, hỗ trợ gì

# PHONG CÁCH CÂU HỎI
- Văn phong hành chính, chuyên nghiệp phù hợp cho hệ thống y tế
- Thuật ngữ chính xác theo quy định pháp lý
- Câu hỏi rõ ràng, có tính tham khảo cao cho predefined system

# VÍ DỤ CÂU HỎI CHẤT LƯỢNG CAO
- "Thủ tục khám chữa bệnh BHYT gồm những bước nào?"
- "Hồ sơ bệnh án cần có những giấy tờ gì theo quy định?"
- "Trường hợp nào được miễn giảm viện phí theo quy định?"
- "Quy trình giải quyết khiếu nại về chi phí y tế như thế nào?"

# ĐỊNH DẠNG TRẢ LỜI
Tối đa {maxQuestions} câu hỏi, chỉ những câu QUAN TRỌNG NHẤT:
{{
    "questions": [
        "Câu hỏi quan trọng 1",
        "Câu hỏi quan trọng 2",
        "...",
        "Tối đa {maxQuestions} câu hỏi"
    ]
}}
"""
