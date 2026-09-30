# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert mẫu để tham khảo

Ví dụ dưới đây minh họa mức độ cụ thể cần có. Học viên không cần copy nguyên, nhưng ba alert trong bài nộp nên rõ ràng tương tự: điều kiện là gì, kéo dài bao lâu, ảnh hưởng tới user ra sao và người trực cần kiểm tra gì trước.

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn trước khi nhận câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính để xác định bước nào bất thường.
- Mitigation tạm thời: dựa trên evidence thực tế để rollback prompt, khôi phục cấu hình liên quan, tắt practice scenario hoặc giảm tải khi demo.
- Owner: `student-<MSSV>`

## Alert 1

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: SLO `fast_successful_requests` (latency <= 3000ms); dashboard panel latency.
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trên `response_sent` liên tục 5 phút.
- Ảnh hưởng tới người dùng: Người dùng chờ lâu hơn để nhận câu trả lời.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel Latency (P50/P95/P99, TTFT) để xác nhận khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` theo `event == response_sent` và `latency_ms > 3000`, lấy một `correlation_id`.
  3. Mở trace cùng `correlation_id` trên Langfuse; span `retrieval` chậm (~2.5s) nghĩa là `rag_slow`, span `generation` chậm nghĩa là LLM/prompt.
- Mitigation tạm thời: Tắt incident `rag_slow` (`POST /incidents/rag_slow/disable`) hoặc rollback label `production` của prompt `day13-chat` về version cũ; giảm tải khi demo.
- Owner: `student-2A202602367`

## Alert 2

- Tên: `HighErrorRateOrRetrievalFailure`
- Severity: `critical`
- Duration: `3m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: SLO `fast_successful_requests` (good = response_sent); guardrail error rate <= 2%, retrieval success >= 90%.
- Điều kiện và thời gian duy trì: `count(request_failed)/count(request_received)*100 > 2` hoặc retrieval success (`tool_success`) < 90% trong 3 phút.
- Ảnh hưởng tới người dùng: Người dùng nhận HTTP 500 hoặc câu trả lời không có context.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel Errors: xem error rate, `error_breakdown` và retrieval success rate.
  2. Lọc log `event == request_failed`, đọc `error_type`, `tool_name`, `tool_success` và lấy `correlation_id`.
  3. Mở trace cùng `correlation_id`; span `retrieval` báo lỗi (ví dụ `Vector store timeout`) xác nhận lỗi ở bước retrieval.
- Mitigation tạm thời: Tắt incident `tool_fail`, khởi động lại/khôi phục vector store, bật câu trả lời fallback khi retrieval lỗi.
- Owner: `student-2A202602367`

## Alert 3

- Tên: `CostOrQualityRegression`
- Severity: `warning`
- Duration: `10m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Guardrails: `daily_cost_usd_max = 2.5`, `quality_score_avg_min = 0.75`; panel Cost, Tokens, Quality.
- Điều kiện và thời gian duy trì: `sum(cost_usd)` trong ngày > 2.5 USD hoặc `mean(quality_score)` < 0.75 trong 10 phút.
- Ảnh hưởng tới người dùng: Chi phí tăng bất thường hoặc chất lượng câu trả lời giảm.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel Cost, Tokens và Quality để xác định metric nào xấu và từ lúc nào.
  2. Lọc log `response_sent` có `tokens_out`/`cost_usd` cao hoặc `quality_score` thấp, lấy `correlation_id`.
  3. Mở trace; xem span `generation` (input/output tokens, cost) và `prompt_version` trong metadata để biết có phải prompt mới gây regression.
- Mitigation tạm thời: Rollback label `production` của `day13-chat` từ v2 về v1; tắt incident `cost_spike`; giới hạn `max_tokens`.
- Owner: `student-2A202602367`

