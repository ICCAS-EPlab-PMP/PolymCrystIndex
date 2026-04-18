"""Helpers for nearby-peak joint candidate grouping."""

from itertools import combinations
from typing import Any, Dict, Iterable, List, Sequence, Tuple


DEFAULT_NEAR_PEAK_Q_THRESHOLD = 0.2
DEFAULT_NEAR_PEAK_ANGLE_THRESHOLD = 2.0


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
    opposite_sign_present = any(
        first[0] == -second[0] or first[1] == -second[1]
        for first, second in combinations(unique_sign_variants, 2)
    )

    member_count_supported = member_count in (2, 4)
    if member_count == 4:
        expected_variants = {
            (1, 1),
            (1, -1),
            (-1, 1),
            (-1, -1),
        }
        sign_pattern_ok = set(unique_sign_variants) == expected_variants
    else:
        sign_pattern_ok = len(unique_sign_variants) == 2 and opposite_sign_present

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
        "absH": next(iter(abs_h_values)) if len(abs_h_values) == 1 else None,
        "absK": next(iter(abs_k_values)) if len(abs_k_values) == 1 else None,
        "l": next(iter(l_values)) if len(l_values) == 1 else None,
        "signVariants": [list(item) for item in unique_sign_variants],
        "requiresSupportedMemberCount": member_count_supported,
        "signPatternOk": sign_pattern_ok,
    }


def _build_group(
    peaks: Sequence[Dict[str, Any]], q_threshold: float, angle_threshold: float
) -> Dict[str, Any]:
    normalized_peaks = sorted(peaks, key=lambda item: item["peakIndex"])
    within_threshold, max_delta_q, max_delta_angle, pair_checks = (
        _all_pairs_within_threshold(normalized_peaks, q_threshold, angle_threshold)
    )
    hk_details = _hk_rule_details(normalized_peaks)
    member_count = len(normalized_peaks)

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
        "members": normalized_peaks,
    }


def identify_near_peak_groups(
    peaks: Iterable[Dict[str, Any]],
    q_threshold: float = DEFAULT_NEAR_PEAK_Q_THRESHOLD,
    angle_threshold: float = DEFAULT_NEAR_PEAK_ANGLE_THRESHOLD,
) -> List[Dict[str, Any]]:
    """Build nearby 2-peak / 4-peak joint candidate groups.

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
                    group = _build_group(combo, q_threshold, angle_threshold)
                    if group["withinThreshold"]["passed"] and group["hkRulePassed"]:
                        matched_group = group
                        break

                if matched_group is None:
                    break

                groups.append(matched_group)
                used_peak_indices.update(matched_group["memberPeakIndices"])

        # 保持输出稳定，避免同一桶里已使用成员再次参与后续组合。

    groups.sort(key=lambda item: (item["memberCount"], item["memberPeakIndices"]))
    return groups


def build_near_peak_groups_from_results(
    diffraction_data: Sequence[Dict[str, Any]],
    miller_data: Sequence[Dict[str, Any]],
    q_threshold: float = DEFAULT_NEAR_PEAK_Q_THRESHOLD,
    angle_threshold: float = DEFAULT_NEAR_PEAK_ANGLE_THRESHOLD,
) -> List[Dict[str, Any]]:
    """Zip observed peaks with parsed Miller assignments and build joint groups."""

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

    return identify_near_peak_groups(
        paired_peaks,
        q_threshold=q_threshold,
        angle_threshold=angle_threshold,
    )
