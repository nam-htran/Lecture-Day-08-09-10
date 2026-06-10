"""
Cleaning rules — raw export → cleaned rows + quarantine.

Baseline gồm các failure mode mở rộng (allowlist doc_id, parse ngày, HR stale version).
Sinh viên thêm ≥3 rule mới: mỗi rule phải ghi `metric_impact` (xem README — chống trivial).
"""

from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Khớp export hợp lệ trong lab (mở rộng khi nhóm thêm doc mới — phải đồng bộ contract).
ALLOWED_DOC_IDS = frozenset(
    {
        "policy_refund_v4",
        "sla_p1_2026",
        "it_helpdesk_faq",
        "hr_leave_policy",
        "access_control_sop",
    }
)

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DMY_SLASH = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
_ISO_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")
_SLASH_DATETIME = re.compile(r"^(\d{4})/(\d{2})/(\d{2})(T\d{2}:\d{2}:\d{2})$")
_NOISY_PREFIX = re.compile(r"^[!\s]+")
_REPEATED_LAM_VIEC = re.compile(r"\blàm việc(?:\s+làm việc)+\b", flags=re.IGNORECASE)


def _norm_text(s: str) -> str:
    return " ".join((s or "").strip().split()).lower()


def _stable_chunk_id(doc_id: str, chunk_text: str, seq: int) -> str:
    h = hashlib.sha256(f"{doc_id}|{chunk_text}|{seq}".encode("utf-8")).hexdigest()[:16]
    return f"{doc_id}_{seq}_{h}"


def _normalize_effective_date(raw: str) -> Tuple[str, str]:
    """
    Trả về (iso_date, error_reason).
    iso_date rỗng nếu không parse được.
    """
    s = (raw or "").strip()
    if not s:
        return "", "empty_effective_date"
    if _ISO_DATE.match(s):
        return s, ""
    m = _DMY_SLASH.match(s)
    if m:
        dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
        return f"{yyyy}-{mm}-{dd}", ""
    return "", "invalid_effective_date_format"


def _normalize_exported_at(raw: str) -> Tuple[str, str]:
    """
    Return (iso_datetime, error_reason).
    Some source systems export the date part with slashes; normalize that instead of
    letting freshness checks see an unparseable publish timestamp.
    """
    s = (raw or "").strip()
    if not s:
        return "", "missing_exported_at"
    if _ISO_DATETIME.match(s):
        return s, ""
    m = _SLASH_DATETIME.match(s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}{m.group(4)}", ""
    return "", "invalid_exported_at_format"


def _is_ambiguous_placeholder(text: str) -> bool:
    stripped = text.strip().lower()
    return stripped == "nội dung không rõ ràng:" or stripped.startswith("nội dung không rõ ràng:")


def _has_repeated_sentence_spam(text: str) -> bool:
    sentences = [p.strip().lower() for p in re.split(r"[.!?]+", text) if p.strip()]
    if not sentences:
        return False
    counts: Dict[str, int] = {}
    for sentence in sentences:
        counts[sentence] = counts.get(sentence, 0) + 1
        if counts[sentence] >= 3:
            return True
    return False


def _is_stale_hr_annual_policy(text: str) -> bool:
    low = text.lower()
    if "bản hr 2025" in low:
        return True
    return bool(re.search(r"\b10\s+ngày(?:\s+làm\s+việc)?\s+phép\s+năm\b", low))


def _repair_chunk_text(text: str) -> str:
    fixed = _NOISY_PREFIX.sub("", text or "").strip()
    fixed = _REPEATED_LAM_VIEC.sub("làm việc", fixed)
    return " ".join(fixed.split())


def _add_retrieval_aliases(doc_id: str, text: str) -> str:
    low = text.lower()
    if (
        doc_id == "sla_p1_2026"
        and "ticket p1 có sla phản hồi" in low
        and "resolution trong 4 giờ" in low
        and "auto escalate" not in low
    ):
        return f"{text} Escalation P1: hệ thống auto escalate sau 10 phút nếu không có phản hồi."
    if (
        doc_id == "sla_p1_2026"
        and "escalation p1" in low
        and "10 phút" in low
        and "auto escalate" not in low
    ):
        return f"{text} [alias: auto escalate P1 no response 10 phút]"
    return text


