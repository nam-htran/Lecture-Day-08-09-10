# Bao cao ca nhan - Nam

## Phan phu trach

Toi phu trach phan Cleaning / Quality / Embed verification cho Lab Day 10. Cac file chinh da sua la `transform/cleaning_rules.py`, `quality/expectations.py`, `etl_pipeline.py`, `contracts/data_contract.yaml`, va cac report trong `docs/`, `reports/`. Muc tieu la bien raw export 247 records thanh mot snapshot cleaned co the publish vao Chroma, co quarantine ro rang, co expectation halt, va co grading evidence.

## Quyet dinh ky thuat

Quyet dinh quan trong nhat la khong chi sua allowlist bang cach them `access_control_sop`, ma them expectation `canonical_doc_coverage` va `access_control_level4_present`. Ly do: baseline co the "chay duoc" nhung van thieu source hop le, dan den grading `gq_d10_10` khong bao gio dung. Toi cung them `unique_nonempty_chunk_id` de bao ve idempotency, va `exported_at_iso_datetime` de freshness monitor khong bi unparseable timestamp.

Voi SLA P1 escalation, query grading dung "auto escalate" trong khi raw chunk dung "tu dong escalate". Toi them retrieval alias hep cho dung chunk P1, va enrich chunk summary P1 bang cau "auto escalate sau 10 phut". Day la quyet dinh transform co chu dich: giu thong tin nghiep vu dung, nhung giup retriever lay dung context trong top-k.

## Anomaly va cach fix

Anomaly lon nhat la baseline `baseline-before` halt vi HR stale: `hr_leave_no_stale_10d_annual` fail 2 violations. Raw co nhieu dong HR 2025 "10 ngay phep nam", trong do mot so dong co effective_date 2026 nen rule chi dua vao ngay khong du. Toi them rule `stale_hr_2025_content` de quarantine theo noi dung va marker "ban HR 2025". Run cuoi `day10-idempotent-rerun` co `stale_hr_2025_content=7`, `stale_hr_policy_effective_date=22`, va expectation HR deu OK.

Anomaly thu hai la `access_control_sop` bi xem nhu unknown source du baseline allowlist thieu. Sau khi them vao allowlist va contract, cleaned output co 6 chunks access control; grading `gq_d10_10` top1 la `access_control_sop` va contains IT Manager/CISO.

## Before / after

Inject run `day10-inject-bad` dung `--no-refund-fix --skip-validate`. Log ghi `refund_no_stale_14d_window FAIL (halt) :: violations=1`, va eval `q_refund_window` co `hits_forbidden=yes`. Sau run clean `day10-idempotent-rerun`, `eval_after_fix.csv` cho `q_refund_window` la `contains_expected=yes`, `hits_forbidden=no`, `top1_doc_expected=yes`. Official `grading_run.jsonl` dat 10/10 cau.

## Cai tien trong 2 gio tiep theo

Neu co them 2 gio, toi se tach retrieval alias thanh file config/versioned rule trong contract thay vi hard-code trong transform, va them mot pytest nho cho cac rule quan trong: HR stale, access allowlist, refund inject, P1 escalation alias.
