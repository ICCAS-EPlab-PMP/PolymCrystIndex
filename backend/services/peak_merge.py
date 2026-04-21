"""Postprocess audit and reporting utility for peak symmetry groups.

The canonical source of truth for symmetry-enabled family matching is the
Fortran-generated ``outputMillerFamilies.jsonl`` artifact, ingested by
``indexing_service.py`` via ``_read_joint_match_groups()``.  That production
path uses ``_derive_legacy_peak_symmetry_groups_from_joint_matches()`` to emit
groups with the correct Fortran-backed family semantics.

This module provides an independent, Python-side implementation of hk-rule
validation and peak-symmetry group identification for audit and reporting
purposes only.  Its results may differ from the Fortran-backed path in
edge cases (e.g. sign-pattern handling, bucket formation).  No production
code should rely on this module as the source of truth for matching logic.
"""

from itertools import combinations
from typing import Any, Dict, Iterable, List, Sequence, Tuple


DEFAULT_PEAK_SYMMETRY_Q_THRESHOLD = 0.02
DEFAULT_PEAK_SYMMETRY_ANGLE_THRESHOLD = 1.0


def _get_peak_q(peak: Dict[str, Any]) -> float:
    for key in ("q", "q_obs", "qobs", "qcalc"):
        if key in peak and peak[key] is not None:
            return float(peak[key])
    raise ValueError("Peak is missing q value")


def _get_peak_angle(peak: Dict[str, Any]) -> float:
    for key in ("psi", "psi_obs", "psiobs", "psicalc"):
        if key in peak and peak[key] is not None:
            return float(peak[key])
    raise ValueError("Peak is missing psi angle")


def _normalize_peak(peak: Dict[str, Any], fallback_index: int) -> Dict[str, Any]:
    return {
        "peakIndex": int(peak.get("peakIndex", fallback_index)),
        "q": _get_peak_q(peak),
        "psi": _get_peak_angle(peak),
        "h": int(peak.get("h", 0)),
        "k": int(peak.get("k", 0)),
        "l": int(peak.get("l", 0)),
    }


def _pair_metrics(first: Dict[str, Any], second: Dict[str, Any]) -> Dict[str, float]:
    return {
        "deltaQ": abs(first["q"] - second["q"]),
        "deltaAngle": abs(first["psi"] - second["psi"]),
    }


def _all_pairs_within_threshold(
    peaks: Sequence[Dict[str, Any]], q_threshold: float, angle_threshold: float
) -> Tuple[bool, float, float, List[Dict[str, Any]]]:
    max_delta_q = 0.0
    max_delta_angle = 0.0
    pair_checks: List[Dict[str, Any]] = []

    for first, second in combinations(peaks, 2):
        metrics = _pair_metrics(first, second)
        max_delta_q = max(max_delta_q, metrics["deltaQ"])
        max_delta_angle = max(max_delta_angle, metrics["deltaAngle"])
        pair_checks.append(
            {
                "peakIndexPair": [first["peakIndex"], second["peakIndex"]],
                "deltaQ": metrics["deltaQ"],
                "deltaAngle": metrics["deltaAngle"],
                "withinThreshold": (
                    metrics["deltaQ"] <= q_threshold
                    and metrics["deltaAngle"] <= angle_threshold
                ),
            }
        )

    is_within = (
        all(item["withinThreshold"] for item in pair_checks) if pair_checks else False
    )
    return is_within, max_delta_q, max_delta_angle, pair_checks


def _sign(value: int) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _check_merge_gradient(peaks: Sequence[Dict[str, Any]], threshold: float) -> bool:
    """Check if candidate peaks have merge gradient (converging toward same position).

    Algorithm TBD - current framework:
    - threshold=0: skip check (pass)
    - threshold>0: check gradient convergence
    TODO: Fill in when user defines specific gradient calculation
    """
    if threshold <= 0:
        return True
    return True


