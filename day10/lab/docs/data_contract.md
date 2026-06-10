# Data contract - Lab Day 10

Nguon chinh la `contracts/data_contract.yaml`. File nay tom tat de review nhanh khi cham.

## 1. Source map

| Nguon | Ingest | Failure mode chinh | Metric / alert |
|-------|--------|--------------------|----------------|
| `policy_refund_v4` | CSV export | stale refund window 14 ngay, vague text, duplicate | `refund_no_stale_14d_window`, `hits_forbidden` |
| `sla_p1_2026` | CSV export | P1/P2 context can rank nham, missing escalation evidence | `sla_p1_auto_escalate_10min_present`, eval `q_p1_escalation` |
| `it_helpdesk_faq` | CSV export | duplicate FAQ, irrelevant unknown docs | `canonical_doc_coverage`, top1 doc expected |
| `hr_leave_policy` | CSV export | HR 2025 stale content: 10 ngay phep nam | `hr_leave_no_2025_marker`, `gq_d10_09` |
| `access_control_sop` | CSV export | baseline allowlist thieu source hop le | `access_control_level4_present`, `gq_d10_10` |

## 2. Schema cleaned

| Cot | Kieu | Bat buoc | Ghi chu |
|-----|------|----------|---------|
| `chunk_id` | string | Co | Stable key cho upsert/prune |
| `doc_id` | string | Co | Phai thuoc 5 canonical doc ids |
| `chunk_text` | string | Co | Da repair/refund fix/alias can thiet |
| `effective_date` | date | Co | ISO `YYYY-MM-DD` |
| `exported_at` | datetime | Co | ISO `YYYY-MM-DDTHH:MM:SS` |

## 3. Quarantine vs drop

Khong drop am tham. Moi row bi loai duoc ghi vao `artifacts/quarantine/quarantine_<run_id>.csv` voi `reason`. Run cuoi `day10-idempotent-rerun` co 214 quarantine rows:

| Reason | Count |
|--------|------:|
| `unknown_doc_id` | 109 |
| `duplicate_chunk_text` | 53 |
| `stale_hr_policy_effective_date` | 22 |
| `missing_chunk_text` | 8 |
| `ambiguous_placeholder_text` | 7 |
| `stale_hr_2025_content` | 7 |
| `missing_effective_date` | 6 |
| `repeated_sentence_spam` | 2 |

## 4. Version & canonical

- Refund canonical: `data/docs/policy_refund_v4.txt`, window dung la 7 ngay lam viec.
- HR canonical: `data/docs/hr_leave_policy.txt`, effective 2026, nhan vien duoi 3 nam co 12 ngay phep nam.
- Access canonical: `data/docs/access_control_sop.txt`, Level 4 Admin Access can IT Manager + CISO.
- Freshness SLA do o publish boundary. Sample data cu hon SLA 24h nen monitor FAIL va can duoc giai thich trong runbook.