def load_raw_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({k: (v or "").strip() for k, v in r.items()})
    return rows


def clean_rows(
    rows: List[Dict[str, str]],
    *,
    apply_refund_window_fix: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Trả về (cleaned, quarantine).

    Baseline (mở rộng theo narrative Day 10):
    1) Quarantine: doc_id không thuộc allowlist (export lạ / catalog sai).
    2) Chuẩn hoá effective_date sang YYYY-MM-DD; quarantine nếu không parse được.
    3) Quarantine: chunk hr_leave_policy có effective_date < 2026-01-01 (bản HR cũ / conflict version).
    4) Quarantine: chunk_text rỗng hoặc effective_date rỗng sau chuẩn hoá.
    5) Loại trùng nội dung chunk_text (giữ bản đầu).
    6) Fix stale refund: policy_refund_v4 chứa '14 ngày làm việc' → 7 ngày.
    """
    quarantine: List[Dict[str, Any]] = []
    seen_text: set[str] = set()
    cleaned: List[Dict[str, Any]] = []
    seq = 0

    for raw in rows:
        doc_id = raw.get("doc_id", "")
        text = raw.get("chunk_text", "")
        eff_raw = raw.get("effective_date", "")
        exported_at = raw.get("exported_at", "")

        if doc_id not in ALLOWED_DOC_IDS:
            quarantine.append({**raw, "reason": "unknown_doc_id"})
            continue

        eff_norm, eff_err = _normalize_effective_date(eff_raw)
        if eff_err == "empty_effective_date":
            quarantine.append({**raw, "reason": "missing_effective_date"})
            continue
        if eff_err == "invalid_effective_date_format":
            quarantine.append({**raw, "reason": eff_err, "effective_date_raw": eff_raw})
            continue

        exported_norm, exported_err = _normalize_exported_at(exported_at)
        if exported_err:
            quarantine.append({**raw, "reason": exported_err, "exported_at_raw": exported_at})
            continue

        if doc_id == "hr_leave_policy" and eff_norm < "2026-01-01":
            quarantine.append(
                {
                    **raw,
                    "reason": "stale_hr_policy_effective_date",
                    "effective_date_normalized": eff_norm,
                }
            )
            continue

        fixed_text = _add_retrieval_aliases(doc_id, _repair_chunk_text(text))

        if not fixed_text:
            quarantine.append({**raw, "reason": "missing_chunk_text"})
            continue

        if _is_ambiguous_placeholder(fixed_text):
            quarantine.append({**raw, "reason": "ambiguous_placeholder_text"})
            continue

        if _has_repeated_sentence_spam(fixed_text):
            quarantine.append({**raw, "reason": "repeated_sentence_spam"})
            continue

        if doc_id == "hr_leave_policy" and _is_stale_hr_annual_policy(fixed_text):
            quarantine.append(
                {
                    **raw,
                    "reason": "stale_hr_2025_content",
                    "effective_date_normalized": eff_norm,
                }
            )
            continue

        if apply_refund_window_fix and doc_id == "policy_refund_v4":
            if "14 ngày làm việc" in fixed_text:
                fixed_text = fixed_text.replace(
                    "14 ngày làm việc",
                    "7 ngày làm việc",
                )
                fixed_text += " [cleaned: stale_refund_window]"

        key = _norm_text(fixed_text)
        if key in seen_text:
            quarantine.append({**raw, "reason": "duplicate_chunk_text"})
            continue
        seen_text.add(key)

        seq += 1
        cleaned.append(
            {
                "chunk_id": _stable_chunk_id(doc_id, fixed_text, seq),
                "doc_id": doc_id,
                "chunk_text": fixed_text,
                "effective_date": eff_norm,
                "exported_at": exported_norm,
            }
        )

    return cleaned, quarantine


def write_cleaned_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at\n", encoding="utf-8")
        return
    fieldnames = ["chunk_id", "doc_id", "chunk_text", "effective_date", "exported_at"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def write_quarantine_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at,reason\n", encoding="utf-8")
        return
    keys: List[str] = []
    seen_k: set[str] = set()
    for r in rows:
        for k in r.keys():
            if k not in seen_k:
                seen_k.add(k)
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore", restval="")
        w.writeheader()
        for r in rows:
            w.writerow(r)
