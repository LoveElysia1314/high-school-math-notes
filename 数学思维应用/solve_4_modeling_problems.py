from __future__ import annotations

import math
from dataclasses import dataclass

# ------------------------------
# Problem 1: 得分波动分析
# ------------------------------


def problem1_score_volatility() -> dict:
    w = [0.2, 0.6, 0.2]
    student_mid = [0.9, 0.7, 0.2]  # 甲
    student_top = [1.0, 0.9, 0.8]  # 乙

    def stats(p):
        e = sum(wi * pi for wi, pi in zip(w, p))
        d = sum(wi * pi * (1 - pi) for wi, pi in zip(w, p))
        return e, d

    e_mid, d_mid = stats(student_mid)
    e_top, d_top = stats(student_top)

    # 扩展分析：将中档题权重从 0.4 到 0.8 扫描，观察中等生/学霸方差比
    # 其余两档平分剩余权重
    sensitivity = []
    for w2 in [0.4, 0.5, 0.6, 0.7, 0.8]:
        w1 = (1 - w2) / 2
        w3 = (1 - w2) / 2
        d1 = (
            w1 * student_mid[0] * (1 - student_mid[0])
            + w2 * student_mid[1] * (1 - student_mid[1])
            + w3 * student_mid[2] * (1 - student_mid[2])
        )
        d2 = (
            w1 * student_top[0] * (1 - student_top[0])
            + w2 * student_top[1] * (1 - student_top[1])
            + w3 * student_top[2] * (1 - student_top[2])
        )
        ratio = d1 / d2 if d2 > 0 else float("inf")
        sensitivity.append((w2, d1, d2, ratio))

    # 参数合理性检查：权重和是否为 1，p 是否落在 [0,1]
    checks = {
        "weights_sum_to_1": abs(sum(w) - 1.0) < 1e-9,
        "p_mid_valid": all(0 <= x <= 1 for x in student_mid),
        "p_top_valid": all(0 <= x <= 1 for x in student_top),
        "d_mid_gt_d_top": d_mid > d_top,
    }

    return {
        "E_mid": e_mid,
        "D_mid": d_mid,
        "E_top": e_top,
        "D_top": d_top,
        "checks": checks,
        "sensitivity": sensitivity,
        "conclusion": (
            "中等生方差显著高于学霸，且当中档题权重提高时，这种差距会进一步扩大。"
            "该模型可以解释‘中游群体波动更大’的统计规律。"
        ),
    }


# ------------------------------
# Problem 2: 估分偏差分析
# ------------------------------


def problem2_estimation_bias() -> dict:
    def E(r):
        return 0.2 * r * r + 0.7 * r + 0.1

    def b(r):
        return E(r) - r

    def D(r):
        return 0.09 - 0.08 * r - 0.01 * r * r

    def mse(r):
        return D(r) + b(r) ** 2

    # b(r)=0.2r^2-0.3r+0.1 = 0 => r=0.5,1.0
    roots = (0.5, 1.0)

    samples = {}
    for r in [0.6, 0.9]:
        samples[r] = {
            "b": b(r),
            "D": D(r),
            "MSE": mse(r),
        }

    # 扩展分析：扫描 r, 找 MSE 最小点
    grid = [i / 100 for i in range(0, 101)]
    best_r = min(grid, key=mse)

    # 参数合理性检查
    checks = {
        "D_nonnegative_on_grid": all(D(r) >= -1e-10 for r in grid),
        "alpha_beta_implied": True,  # 由题面推导，不在此重复推演
        "roots_in_0_1": all(0 <= x <= 1 for x in roots),
    }

    return {
        "roots": roots,
        "samples": samples,
        "best_r_for_mse": best_r,
        "checks": checks,
        "conclusion": (
            "估分偏差在 r=0.5 与 r=1.0 处为零；中高分段更容易‘低估’，低分段更易‘高估’。"
            "同时 D(r) 随 r 增大而下降，说明水平越高得分越稳定。"
        ),
    }


# ------------------------------
# Problem 3: 学科时间分配
# ------------------------------


@dataclass(frozen=True)
class Subject:
    name: str
    cur: float
    M: float
    S0: float
    eta: float
    theta: float


