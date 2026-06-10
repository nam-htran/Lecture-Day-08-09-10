# Bao cao nop bai ca nhan - Lab Day 10: Data Pipeline & Data Observability

> File van giu ten `reports/group_report.md` theo skeleton lab, nhung noi dung duoc viet cho bai nop ca nhan.

**Nguoi nop:** Nam  
**Vai tro:** Ingestion, Cleaning, Quality, Embed, Monitoring, Docs  
**Email:** _dien email_

**Ngay nop:** 2026-06-10  
**Run clean cuoi:** `day10-idempotent-rerun`  
**Run inject:** `day10-inject-bad`

## 1. Pipeline tong quan

Lab xu ly export raw `data/raw/policy_export_dirty.csv` gom 247 records tu nhieu source. Pipeline chay bang mot lenh:

```bash
.\.venv\Scripts\python.exe etl_pipeline.py run --run-id day10-idempotent-rerun
```

Luong chinh la ingest CSV, clean/quarantine, validate expectation, embed vao Chroma collection `day10_kb`, viet manifest, roi chay freshness check. Run cuoi tao `artifacts/cleaned/cleaned_day10-idempotent-rerun.csv`, `artifacts/quarantine/quarantine_day10-idempotent-rerun.csv`, va `artifacts/manifests/manifest_day10-idempotent-rerun.json`. Ket qua: `raw_records=247`, `cleaned_records=33`, `quarantine_records=214`, `embed_upsert count=33`, `PIPELINE_OK`. Rerun sau khi index da sach khong con `embed_prune_removed`, cho thay upsert theo `chunk_id` khong tao duplicate vector.

## 2. Cleaning & expectation

Baseline bi halt: `baseline-before` clean 40 rows, quarantine 207 rows, nhung `hr_leave_no_stale_10d_annual` fail 2 violations. Toi sua `transform/cleaning_rules.py` de them source hop le `access_control_sop`, normalize `exported_at`, quarantine ambiguous placeholder, repeated sentence spam, stale HR 2025 content, va them retrieval alias hep cho SLA P1 escalation. `quality/expectations.py` duoc bo sung coverage/semantic checks: unique chunk id, du 5 canonical docs, khong con HR 2025 marker, exported_at ISO datetime, Access Level 4 present, va P1 auto-escalate 10 phut present.

### 2a. Bang metric_impact

| Rule / Expectation moi | Truoc | Sau / khi inject | Chung cu |
|------------------------|-------|------------------|----------|
| `access_control_sop` allowlist + `canonical_doc_coverage` | baseline allowlist thieu source, grading `gq_d10_10` khong co context | final cleaned co 6 chunks `access_control_sop`, `gq_d10_10` OK | `cleaned_day10-idempotent-rerun.csv`, `grading_run.jsonl` |
| `stale_hr_2025_content` + `hr_leave_no_2025_marker` | `baseline-before` halt: HR stale violations=2 | final: HR stale violations=0; quarantine `stale_hr_2025_content=7` | `run_baseline-before.log`, `quarantine_day10-idempotent-rerun.csv` |
| `normalize_exported_at` + `exported_at_iso_datetime` | raw co timestamp dang `2026/04/...` co the lam freshness WARN | final: `non_iso_exported_at_rows=0` | `run_day10-idempotent-rerun.log` |
| `ambiguous_placeholder_text` | vague text co the vao index | final quarantine 7 rows | `quarantine_day10-idempotent-rerun.csv` |
| `repeated_sentence_spam` | spam duplicate sentence co the thanh unique noisy chunk | final quarantine 2 rows | `quarantine_day10-idempotent-rerun.csv` |
| `sla_p1_auto_escalate_10min_present` | `q_p1_escalation` tung khong bat duoc `10 phut` trong top-k | final grading `gq_d10_06` OK | `grading_run.jsonl` |

Vi du expectation fail co kiem soat: `day10-inject-bad` chay voi `--no-refund-fix --skip-validate`; `refund_no_stale_14d_window` FAIL 1 violation, nhung pipeline tiep tuc embed de tao evidence before/after.

## 3. Before / after retrieval

Inject scenario:

```bash
.\.venv\Scripts\python.exe etl_pipeline.py run --run-id day10-inject-bad --no-refund-fix --skip-validate
.\.venv\Scripts\python.exe eval_retrieval.py --out artifacts/eval/eval_inject_bad.csv
```

Evidence chinh la `q_refund_window`: trong `eval_inject_bad.csv`, `contains_expected=yes` nhung `hits_forbidden=yes`, nghia la top-k van co stale "14 ngay". Sau khi chay clean pipeline va regenerate `eval_after_fix.csv`, cung cau hoi co `contains_expected=yes`, `hits_forbidden=no`, `top1_doc_expected=yes`. HR va access cung dat: `q_hr_annual_leave_under3` top1 `hr_leave_policy`, khong forbidden; `q_access_level4` top1 `access_control_sop`.

Grading official `artifacts/eval/grading_run.jsonl` dat 10/10: `gq_d10_01` den `gq_d10_10` deu `contains_expected=true`, `hits_forbidden=false`; cac cau co `expect_top1_doc_id` deu `top1_doc_matches=true`.

## 4. Freshness & monitoring

SLA freshness la 24 gio tai publish boundary. Manifest run cuoi co `latest_exported_at=2026-04-11T00:00:00`; voi ngay chay 2026-06-10, `freshness_check=FAIL` va `reason=freshness_sla_exceeded`. Day la ket qua hop ly cho sample snapshot cu. Trong production, FAIL nay se kich hoat canh bao data stale; trong lab, no duoc ghi vao runbook de chung minh pipeline do duoc freshness thay vi chi embed thanh cong.

## 5. Lien he Day 09

Collection `day10_kb` la corpus sach cho retriever/agent cua Day 09. Day 09 khong can sua prompt neu source data da duoc publish dung version: refund 7 ngay, SLA P1 15 phut/4 gio/10 phut escalation, HR 12 ngay, va access Level 4 IT Manager + CISO.

## 6. Rui ro con lai & viec chua lam

- Chua co orchestration that nhu Airflow/Dagster; hien la CLI reproducible.
- Freshness chi dua vao manifest, chua doc watermark truc tiep tu source system.
- Chua dien email that cua nguoi nop.
- Chroma DB local bi ignore trong git; khi cham can rerun pipeline hoac nop artifact theo yeu cau GV.
