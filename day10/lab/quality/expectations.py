"""
Expectation suite đơn giản (không bắt buộc Great Expectations).

Sinh viên có thể thay bằng GE / pydantic / custom — miễn là có halt có kiểm soát.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


CANONICAL_DOC_IDS = {
    "policy_refund_v4",
    "sla_p1_2026",
    "it_helpdesk_faq",
    "hr_leave_policy",
    "access_control_sop",
}


@dataclass
class ExpectationResult:
    name: str
    passed: bool
    severity: str  # "warn" | "halt"
    detail: str


def run_expectations(cleaned_rows: List[Dict[str, Any]]) -> Tuple[List[ExpectationResult], bool]:
    """
    Trả về (results, should_halt).

    should_halt = True nếu có bất kỳ expectation severity halt nào fail.
    """
    results: List[ExpectationResult] = []

    # E1: có ít nhất 1 dòng sau clean
    ok = len(cleaned_rows) >= 1
    results.append(
        ExpectationResult(
            "min_one_row",
            ok,
            "halt",
            f"cleaned_rows={len(cleaned_rows)}",
        )
    )

    # E2: không doc_id rỗng
    bad_doc = [r for r in cleaned_rows if not (r.get("doc_id") or "").strip()]
    ok2 = len(bad_doc) == 0
    results.append(
        ExpectationResult(
            "no_empty_doc_id",
            ok2,
            "halt",
            f"empty_doc_id_count={len(bad_doc)}",
        )
    )

    # E3: policy refund không được chứa cửa sổ sai 14 ngày (sau khi đã fix)
    bad_refund = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "policy_refund_v4"
        and "14 ngày làm việc" in (r.get("chunk_text") or "")
    ]
    ok3 = len(bad_refund) == 0
    results.append(
        ExpectationResult(
            "refund_no_stale_14d_window",
            ok3,
            "halt",
            f"violations={len(bad_refund)}",
        )
    )

    # E4: chunk_text đủ dài
    short = [r for r in cleaned_rows if len((r.get("chunk_text") or "")) < 8]
    ok4 = len(short) == 0
    results.append(
        ExpectationResult(
            "chunk_min_length_8",
            ok4,
            "warn",
            f"short_chunks={len(short)}",
        )
    )

    # E5: effective_date đúng định dạng ISO sau clean (phát hiện parser lỏng)
    iso_bad = [
        r
        for r in cleaned_rows
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", (r.get("effective_date") or "").strip())
    ]
    ok5 = len(iso_bad) == 0
    results.append(
        ExpectationResult(
            "effective_date_iso_yyyy_mm_dd",
            ok5,
            "halt",
            f"non_iso_rows={len(iso_bad)}",
        )
    )

    # E6: không còn marker phép năm cũ 10 ngày trên doc HR (conflict version sau clean)
    bad_hr_annual = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "hr_leave_policy"
        and "10 ngày phép năm" in (r.get("chunk_text") or "")
    ]
    ok6 = len(bad_hr_annual) == 0
    results.append(
        ExpectationResult(
            "hr_leave_no_stale_10d_annual",
            ok6,
            "halt",
            f"violations={len(bad_hr_annual)}",
        )
    )

    # E7: chunk_id phai la khoa on dinh va unique de rerun/upsert khong phinh index
    chunk_ids = [(r.get("chunk_id") or "").strip() for r in cleaned_rows]
    duplicate_chunk_ids = len(chunk_ids) - len(set(chunk_ids))
    missing_chunk_ids = sum(1 for x in chunk_ids if not x)
    ok7 = duplicate_chunk_ids == 0 and missing_chunk_ids == 0
    results.append(
        ExpectationResult(
            "unique_nonempty_chunk_id",
            ok7,
            "halt",
            f"missing_chunk_ids={missing_chunk_ids}, duplicate_chunk_ids={duplicate_chunk_ids}",
        )
    )

    # E8: grading can tra du 5 source canonical, dac biet access_control_sop.
    present_doc_ids = {r.get("doc_id") for r in cleaned_rows if r.get("doc_id")}
    missing_docs = sorted(CANONICAL_DOC_IDS - present_doc_ids)
    ok8 = len(missing_docs) == 0
    results.append(
        ExpectationResult(
            "canonical_doc_coverage",
            ok8,
            "halt",
            f"missing_doc_ids={missing_docs}",
        )
    )

    # E9: khong con marker ban HR 2025 trong cleaned, ke ca bien the khong dung exact phrase.
    bad_hr_marker = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "hr_leave_policy"
        and (
            "bản hr 2025" in (r.get("chunk_text") or "").lower()
            or re.search(r"\b10\s+ngày(?:\s+làm\s+việc)?\s+phép\s+năm\b", (r.get("chunk_text") or "").lower())
        )
    ]
    ok9 = len(bad_hr_marker) == 0
    results.append(
        ExpectationResult(
            "hr_leave_no_2025_marker",
            ok9,
            "halt",
            f"violations={len(bad_hr_marker)}",
        )
    )

    # E10: freshness monitor can doc exported_at, nen cleaned phai giu ISO datetime.
    exported_bad = [
        r
        for r in cleaned_rows
        if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$", (r.get("exported_at") or "").strip())
    ]
    ok10 = len(exported_bad) == 0
    results.append(
        ExpectationResult(
            "exported_at_iso_datetime",
            ok10,
            "halt",
            f"non_iso_exported_at_rows={len(exported_bad)}",
        )
    )

    # E11: cau grading access Level 4 phai co evidence sau clean.
    access_l4 = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "access_control_sop"
        and "level 4" in (r.get("chunk_text") or "").lower()
        and "ciso" in (r.get("chunk_text") or "").lower()
    ]
    ok11 = len(access_l4) >= 1
    results.append(
        ExpectationResult(
            "access_control_level4_present",
            ok11,
            "halt",
            f"matching_rows={len(access_l4)}",
        )
    )

    # E12: cau escalation P1 can chunk 10 phut va alias auto escalate de retrieval on dinh.
    p1_escalation = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "sla_p1_2026"
        and "10 phút" in (r.get("chunk_text") or "").lower()
        and "auto escalate" in (r.get("chunk_text") or "").lower()
    ]
    ok12 = len(p1_escalation) >= 1
    results.append(
        ExpectationResult(
            "sla_p1_auto_escalate_10min_present",
            ok12,
            "halt",
            f"matching_rows={len(p1_escalation)}",
        )
    )

    halt = any(not r.passed and r.severity == "halt" for r in results)
    return results, halt
