# Báo cáo chất lượng - Lab Day 10

**Run sạch:** `day10-grade-final`  
**Run inject:** `day10-inject-bad`  
**Ngày:** 2026-06-10

## 1. Tóm tắt số liệu

| Chỉ số | Trước / inject | Sau clean | Ghi chú |
|--------|----------------|-----------|---------|
| `raw_records` | 247 | 247 | Cùng file raw `data/raw/policy_export_dirty.csv` |
| `cleaned_records` | 33 | 33 | Run inject bỏ refund fix nhưng vẫn giữ cùng số row sạch |
| `quarantine_records` | 214 | 214 | Quarantine ghi rõ `reason` cho từng record bị loại |
| Expectation halt? | `refund_no_stale_14d_window` fail 1 violation | Không halt, `PIPELINE_OK` | Inject dùng `--skip-validate` để tạo evidence |
| Embed count | 33 | 33 | Rerun dùng upsert theo `chunk_id`, không phình index |

## 2. Bằng chứng bắt buộc

| Yêu cầu | Artifact |
|---------|----------|
| Log số record | `artifacts/logs/run_day10-grade-final.log` có `run_id`, `raw_records=247`, `cleaned_records=33`, `quarantine_records=214` |
| Quarantine | `artifacts/quarantine/quarantine_day10-grade-final.csv` |
| Expectation halt có kiểm soát | `artifacts/logs/run_day10-inject-bad.log` có `refund_no_stale_14d_window FAIL (halt) :: violations=1` |
| `run_id` trên manifest | `artifacts/manifests/manifest_day10-grade-final.json` |
| Before/after retrieval | `artifacts/eval/eval_inject_bad.csv` và `artifacts/eval/eval_after_fix.csv` |

## 3. Before / after retrieval

Hàng quan trọng nhất là `q_refund_window`:

| Run | `top1_doc_id` | `contains_expected` | `hits_forbidden` | `top1_doc_expected` |
|-----|---------------|---------------------|------------------|---------------------|
| Inject bad | `policy_refund_v4` | yes | yes | yes |
| After fix | `policy_refund_v4` | yes | no | yes |

Ý nghĩa: trước khi fix, retrieval vẫn kéo được thông tin đúng "7 ngày" nhưng trong top-k còn chunk stale "14 ngày", nên `hits_forbidden=yes`. Sau khi clean và publish lại, cùng câu hỏi không còn forbidden context.

Các hàng kiểm tra thêm:

| Câu hỏi | Kết quả sau fix |
|---------|-----------------|
| `q_hr_annual_leave_under3` | Top-1 là `hr_leave_policy`, có nội dung 12 ngày phép năm, không còn 10 ngày phép năm |
| `q_access_level4` | Top-1 là `access_control_sop`, có IT Manager / CISO |
| `q_p1_escalation` | Top-1 là `sla_p1_2026`, có thông tin auto escalate sau 10 phút |

## 4. Freshness & monitor

`freshness_check=FAIL` trong run `day10-grade-final` vì `latest_exported_at=2026-04-11T00:00:00` cũ hơn SLA 24 giờ tại thời điểm chạy ngày 2026-06-10. Với dữ liệu mẫu của lab, kết quả FAIL này là hợp lý. Điểm quan trọng là manifest ghi timestamp dữ liệu và monitor trả lý do cụ thể: `freshness_sla_exceeded`.

## 5. Corruption inject

Lệnh inject:

```powershell
.\.venv\Scripts\python.exe etl_pipeline.py run --run-id day10-inject-bad --no-refund-fix --skip-validate
```

Run này cố ý tắt rule sửa refund 14 ngày thành 7 ngày. Expectation suite phát hiện lỗi:

```text
expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1
```

`--skip-validate` chỉ dùng để publish index xấu phục vụ so sánh before/after. Với pipeline chuẩn, lỗi này sẽ làm job dừng có kiểm soát.

## 6. Hạn chế & việc chưa làm

- Freshness monitor hiện đọc từ manifest, chưa đọc watermark trực tiếp từ source system.
- Retrieval alias cho SLA P1 là fix có chủ đích trong phạm vi lab; production nên có query expansion/chunking strategy được review.
- Pipeline hiện chạy bằng CLI, chưa có orchestrator như Airflow hoặc Dagster.
