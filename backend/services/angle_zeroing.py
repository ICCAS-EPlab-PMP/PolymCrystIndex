"""POLYCRYINDEX v1.8.5 — 归零重评 (Angle Zeroing Re-evaluation)

后处理步骤：对于优化得到的晶胞候选，检查 α, β, γ 是否接近 90°。
若某个角度偏离 90° 小于阈值 T，则生成归零版本（将该角度设为 90°），
重新计算残差。如果残差上升不超过 ΔR_max，则接受归零版本。

使用方式
--------
    from services.angle_zeroing import evaluate_angle_zeroing

    result = evaluate_angle_zeroing(
        cell_params={"a": 5.0, "b": 5.0, "c": 10.0,
                     "alpha": 89.5, "beta": 90.2, "gamma": 90.0},
        threshold=1.0,
        tolerance=0.5,
    )
    # result["accepted"] → True/False
    # result["zeroedCell"] → 归零后的晶胞参数（若接受）
"""

from typing import Any, Dict, List, Tuple

DEFAULT_ANGLE_ZEROING_THRESHOLD = 1.0
DEFAULT_ANGLE_ZEROING_TOLERANCE = 0.5
TARGET_RIGHT_ANGLE = 90.0


def _is_near_right_angle(angle: float, threshold: float) -> bool:
    """检查角度是否在阈值 T 内接近 90°。"""
    return abs(angle - TARGET_RIGHT_ANGLE) < threshold


def _zero_angles(
    cell_params: Dict[str, float], threshold: float
) -> Tuple[Dict[str, float], int]:
    """将接近 90° 的角度归零。

    Returns:
        (zeroed_cell, zero_count): 归零后的晶胞参数，以及归零的角度数量
    """
    zeroed = dict(cell_params)
    zero_count = 0
    for key in ("alpha", "beta", "gamma"):
        if key in zeroed and _is_near_right_angle(zeroed[key], threshold):
            zeroed[key] = TARGET_RIGHT_ANGLE
            zero_count += 1
    return zeroed, zero_count

def _compute_zeroed_residual(
    cell_params: Dict[str, float],
    observed_peaks: List[Dict[str, float]],
    hkl_assignments: List[Dict[str, int]],
    wavelength: float = 1.542,
) -> float:
    """用零化后的 cell 参数重新计算残差 R_factor。

    使用倒易点阵公式计算每个 hkl 的理论 q_calc，然后:
        R_factor = Σ|q_obs - q_calc| / Σ|q_obs|

    Args:
        cell_params: {a, b, c, alpha, beta, gamma}
        observed_peaks: [{q_obs, psi_obs}, ...]
        hkl_assignments: [{h, k, l}, ...]  — 与 observed_peaks 顺序对应
        wavelength: X 射线波长

    Returns:
        R_factor (float)
    """
    import math
    if not observed_peaks or not hkl_assignments:
        return 0.0

    a = cell_params.get("a", 1.0)
    b = cell_params.get("b", 1.0)
    c = cell_params.get("c", 1.0)
    alpha = math.radians(cell_params.get("alpha", 90.0))
    beta = math.radians(cell_params.get("beta", 90.0))
    gamma = math.radians(cell_params.get("gamma", 90.0))

    cos_a = math.cos(alpha)
    cos_b = math.cos(beta)
    cos_g = math.cos(gamma)
    sin_a = math.sin(alpha)
    sin_b = math.sin(beta)
    sin_g = math.sin(gamma)

    # 晶胞体积
    v_sq = 1.0 - cos_a * cos_a - cos_b * cos_b - cos_g * cos_g + 2.0 * cos_a * cos_b * cos_g
    if v_sq <= 0:
        return float("inf")
    volume = a * b * c * math.sqrt(v_sq)
    if volume <= 0:
        return float("inf")

    # 倒易点阵参数 (A11-F11)
    A11 = (b * b * c * c * sin_a * sin_a) / (volume * volume)
    B11 = (a * a * c * c * sin_b * sin_b) / (volume * volume)
    C11 = (a * a * b * b * sin_g * sin_g) / (volume * volume)
    D11 = 2.0 * a * b * c * c * (cos_a * cos_b - cos_g) / (volume * volume)
    E11 = 2.0 * a * a * b * c * (cos_g * cos_a - cos_b) / (volume * volume)
    F11 = 2.0 * a * b * b * c * (cos_b * cos_g - cos_a) / (volume * volume)

    n = min(len(observed_peaks), len(hkl_assignments))
    sum_abs_delta = 0.0
    sum_q_obs = 0.0

    for i in range(n):
        q_obs = float(observed_peaks[i].get("q_obs", observed_peaks[i].get("q", 0.0)))
        hkl = hkl_assignments[i]
        h = float(hkl.get("h", 0))
        k = float(hkl.get("k", 0))
        l = float(hkl.get("l", 0))

        # 1/d²
        d_star_sq = (
            A11 * h * h + B11 * k * k + C11 * l * l
            + D11 * h * k + E11 * k * l + F11 * h * l
        )
        if d_star_sq <= 0:
            continue

        q_calc = math.sqrt(d_star_sq) * 2.0 * math.pi / wavelength
        sum_abs_delta += abs(q_obs - q_calc)
        sum_q_obs += abs(q_obs)

    if sum_q_obs <= 0:
        return float("inf")

    return sum_abs_delta / sum_q_obs



