"""Explicit, configurable demo schema. These are NOT bank policy thresholds."""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


SCENARIOS = ["healthy", "borderline", "distressed"]
DEFAULT_MIX = [0.55, 0.30, 0.15]
CATEGORIES = {
    "sector": ["retail", "services", "manufacturing", "logistics", "it"],
    "region": ["central", "north_west", "volga", "south", "ural", "siberia"],
    "legal_form": ["LLC", "IE"],
    "product_id": ["working_capital", "equipment", "credit_line"],
    "term_months": [6, 12, 24, 36, 60],
}
# name: (lower bound, upper bound, log1p transform, integer)
FEATURES = {
    "company_age_months": (3, 180, True, True),
    "headcount": (1, 100, True, True),
    "monthly_revenue": (150_000, 15_000_000, True, False),
    "margin": (0.02, 0.48, False, False),
    "debt_to_revenue": (0, 6, True, False),
    "liquidity_months": (0, 12, True, False),
    "revenue_volatility": (0.01, 0.5, True, False),
    "overdue_days": (0, 180, True, True),
    "requested_to_revenue": (0.2, 12, True, False),
    "collateral_coverage": (0, 2, True, False),
}
PRODUCTS = [
    {"product_id": "working_capital", "name": "Demo working capital",
     "min_amount": 100_000.0, "max_amount": 15_000_000.0,
     "annual_rate": 0.20, "allowed_terms": "6,12,24,36", "purpose": "working_capital"},
    {"product_id": "equipment", "name": "Demo equipment loan",
     "min_amount": 200_000.0, "max_amount": 30_000_000.0,
     "annual_rate": 0.18, "allowed_terms": "12,24,36,60", "purpose": "equipment"},
    {"product_id": "credit_line", "name": "Demo credit line (installment approximation)",
     "min_amount": 100_000.0, "max_amount": 10_000_000.0,
     "annual_rate": 0.22, "allowed_terms": "6,12,24", "purpose": "cash_gap"},
]
PRODUCT_MAP = {p["product_id"]: p for p in PRODUCTS}
TRANSITIONS = {
    "DRAFT": {"SUBMITTED"}, "SUBMITTED": {"VALIDATING"},
    "VALIDATING": {"NEEDS_INFO", "ENRICHING"}, "ENRICHING": {"SCORING"},
    "SCORING": {"APPROVED", "COUNTER_OFFER", "REJECTED"},
    "APPROVED": {"SIGNING"}, "SIGNING": {"ISSUED"},
    "NEEDS_INFO": {"SUBMITTED"}, "COUNTER_OFFER": {"SIGNING"}, "REJECTED": set(), "ISSUED": set(),
}


def project_profiles(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Project decoder output to physical domains; report every clipped value."""
    df = df.copy()
    report = {}
    for name, (lo, hi, _, integer) in FEATURES.items():
        values = df[name].to_numpy(dtype=float)
        report[name] = int(((values < lo) | (values > hi) | ~np.isfinite(values)).sum())
        values = np.nan_to_num(values, nan=lo, posinf=hi, neginf=lo).clip(lo, hi)
        df[name] = np.rint(values).astype(int) if integer else np.round(values, 6)
    changed = 0
    for i, row in df.iterrows():
        allowed = [int(t) for t in PRODUCT_MAP[row.product_id]["allowed_terms"].split(",")]
        term = min(allowed, key=lambda t: abs(t - int(row.term_months)))
        changed += term != int(row.term_months)
        df.at[i, "term_months"] = term
    df["term_months"] = df["term_months"].astype(int)
    report["product_term_adjustments"] = int(changed)
    return df, report


def validate_profiles(df: pd.DataFrame, minimum_rows: int = 1) -> None:
    required = ["company_id", "scenario", *FEATURES, *CATEGORIES]
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"Missing profile columns: {sorted(missing)}")
    if len(df) < minimum_rows or df[required].isna().any().any():
        raise ValueError(f"Need >= {minimum_rows} complete company snapshots")
    if df.company_id.duplicated().any():
        raise ValueError("One snapshot per company is required: duplicate company_id")
    if not df.scenario.isin(SCENARIOS).all():
        raise ValueError(f"scenario must be one of {SCENARIOS}")
    for name, (lo, hi, _, integer) in FEATURES.items():
        v = df[name].to_numpy(dtype=float)
        if not (np.isfinite(v).all() and ((v >= lo) & (v <= hi)).all()):
            raise ValueError(f"{name} must be finite in [{lo}, {hi}]; edit schema if needed")
        if integer and not np.equal(v, np.rint(v)).all():
            raise ValueError(f"{name} must be integer")
    for name, choices in CATEGORIES.items():
        if not df[name].isin(choices).all():
            raise ValueError(f"Unknown {name}, expected {choices}")
    for row in df.itertuples():
        if str(int(row.term_months)) not in PRODUCT_MAP[row.product_id]["allowed_terms"].split(","):
            raise ValueError(f"Invalid product/term: {row.product_id}/{row.term_months}")


@dataclass
class Codec:
    """Train-only log/standard scaling; fixed categorical vocabularies."""
    mean: np.ndarray
    scale: np.ndarray

    @classmethod
    def fit(cls, df: pd.DataFrame) -> "Codec":
        x = cls.raw_numeric(df)
        return cls(x.mean(0), x.std(0).clip(0.05))

    @staticmethod
    def raw_numeric(df: pd.DataFrame) -> np.ndarray:
        return np.column_stack([
            np.log1p(df[name].to_numpy(float)) if spec[2] else df[name].to_numpy(float)
            for name, spec in FEATURES.items()
        ])

    def encode(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        x = ((self.raw_numeric(df) - self.mean) / self.scale).astype("float32")
        cat = np.column_stack([
            pd.Categorical(df[name], categories=choices).codes
            for name, choices in CATEGORIES.items()
        ]).astype("int64")
        cond = pd.Categorical(df.scenario, categories=SCENARIOS).codes.astype("int64")
        if (cat < 0).any() or (cond < 0).any():
            raise ValueError("Unknown categories; validate the source profiles")
        return x, cat, cond

    def graph_features(self, df: pd.DataFrame) -> np.ndarray:
        x, cats, _ = self.encode(df)
        onehot = [np.eye(len(choices), dtype="float32")[cats[:, i]]
                  for i, choices in enumerate(CATEGORIES.values())]
        return np.concatenate([x, *onehot], axis=1)

    def decode(self, values: np.ndarray, cats: np.ndarray, conditions: np.ndarray):
        raw = values * self.scale + self.mean
        data = {}
        for j, (name, spec) in enumerate(FEATURES.items()):
            # Bounds protect expm1 from overflow; projection still records domain violations.
            data[name] = np.expm1(raw[:, j].clip(-10, 30)) if spec[2] else raw[:, j]
        for j, (name, choices) in enumerate(CATEGORIES.items()):
            data[name] = np.asarray(choices)[cats[:, j]]
        data["scenario"] = np.asarray(SCENARIOS)[conditions]
        data["company_id"] = [f"G{i:07d}" for i in range(len(values))]
        return project_profiles(pd.DataFrame(data))

    def to_dict(self) -> dict:
        return {"mean": self.mean.tolist(), "scale": self.scale.tolist()}

    @classmethod
    def from_dict(cls, value: dict) -> "Codec":
        return cls(np.array(value["mean"]), np.array(value["scale"]))
