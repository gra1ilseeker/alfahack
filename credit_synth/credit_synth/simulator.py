"""An explicit fictional source distribution, used only when no dataset exists."""
from pathlib import Path
import numpy as np
import pandas as pd

from .schema import CATEGORIES, SCENARIOS, DEFAULT_MIX, project_profiles, validate_profiles
from .utils import sample_pairs, weighted_pairs, write_json


def bootstrap_profiles(n: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    scenario = rng.choice(3, size=n, p=DEFAULT_MIX)
    sector = rng.choice(CATEGORIES["sector"], n, p=[0.30, 0.25, 0.18, 0.15, 0.12])
    sector_scale = np.array([{"retail": 1.0, "services": 0.8, "manufacturing": 1.8,
                              "logistics": 1.3, "it": 0.9}[s] for s in sector])
    revenue = rng.lognormal(np.log(1_500_000), 0.65, n) * sector_scale
    product = rng.choice(CATEGORIES["product_id"], n, p=[0.55, 0.30, 0.15])
    df = pd.DataFrame({
        "company_id": [f"B{i:07d}" for i in range(n)],
        "scenario": np.asarray(SCENARIOS)[scenario], "sector": sector,
        "region": rng.choice(CATEGORIES["region"], n, p=[.32, .15, .18, .13, .12, .10]),
        "legal_form": rng.choice(CATEGORIES["legal_form"], n, p=[.70, .30]),
        "product_id": product, "term_months": rng.choice([6, 12, 24, 36, 60], n),
        "company_age_months": rng.lognormal(np.array([4.0, 3.5, 3.1])[scenario], .5),
        "headcount": revenue / 200_000 * rng.lognormal(0, .25, n),
        "monthly_revenue": revenue,
        "margin": rng.normal(np.array([.25, .14, .065])[scenario], .035),
        "debt_to_revenue": rng.gamma(3, np.array([.25, .65, 1.1])[scenario]),
        "liquidity_months": rng.gamma(3, np.array([1.3, .55, .15])[scenario]),
        "revenue_volatility": rng.normal(np.array([.08, .17, .29])[scenario], .035),
        "overdue_days": np.where(scenario == 0, rng.poisson(.4, n),
                                 np.where(scenario == 1, rng.poisson(14, n), rng.poisson(80, n))),
        "requested_to_revenue": rng.lognormal(np.array([.2, .7, 1.0])[scenario], .45),
        "collateral_coverage": rng.beta(2, 3, n) * 2,
    })
    df, _ = project_profiles(df)
    validate_profiles(df)
    return df


def bootstrap_graph(df: pd.DataFrame, seed: int = 42, degree: float = 6) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = len(df)
    candidates = sample_pairs(n, min(n * 32, n * (n - 1) // 2), rng)
    a, b = candidates.T
    scores = (1.8 * (df.sector.to_numpy()[a] == df.sector.to_numpy()[b])
              + 1.2 * (df.region.to_numpy()[a] == df.region.to_numpy()[b])
              - .5 * np.abs(np.log(df.monthly_revenue.to_numpy()[a] /
                                  df.monthly_revenue.to_numpy()[b])))
    edges = weighted_pairs(candidates, scores, round(n * degree / 2), rng)
    return pd.DataFrame({"source_company_id": df.company_id.to_numpy()[edges[:, 0]],
                         "target_company_id": df.company_id.to_numpy()[edges[:, 1]]})


def bootstrap(out: Path, rows: int, seed: int) -> None:
    if rows < 100:
        raise ValueError("Use at least 100 bootstrap companies")
    out.mkdir(parents=True, exist_ok=True)
    df = bootstrap_profiles(rows, seed)
    df.to_csv(out / "profiles.csv", index=False)
    bootstrap_graph(df, seed + 1).to_csv(out / "company_links.csv", index=False)
    write_json(out / "source_manifest.json", {
        "source": "fictional_rule_simulator", "seed": seed, "rows": rows,
        "contains_real_bank_data": False,
        "warning": "Learning this source learns the simulator, not a real bank distribution.",
    })