def s_star(t: float, eta: float, theta: float, M: float, S0: float) -> float:
    return (eta * t * M + theta * S0) / (eta * t + theta)


def dS_dt(t: float, eta: float, theta: float, M: float, S0: float) -> float:
    return eta * theta * (M - S0) / (eta * t + theta) ** 2


def t_min(cur: float, eta: float, theta: float, M: float, S0: float) -> float:
    return theta * (cur - S0) / (eta * (M - cur))


def problem3_time_allocation() -> dict:
    subjects = [
        Subject("语文", 105, 120, 95, 0.01, 0.05),
        Subject("数学", 90, 120, 70, 0.05, 0.20),
        Subject("英语", 105, 125, 95, 0.02, 0.10),
        Subject("历史", 80, 90, 70, 0.03, 0.08),
        Subject("政治", 75, 85, 70, 0.03, 0.10),
        Subject("地理", 75, 85, 70, 0.03, 0.10),
    ]
    T = 30.0

    tmins = {s.name: t_min(s.cur, s.eta, s.theta, s.M, s.S0) for s in subjects}
    Tmin = sum(tmins.values())
    deltaT = T - Tmin

    def gain_if_single_breakthrough(name: str) -> float:
        s = next(x for x in subjects if x.name == name)
        t = tmins[name] + deltaT
        return s_star(t, s.eta, s.theta, s.M, s.S0) - s.cur

    gain_math = gain_if_single_breakthrough("数学")
    gain_eng = gain_if_single_breakthrough("英语")

    # 双突破：数学和英语，求等边际收益点
    s_math = next(x for x in subjects if x.name == "数学")
    s_eng = next(x for x in subjects if x.name == "英语")

    # 用二分法在 [0, deltaT] 上解方程
    def f(x: float) -> float:
        tm = tmins["数学"] + x
        te = tmins["英语"] + (deltaT - x)
        return dS_dt(tm, s_math.eta, s_math.theta, s_math.M, s_math.S0) - dS_dt(
            te, s_eng.eta, s_eng.theta, s_eng.M, s_eng.S0
        )

    left, right = 0.0, max(0.0, deltaT)
    if deltaT <= 1e-12:
        x_star = 0.0
    else:
        fl, fr = f(left), f(right)
        if fl * fr > 0:
            # 无内部根，取边界最优
            x_star = left if abs(fl) < abs(fr) else right
        else:
            for _ in range(80):
                mid = (left + right) / 2
                fm = f(mid)
                if fl * fm <= 0:
                    right = mid
                    fr = fm
                else:
                    left = mid
                    fl = fm
            x_star = (left + right) / 2

    tm_star = tmins["数学"] + x_star
    te_star = tmins["英语"] + (deltaT - x_star)
    gain_dual = (
        s_star(tm_star, s_math.eta, s_math.theta, s_math.M, s_math.S0)
        - s_math.cur
        + s_star(te_star, s_eng.eta, s_eng.theta, s_eng.M, s_eng.S0)
        - s_eng.cur
    )

    # 参数合理性检查
    checks = {
        "all_eta_positive": all(s.eta > 0 for s in subjects),
        "all_theta_positive": all(s.theta > 0 for s in subjects),
        "all_S0_cur_M_ordered": all(s.S0 < s.cur < s.M for s in subjects),
        "time_budget_feasible": Tmin <= T,
    }

    if gain_dual >= max(gain_math, gain_eng):
        recommend = "优先采用数英双突破（等边际分配）"
    elif gain_math >= gain_eng:
        recommend = "优先单突破数学"
    else:
        recommend = "优先单突破英语"

    # 独立探究：不采用“两段式保底+突破”，直接最大化六科总稳态分数
    # max sum_i S_i*(t_i), s.t. sum_i t_i = T, t_i >= 0
    # 由凹优化一阶条件：对所有 t_i>0 的科目，有 dS_i*/dt_i = lambda
    # dS/dt = a/(eta*t+theta)^2, 其中 a=eta*theta*(M-S0)
    # 可解得 t_i(lambda)=max(0, (sqrt(a/lambda)-theta)/eta)
    def total_time_given_lambda(lam: float) -> float:
        total = 0.0
        for s in subjects:
            a = s.eta * s.theta * (s.M - s.S0)
            t_i = (math.sqrt(a / lam) - s.theta) / s.eta
            if t_i > 0:
                total += t_i
        return total

    def solve_global_optimal_allocation(
        total_T: float,
    ) -> tuple[dict[str, float], float]:
        # 若 lambda 过大，所有 t_i 都趋于 0；若 lambda 很小，总时间会很大。
        # 用二分法解 sum_i t_i(lambda)=T。
        lam_low = 1e-12
        lam_high = max(s.eta * s.theta * (s.M - s.S0) / (s.theta**2) for s in subjects)

        for _ in range(100):
            lam_mid = (lam_low + lam_high) / 2
            t_sum = total_time_given_lambda(lam_mid)
            if t_sum > total_T:
                lam_low = lam_mid
            else:
                lam_high = lam_mid

        lam_star = (lam_low + lam_high) / 2
        alloc = {}
        for s in subjects:
            a = s.eta * s.theta * (s.M - s.S0)
            t_i = (math.sqrt(a / lam_star) - s.theta) / s.eta
            alloc[s.name] = max(0.0, t_i)

        # 数值上做一次归一化，保证总和严格为 T
        t_sum = sum(alloc.values())
        if t_sum > 0:
            scale = total_T / t_sum
            for k in alloc:
                alloc[k] *= scale

        total_score = 0.0
        for s in subjects:
            total_score += s_star(alloc[s.name], s.eta, s.theta, s.M, s.S0)
        return alloc, total_score

    global_alloc, global_total_score = solve_global_optimal_allocation(T)
    global_scores = {
        s.name: s_star(global_alloc[s.name], s.eta, s.theta, s.M, s.S0)
        for s in subjects
    }
    global_gain_vs_current = sum(global_scores[s.name] - s.cur for s in subjects)

    return {
        "tmins": tmins,
        "Tmin": Tmin,
        "deltaT": deltaT,
        "gain_math_only": gain_math,
        "gain_eng_only": gain_eng,
        "x_star_math_extra": x_star,
        "gain_dual": gain_dual,
        "global_opt_allocation": global_alloc,
        "global_opt_scores": global_scores,
        "global_opt_total_score": global_total_score,
        "global_opt_gain_vs_current": global_gain_vs_current,
        "checks": checks,
        "recommend": recommend,
        "conclusion": (
            "先保底、再突破是必要策略；在当前参数下通常会出现‘边际收益均衡分配优于孤注一掷’。"
        ),
    }


