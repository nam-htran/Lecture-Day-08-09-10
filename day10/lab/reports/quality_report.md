# Quality report - Lab Day 10

**run_id clean:** `day10-idempotent-rerun`  
**run_id inject:** `day10-inject-bad`  
**Ngay:** 2026-06-10

## 1. Tom tat so lieu

| Chi so | Truoc / inject | Sau clean | Ghi chu |
|--------|----------------|-----------|---------|
| raw_records | 247 | 247 | cung raw CSV |
| cleaned_records | 33 | 33 | inject bo refund fix nhung van giu same row count |
| quarantine_records | 214 | 214 | quarantine reason duoc ghi rieng |
| Expectation halt? | refund halt fail 1 violation, skip validate co chu dich | no halt | final `PIPELINE_OK` |
| embed count | 33 | 33 | final rerun idempotent |

## 2. Before / after retrieval

Artifact:

- Before/inject: `artifacts/eval/eval_inject_bad.csv`
- After/fix: `artifacts/eval/eval_after_fix.csv`

Key row: `q_refund_window`

| Run | top1_doc_id | contains_expected | hits_forbidden | top1_doc_expected |
|-----|-------------|-------------------|----------------|-------------------|
| inject bad | `policy_refund_v4` | yes | yes | yes |
| after fix | `policy_refund_v4` | yes | no | yes |

Merit rows:

| Question | After result |
|----------|--------------|
| `q_hr_annual_leave_under3` | top1 `hr_leave_policy`, contains expected 12 ngay, no forbidden 10 ngay |
| `q_access_level4` | top1 `access_control_sop`, contains IT Manager/CISO |
| `q_p1_escalation` | top1 `sla_p1_2026`, contains 10 phut after retrieval alias |

## 3. Freshness & monitor

`freshness_check=FAIL` for run `day10-idempotent-rerun` because `latest_exported_at=2026-04-11T00:00:00` is older than SLA 24h on 2026-06-10. This is expected for the lab sample. The important behavior is that the manifest records the data timestamp and the monitor reports a concrete reason: `freshness_sla_exceeded`.

## 4. Corruption inject

Inject command:

```bash
.\.venv\Scripts\python.exe etl_pipeline.py run --run-id day10-inject-bad --no-refund-fix --skip-validate
```

This intentionally disables the refund 14->7 day repair. The expectation suite detects the issue:

```text
expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1
```

`--skip-validate` is used only to publish the bad index and create before/after evidence. A normal run would halt.

## 5. Han che & viec chua lam

- Freshness monitor is manifest-based only.
- Retrieval alias is a targeted lab fix; production should prefer better chunking/query expansion with review.
- No external orchestrator is included; rerun is manual CLI.