def _hk_rule_details(peaks: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    abs_h_values = {abs(peak["h"]) for peak in peaks}
    abs_k_values = {abs(peak["k"]) for peak in peaks}
    l_values = {peak["l"] for peak in peaks}
    sign_variants = [(_sign(peak["h"]), _sign(peak["k"])) for peak in peaks]
    unique_sign_variants = sorted(set(sign_variants))
    member_count = len(peaks)

    same_hk_magnitude = len(abs_h_values) == 1 and len(abs_k_values) == 1
    same_l = len(l_values) == 1
    unique_sign_count_matches = len(unique_sign_variants) == member_count

    abs_h = next(iter(abs_h_values)) if len(abs_h_values) == 1 else None
    abs_k = next(iter(abs_k_values)) if len(abs_k_values) == 1 else None

    h_signs = {0} if abs_h == 0 else ({1, -1} if abs_h is not None else set())
    k_signs = {0} if abs_k == 0 else ({1, -1} if abs_k is not None else set())
    expected_variants = {(hs, ks) for hs in h_signs for ks in k_signs}

    opposite_sign_present = any(
        first[0] == -second[0] or first[1] == -second[1]
        for first, second in combinations(unique_sign_variants, 2)
    )

    member_count_supported = member_count in (2, 4)

    if abs_h == 0 and abs_k == 0:
        sign_pattern_ok = False
    elif member_count == 4:
        sign_pattern_ok = set(unique_sign_variants) == expected_variants
    else:
        sign_pattern_ok = len(unique_sign_variants) == 2 and opposite_sign_present

    if member_count == 4:
        hk_rule_passed = (
            member_count_supported
            and same_hk_magnitude
            and same_l
            and sign_pattern_ok
        )
    else:
        hk_rule_passed = (
            member_count_supported
            and same_hk_magnitude
            and same_l
            and unique_sign_count_matches
            and sign_pattern_ok
        )

    return {
        "hkRulePassed": hk_rule_passed,
        "sameAbsH": len(abs_h_values) == 1,
        "sameAbsK": len(abs_k_values) == 1,
        "sameL": same_l,
        "absH": abs_h,
        "absK": abs_k,
        "l": next(iter(l_values)) if len(l_values) == 1 else None,
        "signVariants": [list(item) for item in unique_sign_variants],
        "requiresSupportedMemberCount": member_count_supported,
        "signPatternOk": sign_pattern_ok,
    }


def _build_group(
    peaks: Sequence[Dict[str, Any]],
    q_threshold: float,
    angle_threshold: float,
    merge_gradient_enabled: bool = False,
    merge_gradient_threshold: float = 0.0,
) -> Dict[str, Any]:
    normalized_peaks = sorted(peaks, key=lambda item: item["peakIndex"])
    within_threshold, max_delta_q, max_delta_angle, pair_checks = (
        _all_pairs_within_threshold(normalized_peaks, q_threshold, angle_threshold)
    )
    hk_details = _hk_rule_details(normalized_peaks)
    member_count = len(normalized_peaks)

    gradient_passed = False
    if merge_gradient_enabled:
        gradient_passed = _check_merge_gradient(normalized_peaks, merge_gradient_threshold)

    return {
        "groupType": f"{member_count}-peak",
        "memberPeakIndices": [peak["peakIndex"] for peak in normalized_peaks],
        "memberCount": member_count,
        "withinThreshold": {
            "passed": within_threshold,
            "deltaQMax": max_delta_q,
            "deltaAngleMax": max_delta_angle,
            "Tq": q_threshold,
            "Ta": angle_threshold,
            "pairChecks": pair_checks,
        },
        "hkRulePassed": hk_details["hkRulePassed"],
        "hkRule": hk_details,
        "mergeGradient": {
            "enabled": merge_gradient_enabled,
            "passed": gradient_passed,
            "threshold": merge_gradient_threshold,
        },
        "members": normalized_peaks,
    }


def identify_peak_symmetry_groups(
    peaks: Iterable[Dict[str, Any]],
    q_threshold: float = DEFAULT_PEAK_SYMMETRY_Q_THRESHOLD,
    angle_threshold: float = DEFAULT_PEAK_SYMMETRY_ANGLE_THRESHOLD,
    merge_gradient_enabled: bool = False,
    merge_gradient_threshold: float = 0.0,
) -> List[Dict[str, Any]]:
    """Build symmetric 2-peak / 4-peak joint candidate groups.

    Peaks are kept as separate members. Grouping requires all member pairs to satisfy
    both thresholds simultaneously, and the hk rule requires equal |h|/|k|, equal l,
    plus supported sign variants (2 or all 4 combinations).
    """

    normalized_peaks = [
        _normalize_peak(peak, fallback_index)
        for fallback_index, peak in enumerate(peaks, start=1)
    ]
    signature_buckets: Dict[Tuple[int, int, int], List[Dict[str, Any]]] = {}
    for peak in normalized_peaks:
        signature = (abs(peak["h"]), abs(peak["k"]), peak["l"])
        signature_buckets.setdefault(signature, []).append(peak)

    groups: List[Dict[str, Any]] = []
    for bucket in signature_buckets.values():
        available = sorted(bucket, key=lambda item: item["peakIndex"])
        used_peak_indices = set()

        for target_size in (4, 2):
            while True:
                candidate_pool = [
                    peak
                    for peak in available
                    if peak["peakIndex"] not in used_peak_indices
                ]
                matched_group = None
                for combo in combinations(candidate_pool, target_size):
                    group = _build_group(
                        combo,
                        q_threshold,
                        angle_threshold,
                        merge_gradient_enabled,
                        merge_gradient_threshold,
                    )
                    if group["withinThreshold"]["passed"] and group["hkRulePassed"]:
                        matched_group = group
                        break

                if matched_group is None:
                    break

                groups.append(matched_group)
                used_peak_indices.update(matched_group["memberPeakIndices"])

    groups.sort(key=lambda item: (item["memberCount"], item["memberPeakIndices"]))
    return groups


def build_peak_symmetry_groups_from_results(
    diffraction_data: Sequence[Dict[str, Any]],
    miller_data: Sequence[Dict[str, Any]],
    q_threshold: float = DEFAULT_PEAK_SYMMETRY_Q_THRESHOLD,
    angle_threshold: float = DEFAULT_PEAK_SYMMETRY_ANGLE_THRESHOLD,
    merge_gradient_enabled: bool = False,
    merge_gradient_threshold: float = 0.0,
) -> List[Dict[str, Any]]:
    """Secondary / reporting-only helper — zips observed peaks with Miller assignments.

    **This function is NOT the canonical matching source.**  The production path
    uses ``_read_joint_match_groups()`` (reads Fortran's ``outputMillerFamilies.jsonl``)
    and ``_derive_legacy_peak_symmetry_groups_from_joint_matches()`` in
    ``indexing_service.py``.  This Python helper re-derives groups from in-memory
    data for audit / reporting purposes only; its grouping semantics may diverge
    from the Fortran artifact in edge cases.
    """

    paired_peaks = []
    for peak_index, (diffraction_peak, miller_peak) in enumerate(
        zip(diffraction_data, miller_data), start=1
    ):
        paired_peaks.append(
            {
                "peakIndex": peak_index,
                "q": diffraction_peak.get("q_obs"),
                "psi": diffraction_peak.get("psi_obs"),
                "h": miller_peak.get("h", 0),
                "k": miller_peak.get("k", 0),
                "l": miller_peak.get("l", 0),
            }
        )

    return identify_peak_symmetry_groups(
        paired_peaks,
        q_threshold=q_threshold,
        angle_threshold=angle_threshold,
        merge_gradient_enabled=merge_gradient_enabled,
        merge_gradient_threshold=merge_gradient_threshold,
    )
