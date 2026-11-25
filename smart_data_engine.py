"""Smart Data Engine for Libya OilCast AI.

Pure data-inspection helpers. This module does not modify the original DataFrame
and is intentionally independent from Streamlit so it can be tested separately.
"""
from __future__ import annotations

import re
from typing import Any

import pandas as pd


def normalize_name(name: Any) -> str:
    """Normalize an English/Arabic column label for conservative matching."""
    value = str(name).strip().lower().replace("%", " pct ")
    value = re.sub(r"[^\w]+", "_", value, flags=re.UNICODE)
    return re.sub(r"_+", "_", value).strip("_")


# Matching is intentionally conservative: aliases should identify a variable,
# not merely a vague word such as "pressure" or "rate".
VARIABLES: dict[str, dict[str, Any]] = {
    "production": {
        "date": ["date", "datetime", "timestamp", "production_date", "التاريخ"],
        "oil_rate": ["oil_rate", "oil_rate_bopd", "oil_production", "oil_production_bopd", "qo", "wopr", "bopd", "إنتاج_النفط"],
        "water_rate": ["water_rate", "water_rate_bpd", "water_production_rate", "qw", "wwpr", "إنتاج_المياه"],
        "gas_rate": ["gas_rate", "gas_rate_mscf", "gas_production_rate", "qg", "wgpr", "إنتاج_الغاز"],
        "water_cut": ["water_cut", "water_cut_pct", "watercut", "wc", "bsw", "نسبة_المياه"],
        "well": ["well", "well_id", "well_name", "well_no", "uwi", "البئر"],
        "field": ["field", "field_name", "oilfield", "الحقل"],
    },
    "drilling": {
        "depth": ["depth", "measured_depth", "md", "tvd", "hole_depth", "العمق"],
        "rop": ["rop", "rate_of_penetration", "drilling_rate", "معدل_الاختراق"],
        "wob": ["wob", "weight_on_bit", "وزن_اللقمة"],
        "torque": ["torque", "rotary_torque", "العزم"],
        "rpm": ["rpm", "rotary_speed", "rotary_rpm", "سرعة_الدوران"],
        "date": ["date", "datetime", "timestamp", "التاريخ"],
        "well": ["well", "well_id", "well_name", "البئر"],
    },
    "drilling_fluids": {
        "mud_weight": ["mud_weight", "mud_density", "mw", "mud_wt", "كثافة_الطين"],
        "viscosity": ["plastic_viscosity", "pv", "viscosity", "اللزوجة"],
        "yield_point": ["yield_point", "yp", "نقطة_الخضوع"],
        "gel_strength": ["gel_strength", "gel_10_sec", "gel_10_min", "قوة_الجل"],
        "ph": ["ph", "mud_ph"],
        "filtration": ["filtration", "fluid_loss", "api_fluid_loss", "فقدان_الراشح"],
        "date": ["date", "datetime", "timestamp", "التاريخ"],
        "well": ["well", "well_id", "well_name", "البئر"],
    },
    "reservoir": {
        "pressure": ["reservoir_pressure", "average_reservoir_pressure", "static_reservoir_pressure", "ضغط_المكمن"],
        "porosity": ["porosity", "poro", "phi", "المسامية"],
        "permeability": ["permeability", "perm", "k_md", "النفاذية"],
        "water_saturation": ["water_saturation", "sw", "تشبع_المياه"],
        "net_pay": ["net_pay", "net_pay_thickness", "pay_thickness", "سمك_الطبقة_المنتجة"],
        "temperature": ["reservoir_temperature", "res_temperature", "حرارة_المكمن"],
        "well": ["well", "well_id", "well_name", "البئر"],
    },
    "well_testing": {
        "flow_rate": ["test_rate", "flow_rate", "stabilized_rate", "q_test", "معدل_الجريان"],
        "pressure": ["flowing_pressure", "shut_in_pressure", "bottomhole_pressure", "bhp", "ضغط_قاع_البئر"],
        "time": ["elapsed_time", "shut_in_time", "test_time", "الزمن"],
        "date": ["date", "test_date", "datetime", "التاريخ"],
        "well": ["well", "well_id", "well_name", "البئر"],
    },
    "well_logs": {
        "depth": ["depth", "measured_depth", "md", "tvd", "العمق"],
        "gamma_ray": ["gamma_ray", "gr", "gamma", "أشعة_غاما"],
        "resistivity": ["resistivity", "rt", "ild", "res", "المقاومية"],
        "density": ["density", "rhob", "bulk_density", "الكثافة"],
        "neutron_porosity": ["neutron_porosity", "nphi", "neutron", "المسامية_النيوترونية"],
        "sonic": ["sonic", "dt", "acoustic", "زمن_العبور"],
    },
}