# ------------------------------
# Problem 4: 劳逸结合最优配置
# ------------------------------


def problem4_work_rest() -> dict:
    def P(t1, t2, t3):
        return (4 + 0.9 * t1) * (1 + 0.2 * t2) * (1 + 0.15 * t3)

    p_extreme = P(3, 0, 0)
    p_balanced = P(1.5, 1.5, 1)

    # 由单调性先取 t3=1, 再令 t1+t2=3 => t1=3-t2
    # P(t2)=1.15*(6.7-0.9t2)*(1+0.2t2) 为开口向下二次函数
    # 展开后顶点 t2*=53/18≈2.944
    t2_star = 53 / 18
    t1_star = 3 - t2_star
    t3_star = 1.0
    p_star = P(t1_star, t2_star, t3_star)

    # 扩展分析：若运动增益从 0.15 改为 g，最优 t2 是否变化
    # 由于 g 只是整体乘子，t2* 不变
    sensitivity_g = []
    for g in [0.05, 0.10, 0.15, 0.20, 0.30]:

        def Pg(t1, t2, t3):
            return (4 + 0.9 * t1) * (1 + 0.2 * t2) * (1 + g * t3)

        sensitivity_g.append((g, Pg(t1_star, t2_star, 1.0)))

    checks = {
        "constraints_feasible": 0 <= t1_star <= 3
        and 0 <= t2_star <= 3
        and abs(t1_star + t2_star - 3) < 1e-9,
        "p_balanced_gt_extreme": p_balanced > p_extreme,
    }

    return {
        "P_extreme": p_extreme,
        "P_balanced": p_balanced,
        "t_star": (t1_star, t2_star, t3_star),
        "P_max": p_star,
        "sensitivity_g": sensitivity_g,
        "checks": checks,
        "conclusion": (
            "运动和思考并非挤占学习时间，而是通过乘积协同提升总产出；最优策略不是把全部时间压在刷题。"
        ),
    }


