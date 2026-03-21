from __future__ import annotations

CONFIG_FILE = "study_config.json"
PRESETS_FILE = "study_presets.json"
PANEL_STATE_FILE = "study_panel_state.json"
CURVE_STRENGTH = 1.0

SUBJECT_SCORE_DEFAULTS = {
    "语文": [105, 120, 95],
    "数学": [90, 120, 70],
    "英语": [105, 125, 95],
    "物理": [80, 90, 70],
    "历史": [80, 90, 70],
    "生物": [80, 90, 70],
    "化学": [80, 90, 70],
    "政治": [75, 85, 70],
    "地理": [75, 85, 70],
}

SUBJECT_ADVANCED_DEFAULTS = {
    "语文": [0.01, 0.05],
    "数学": [0.05, 0.20],
    "英语": [0.02, 0.10],
    "物理": [0.04, 0.12],
    "历史": [0.03, 0.08],
    "生物": [0.03, 0.10],
    "化学": [0.03, 0.10],
    "政治": [0.03, 0.10],
    "地理": [0.03, 0.10],
}

CORE_SUBJECTS = ["语文", "数学", "英语"]
GROUP_A = ["物理", "历史"]
GROUP_B = ["生物", "化学", "政治", "地理"]
DEFAULT_ELECTIVES = ["历史", "政治", "地理"]

SUBJECT_AXIS = {
    "语文": -0.8,
    "数学": 1.0,
    "英语": -1.0,
    "物理": 1.0,
    "历史": 0.5,
    "生物": 0.5,
    "化学": 0.7,
    "政治": -0.9,
    "地理": -0.5,
}

SUBJECT_FULL_MARKS = {
    "语文": 150,
    "数学": 150,
    "英语": 150,
    "物理": 100,
    "历史": 100,
    "生物": 100,
    "化学": 100,
    "政治": 100,
    "地理": 100,
}

SPECTRUM_ELECTIVES = {
    "偏文": ["历史", "政治", "地理"],
    "偏理": ["物理", "生物", "化学"],
    "均衡": ["历史", "生物", "化学"],
}

PRESET_CONFIGS = {
    "学神-均衡": {
        "mode": "parametric",
        "params": {
            "overall_rate": 0.90,
            "student_spectrum": 0.0,
            "delta_base_exp": 0.1,
            "delta_cap_exp": 0.3,
        },
        "electives": ["历史", "生物", "化学"],
    },
    "学霸-偏理": {
        "mode": "parametric",
        "params": {
            "overall_rate": 0.82,
            "student_spectrum": 0.5,
            "delta_base_exp": 0.1,
            "delta_cap_exp": 0.3,
        },
        "electives": ["物理", "生物", "化学"],
    },
    "学霸-偏文": {
        "mode": "parametric",
        "params": {
            "overall_rate": 0.82,
            "student_spectrum": -0.5,
            "delta_base_exp": 0.1,
            "delta_cap_exp": 0.3,
        },
        "electives": ["历史", "政治", "地理"],
    },
    "学酥-偏理": {
        "mode": "parametric",
        "params": {
            "overall_rate": 0.70,
            "student_spectrum": 0.5,
            "delta_base_exp": 0.1,
            "delta_cap_exp": 0.3,
        },
        "electives": ["物理", "生物", "化学"],
    },
    "学酥-偏文": {
        "mode": "parametric",
        "params": {
            "overall_rate": 0.70,
            "student_spectrum": -0.5,
            "delta_base_exp": 0.1,
            "delta_cap_exp": 0.3,
        },
        "electives": ["历史", "政治", "地理"],
    },
}