UNIT_HINTS = {
    "bopd": ["bopd", "bbl/day", "stb/day", "bbl/d"],
    "bpd": ["bpd", "bbl/day", "bbl/d"],
    "mscf/d": ["mscf/d", "mscfpd"],
    "psi": ["psi"],
    "kpa": ["kpa"],
    "ft": ["ft", "feet"],
    "m": ["meter", "meters", "_m"],
    "md": ["md", "millidarcy"],
    "cp": ["cp", "centipoise"],
    "g/cc": ["g/cc", "g/cm3", "sg"],
    "%": ["pct", "percent", "percentage", "%"],
    "api": ["api"],
}


def detect_columns(df: pd.DataFrame) -> dict[str, dict[str, str]]:
    """Return domain -> canonical variable -> original column name."""
    normalized = {col: normalize_name(col) for col in df.columns}
    found: dict[str, dict[str, str]] = {}
    for domain, variables in VARIABLES.items():
        matches: dict[str, str] = {}
        for variable, aliases in variables.items():
            alias_set = {normalize_name(alias) for alias in aliases}
            # Permit a unit suffix in headers, e.g. "mud_weight_g_cc".
            cols = [
                original for original, norm in normalized.items()
                if any(norm == alias or norm.startswith(alias + "_") for alias in alias_set)
            ]
            if len(cols) == 1:
                matches[variable] = str(cols[0])
        if matches:
            found[domain] = matches
    return found


def classify_dataset(df: pd.DataFrame) -> dict[str, Any]:
    """Suggest the most likely petroleum data domain from recognized columns."""
    detected = detect_columns(df)
    weights = {
        "production": {"oil_rate": 4, "water_rate": 2, "gas_rate": 2, "water_cut": 2},
        "drilling": {"rop": 3, "wob": 3, "torque": 2, "rpm": 2, "depth": 1},
        "drilling_fluids": {"mud_weight": 4, "viscosity": 3, "yield_point": 3, "gel_strength": 2, "filtration": 2},
        "reservoir": {"porosity": 3, "permeability": 3, "water_saturation": 3, "net_pay": 2, "temperature": 1},
        "well_testing": {"flow_rate": 3, "pressure": 2, "time": 2},
        "well_logs": {"gamma_ray": 4, "resistivity": 4, "density": 3, "neutron_porosity": 3, "sonic": 2, "depth": 1},
    }
    scores = {domain: sum(weights[domain].get(var, 0) for var in cols) for domain, cols in detected.items()}
    scores = {domain: scores.get(domain, 0) for domain in VARIABLES}
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_domain, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0
    confidence = "low" if best_score < 3 else ("medium" if best_score < 6 or best_score == second_score else "high")
    return {
        "suggested_domain": best_domain if best_score else "unknown",
        "confidence": confidence if best_score else "low",
        "scores": scores,
        "detected_columns": detected.get(best_domain, {}) if best_score else {},
        "all_detected_columns": detected,
    }


def detect_units(df: pd.DataFrame) -> dict[str, str | None]:
    """Suggest units from column labels only; never convert values automatically."""
    result: dict[str, str | None] = {}
    for column in df.columns:
        label = normalize_name(column)
        unit = None
        for candidate, hints in UNIT_HINTS.items():
            if any(normalize_name(hint) in label for hint in hints):
                unit = candidate
                break
        result[str(column)] = unit
    return result


def profile_data(df: pd.DataFrame) -> dict[str, Any]:
    """Build a non-destructive data-quality profile for a DataFrame."""
    rows = []
    for col in df.columns:
        series = df[col]
        numeric = pd.to_numeric(series, errors="coerce")
        numeric_count = int(numeric.notna().sum())
        outliers = 0
        if numeric_count >= 4:
            q1, q3 = numeric.quantile([0.25, 0.75])
            iqr = q3 - q1
            if pd.notna(iqr) and iqr > 0:
                outliers = int(((numeric < q1 - 1.5 * iqr) | (numeric > q3 + 1.5 * iqr)).sum())
        rows.append({
            "column": str(col),
            "dtype": str(series.dtype),
            "missing": int(series.isna().sum()),
            "missing_pct": round(float(series.isna().mean() * 100), 2) if len(df) else 0.0,
            "unique": int(series.nunique(dropna=True)),
            "numeric_values": numeric_count,
            "possible_outliers_iqr": outliers,
            "unit_hint": detect_units(df)[str(col)],
        })
    return {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "duplicate_rows": int(df.duplicated().sum()),
        "columns": pd.DataFrame(rows),
    }