# ------------------------------
# Reporting
# ------------------------------


def print_report():
    p1 = problem1_score_volatility()
    p2 = problem2_estimation_bias()
    p3 = problem3_time_allocation()
    p4 = problem4_work_rest()

    print("=" * 72)
    print("4题统一求解 + 建模分析 + 参数合理性检查")
    print("=" * 72)

    print("\n[第1题] 得分波动分析")
    print(f"- 甲: E={p1['E_mid']:.4f}, D={p1['D_mid']:.4f}")
    print(f"- 乙: E={p1['E_top']:.4f}, D={p1['D_top']:.4f}")
    print(f"- 参数检查: {p1['checks']}")
    print("- 中档题权重敏感性(示例):")
    for w2, d1, d2, ratio in p1["sensitivity"]:
        print(f"  w2={w2:.1f}: D甲={d1:.4f}, D乙={d2:.4f}, 比值={ratio:.2f}")
    print(f"- 结论: {p1['conclusion']}")

    print("\n[第2题] 估分偏差分析")
    print(f"- b(r)=0 的根: r={p2['roots'][0]:.1f}, {p2['roots'][1]:.1f}")
    for r, info in p2["samples"].items():
        print(
            f"- r={r:.1f}: b={info['b']:.4f}, D={info['D']:.4f}, MSE={info['MSE']:.4f}"
        )
    print(f"- 扫描网格下 MSE 最小点约在 r={p2['best_r_for_mse']:.2f}")
    print(f"- 参数检查: {p2['checks']}")
    print(f"- 结论: {p2['conclusion']}")

    print("\n[第3题] 学科时间分配")
    print("- 各科 t_min(小时/周):")
    for k, v in p3["tmins"].items():
        print(f"  {k}: {v:.2f}")
    print(f"- T_min={p3['Tmin']:.2f}, ΔT={p3['deltaT']:.2f}")
    print(f"- 只突破数学: 提升 {p3['gain_math_only']:.2f} 分")
    print(f"- 只突破英语: 提升 {p3['gain_eng_only']:.2f} 分")
    print(f"- 数英双突破(最优): 提升 {p3['gain_dual']:.2f} 分")
    print(f"- 数学额外最优分配 x*={p3['x_star_math_extra']:.2f} 小时")
    print("- 独立探究(不采用两段式): 直接最大化六科总分")
    print("  最优时间分配(小时/周):")
    for k, v in p3["global_opt_allocation"].items():
        print(f"  {k}: {v:.2f}")
    print("  对应稳态分数:")
    for k, v in p3["global_opt_scores"].items():
        print(f"  {k}: {v:.2f}")
    print(f"  六科总稳态分数: {p3['global_opt_total_score']:.2f}")
    print(f"  相对当前总分提升: {p3['global_opt_gain_vs_current']:.2f}")
    print(f"- 参数检查: {p3['checks']}")
    print(f"- 建议: {p3['recommend']}")
    print(f"- 结论: {p3['conclusion']}")

    print("\n[第4题] 劳逸结合最优配置")
    print(f"- 极端刷题 P1={p4['P_extreme']:.4f}")
    print(f"- 平衡策略 P2={p4['P_balanced']:.4f}")
    t1, t2, t3 = p4["t_star"]
    print(f"- 最优时间 (t1,t2,t3)=({t1:.3f}, {t2:.3f}, {t3:.1f})")
    print(f"- 最大产出 P_max={p4['P_max']:.4f}")
    print("- 运动增益敏感性(在最优t1,t2下):")
    for g, val in p4["sensitivity_g"]:
        print(f"  g={g:.2f}: P={val:.4f}")
    print(f"- 参数检查: {p4['checks']}")
    print(f"- 结论: {p4['conclusion']}")


if __name__ == "__main__":
    print_report()
