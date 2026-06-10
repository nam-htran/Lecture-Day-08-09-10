# Runbook - Lab Day 10

## Symptom

- Agent tra loi refund window la 14 ngay thay vi 7 ngay.
- Cau HR 2026 tra ve 10 ngay phep nam thay vi 12 ngay.
- Cau Level 4 Admin Access khong tim thay IT Manager/CISO.
- Freshness monitor bao FAIL tren manifest.

## Detection

- `python etl_pipeline.py run` fail/halt neu expectation severity `halt` fail.
- `artifacts/logs/run_<run_id>.log` co `raw_records`, `cleaned_records`, `quarantine_records`, expectation result.
- `python eval_retrieval.py --out artifacts/eval/eval_after_fix.csv` de xem `contains_expected`, `hits_forbidden`, `top1_doc_expected`.
- `python grading_run.py --out artifacts/eval/grading_run.jsonl` de kiem tra 10 cau grading.

## Diagnosis

| Buoc | Viec lam | Ket qua mong doi |
|------|----------|------------------|
| 1 | Mo manifest moi nhat trong `artifacts/manifests/` | thay `run_id`, count, `latest_exported_at` |
| 2 | Mo quarantine CSV | thay reason nhu `unknown_doc_id`, `stale_hr_2025_content` |
| 3 | Kiem tra cleaned CSV theo `doc_id` | du 5 source canonical, 33 chunks |
| 4 | Chay eval before/after | inject co `hits_forbidden=yes` cho refund, after fix la `no` |
| 5 | Chay grading quick check | `gq_d10_01` den `gq_d10_10` OK |

## Mitigation

1. Dung publish neu expectation halt fail.
2. Neu da inject/bad publish, chay lai:

```bash
.\.venv\Scripts\python.exe etl_pipeline.py run --run-id day10-idempotent-rerun
.\.venv\Scripts\python.exe grading_run.py --out artifacts/eval/grading_run.jsonl
```

3. Chroma publish la snapshot: run sach se prune vector id khong con trong cleaned.
4. Neu freshness FAIL trong production, tam thoi canh bao "data stale" va rollback sang manifest sach gan nhat.

## Prevention

- Giu `canonical_doc_coverage` de khong mat `access_control_sop`.
- Giu `refund_no_stale_14d_window` va `hr_leave_no_2025_marker` de chan stale policy.
- Giu `exported_at_iso_datetime` de freshness khong WARN do timestamp khong parse duoc.
- Review quarantine reason moi ngay sau batch; neu `unknown_doc_id` tang bat thuong thi cap nhat contract/source catalog.
- Do freshness o publish boundary, khong chi o ingest start.
