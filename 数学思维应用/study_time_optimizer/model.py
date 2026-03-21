from __future__ import annotations

import math
from typing import Dict, List, Optional


class StudyTimeModel:
    @staticmethod
    def s_star(t: float, eta: float, theta: float, M: float, S0: float) -> float:
        return (eta * t * M + theta * S0) / (eta * t + theta)

    @staticmethod
    def t_min(cur: float, eta: float, theta: float, M: float, S0: float) -> float:
        denom = eta * (M - cur)
        if denom <= 0:
            return 0.0
        return max(0.0, theta * (cur - S0) / denom)

    @staticmethod
    def validate_subjects(subjects: List[Dict]) -> Optional[str]:
        for s in subjects:
            if s["eta"] <= 0 or s["theta"] <= 0:
                return f"{s['name']} 的 eta 与 theta 必须大于 0。"
            if s["M"] <= s["S0"]:
                return f"{s['name']} 的长期上限 M 必须大于基础分 S0。"
            if not (s["S0"] <= s["cur"] <= s["M"]):
                return f"{s['name']} 需满足 S0 <= S_cur <= M。"
        return None

    @staticmethod
    def calc_global_opt(subjects: List[Dict], total_time: float) -> Dict[str, float]:
        def total_alloc_time(lam: float) -> float:
            total = 0.0
            for s in subjects:
                a = s["eta"] * s["theta"] * (s["M"] - s["S0"])
                val = math.sqrt(a / lam) - s["theta"]
                if val > 0:
                    total += val / s["eta"]
            return total

        low, high = 1e-12, 1e6
        for _ in range(100):
            mid = (low + high) / 2.0
            if total_alloc_time(mid) > total_time:
                low = mid
            else:
                high = mid
        lam = (low + high) / 2.0

        alloc = {}
        for s in subjects:
            a = s["eta"] * s["theta"] * (s["M"] - s["S0"])
            val = math.sqrt(a / lam) - s["theta"]
            alloc[s["name"]] = max(0.0, val / s["eta"])
        return alloc