def evaluate_angle_zeroing(
    candidate: Dict[str, Any],
    threshold: float = DEFAULT_ANGLE_ZEROING_THRESHOLD,
    tolerance: float = DEFAULT_ANGLE_ZEROING_TOLERANCE,
) -> Dict[str, Any]:
    """归零重评：评估晶胞候选是否应接受归零版本。

    算法：
        1. 检查 α/β/γ 是否在 threshold 度内接近 90°
        2. 生成归零版本（将接近的角度设为 90°）
        3. 比较原始残差 R 和归零残差 R'
        4. 若 R' - R ≤ tolerance（ΔR_max），则接受归零版本

    Args:
        candidate: 晶胞候选 dict，至少包含：
            - cellParams: {a, b, c, alpha, beta, gamma}
            - residual (或 r_factor / bestError): 原始残差
            可选：zeroedCellParams, zeroedResidual（若已计算）
        threshold: 角度阈值 T（度），默认 1.0°
        tolerance: 残差容忍上限 ΔR_max，默认 0.5

    Returns:
        {
            "evaluated": bool,          # 是否执行了归零重评
            "accepted": bool,           # 是否接受归零版本
            "zeroedAngles": List[str],  # 被归零的角度名称
            "originalCell": dict,       # 原始晶胞参数
            "zeroedCell": dict,         # 归零后晶胞参数（若 evaluated=True）
            "originalResidual": float,  # 原始残差
            "zeroedResidual": float,    # 归零后残差（若 evaluated=True）
            "residualChange": float,    # 残差变化量（R' - R）
            "threshold": float,         # 角度阈值
            "tolerance": float,         # 残差容忍上限
        }
    """
    cell_params = candidate.get("cellParams", {})
    if not cell_params:
        return {
            "evaluated": False,
            "accepted": False,
            "adapted": False,
            "reason": "missing_cell_params",
        }

    original_residual = float(
        candidate.get("residual")
        or candidate.get("r_factor")
        or candidate.get("bestError")
        or 0.0
    )

    # 找出接近 90° 的角度
    near_right_angles = []
    for key in ("alpha", "beta", "gamma"):
        if key in cell_params and _is_near_right_angle(cell_params[key], threshold):
            near_right_angles.append(key)

    if not near_right_angles:
        return {
            "evaluated": False,
            "accepted": False,
            "adapted": False,
            "reason": "no_angle_near_90",
            "originalCell": cell_params,
            "originalResidual": original_residual,
            "threshold": threshold,
            "tolerance": tolerance,
        }

    # 生成归零版本
    zeroed_cell, zero_count = _zero_angles(cell_params, threshold)

    # 如果已有预计算的归零残差，使用它
    zeroed_residual = float(
        candidate.get("zeroedResidual", 0.0)
        or candidate.get("zeroedRFactor", 0.0)
    )
    residual_precomputed = "zeroedResidual" in candidate or "zeroedRFactor" in candidate

    # Preserve Fortran raw error for reference before recomputing
    fortran_raw_error = original_residual

    if not residual_precomputed:
        # v1.9.1: 自行计算归零残差
        observed_peaks = candidate.get("observedPeaks", [])
        hkl_assignments = candidate.get("hklAssignments", [])
        wavelength = float(candidate.get("wavelength", 1.542))

        # Recompute original residual using SAME formula for fair comparison
        if observed_peaks and hkl_assignments:
            original_residual = _compute_zeroed_residual(
                cell_params, observed_peaks, hkl_assignments, wavelength
            )

        zeroed_residual = _compute_zeroed_residual(
            zeroed_cell, observed_peaks, hkl_assignments, wavelength
        )
        if zeroed_residual == float("inf"):
            return {
                "evaluated": True,
                "accepted": False,
                "adapted": False,
                "zeroedAngles": near_right_angles,
                "originalCell": cell_params,
                "zeroedCell": zeroed_cell,
                "originalResidual": original_residual,
                "zeroedResidual": None,
                "residualChange": None,
                "threshold": threshold,
                "tolerance": tolerance,
                "fortranRawError": fortran_raw_error,
                "reason": "residual_computation_failed",
            }

    residual_change = zeroed_residual - original_residual
    accepted = residual_change <= tolerance

    result = {
        "evaluated": True,
        "accepted": accepted,
        "adapted": accepted,
        "zeroedAngles": near_right_angles,
        "originalCell": cell_params,
        "zeroedCell": zeroed_cell,
        "originalResidual": original_residual,
        "zeroedResidual": zeroed_residual,
        "residualChange": residual_change,
        "threshold": threshold,
        "tolerance": tolerance,
        "fortranRawError": fortran_raw_error,
    }
    return result


def apply_angle_zeroing_to_results(
    results: Dict[str, Any],
    threshold: float = DEFAULT_ANGLE_ZEROING_THRESHOLD,
    tolerance: float = DEFAULT_ANGLE_ZEROING_TOLERANCE,
) -> Dict[str, Any]:
    """对一组结果批量应用归零重评。

    这是一个便利包装器，用于在 indexing_service 的后处理输出前
    批量评估多个晶胞候选。

    Args:
        results: 包含 cellParams 和 residual 的结果字典或列表
        threshold: 角度阈值
        tolerance: 残差容忍上限

    Returns:
        附加了 angleZeroing 字段的结果
    """
    if isinstance(results, list):
        processed = []
        for item in results:
            if isinstance(item, dict) and "cellParams" in item:
                zr = evaluate_angle_zeroing(item, threshold, tolerance)
                item["angleZeroing"] = zr
            processed.append(item)
        return processed
    elif isinstance(results, dict):
        if "cellParams" in results:
            zr = evaluate_angle_zeroing(results, threshold, tolerance)
            results["angleZeroing"] = zr
        return results
    return results
