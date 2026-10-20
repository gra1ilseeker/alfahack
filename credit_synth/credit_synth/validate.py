from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd

from .business import annuity, credit_decision
from .export import PRIMARY_KEYS, FOREIGN_KEYS
from .schema import PRODUCT_MAP, TRANSITIONS, validate_profiles
from .utils import write_json


def load_tables(path: Path) -> dict:
    return {name: pd.read_csv(path / f"{name}.csv") for name in PRIMARY_KEYS}


def validate_tables(tables: dict, fixtures: list, as_of: str) -> dict:
    passed = 0

    def require(condition, message):
        nonlocal passed
        if not bool(condition):
            raise ValueError(f"Dataset validation failed: {message}")
        passed += 1

    validate_profiles(tables["profiles"])
    for table, key in PRIMARY_KEYS.items():
        frame = tables[table]
        require(key in frame and not frame[key].isna().any() and not frame[key].duplicated().any(),
                f"{table}: invalid primary key")
        for col, (parent, parent_key) in FOREIGN_KEYS.get(table, {}).items():
            require(frame[col].isin(tables[parent][parent_key]).all(), f"{table}.{col}: dangling FK")
    apps, decisions = tables["applications"], tables["decisions"]
    profiles = tables["profiles"].set_index("company_id")
    require(set(apps.status) <= set(TRANSITIONS), "unknown application state")
    require(not decisions.application_id.duplicated().any() and
            set(decisions.application_id) == set(apps.application_id), "one decision record per application")
    require(not tables["loans"].application_id.duplicated().any(), "duplicate disbursement")
    require(not tables["financials_monthly"].duplicated(["company_id", "month"]).any(), "duplicate month")
    require(not tables["memberships"].duplicated(["company_id", "client_id"]).any(), "duplicate membership")
    events_by_app = {a: group.sort_values("sequence")
                     for a, group in tables["application_events"].groupby("application_id")}
    doc_groups = {a: group for a, group in tables["documents"].groupby("application_id")}
    decision_map = decisions.set_index("application_id")
    memberships = set(zip(tables["memberships"].company_id, tables["memberships"].client_id))
    for a in apps.itertuples():
        require((a.company_id, a.client_id) in memberships, "applicant is not a company member")
        product = PRODUCT_MAP[a.product_id]
        require(product["min_amount"] <= a.requested_amount <= product["max_amount"], "product amount bounds")
        require(str(a.term_months) in product["allowed_terms"].split(","), "product term bounds")
        require(a.application_id in events_by_app and a.application_id in doc_groups, "missing events/documents")
        ev = events_by_app[a.application_id]
        states = ev.to_status.tolist()
        require(states[0] == "DRAFT" and states[-1] == a.status, "history endpoints")
        require(ev.sequence.tolist() == list(range(len(ev))), "history sequence")
        require(pd.to_datetime(ev.occurred_at).is_monotonic_increasing, "event chronology")
        require(all(new in TRANSITIONS[old] for old, new in zip(states, states[1:])), "illegal transition")
        require(pd.isna(ev.iloc[0].from_status) and ev.from_status.iloc[1:].tolist() == states[:-1],
                "event from_status disagrees with previous state")
        require(pd.to_datetime(ev.occurred_at).max().date() <= pd.Timestamp(as_of).date(), "future event")
        docs = doc_groups[a.application_id]
        require(set(docs.company_id) == {a.company_id}, "document/app company mismatch")
        require(set(docs.document_type) == {"registration", "financial_statement", "bank_statement"}, "document types")
        complete = bool(docs.status.eq("accepted").all())
        require(complete == bool(a.documents_complete), "document completeness mismatch")
        require(docs.loc[docs.status.eq("accepted"), "content_text"].notna().all(), "missing accepted document body")
        p = profiles.loc[a.company_id].to_dict()
        expected = credit_decision(p, a.requested_amount, a.term_months, product["annual_rate"], complete)
        decision = decision_map.loc[a.application_id]
        require(expected["outcome"] == decision.outcome and expected["reason_code"] == decision.reason_code,
                "decision disagrees with explicit demo rules")
        require((a.status == decision.outcome) or (a.status == "ISSUED" and decision.outcome == "APPROVED"),
                "status/decision mismatch")
        if expected["dscr"] is not None:
            require(abs(expected["dscr"] - decision.dscr) < 1e-5, "incorrect DSCR")
        if pd.notna(decision.offered_amount):
            require(product["min_amount"] <= decision.offered_amount <= a.requested_amount, "offer bounds")
        if decision.outcome == "COUNTER_OFFER":
            require(decision.offered_amount < a.requested_amount, "counter offer must reduce amount")
    financials = tables["financials_monthly"]
    require(np.isfinite(financials[["revenue", "expenses", "profit", "debt_balance", "cash_balance"]]).all().all(),
            "non-finite financial values")
    require((financials[["revenue", "expenses", "debt_balance", "cash_balance"]] >= 0).all().all(),
            "negative financial amounts")
    require(np.allclose(financials.revenue - financials.expenses, financials.profit, atol=.011), "accounting identity")
    require((financials.groupby("company_id").size() == 12).all(), "need twelve monthly observations")
    require((pd.to_datetime(financials.month) < pd.Timestamp(as_of).replace(day=1)).all(), "future financial observation")
    means = financials.groupby("company_id").revenue.mean()
    require(np.allclose(means, profiles.loc[means.index].monthly_revenue, rtol=0, atol=.011), "snapshot revenue mismatch")
    require(set(tables["loans"].application_id) == set(apps.loc[apps.status.eq("ISSUED"), "application_id"]),
            "loans must exist exactly for issued applications")
    for loan in tables["loans"].itertuples():
        d = decision_map.loc[loan.application_id]
        require(abs(loan.disbursed_amount - d.offered_amount) < .01, "disbursement/offer mismatch")
        require(abs(loan.monthly_payment - annuity(loan.disbursed_amount, loan.annual_rate, loan.term_months)) < .011,
                "incorrect annuity")
    edges = tables["company_links"]
    require((edges.source_company_id != edges.target_company_id).all(), "graph self loop")
    pair_keys = [tuple(sorted(p)) for p in zip(edges.source_company_id, edges.target_company_id)]
    require(len(set(pair_keys)) == len(pair_keys), "duplicate undirected edge")
    for fixture in fixtures:
        actual = apps.set_index("application_id").loc[fixture["application_id"], "status"]
        require(actual == fixture["expected_status"], f"fixture {fixture['case']} failed")
    return {"valid": True, "checks_passed": passed,
            "rows": {name: len(frame) for name, frame in tables.items()},
            "application_statuses": {str(k): int(v) for k, v in apps.status.value_counts().items()},
            "fixture_cases": [f["case"] for f in fixtures]}


def validate_dataset(path: Path) -> dict:
    metadata = json.loads((path / "metadata.json").read_text())
    report = validate_tables(load_tables(path), json.loads((path / "fixtures.json").read_text()), metadata["as_of"])
    with sqlite3.connect(path / "dataset.sqlite") as conn:
        if conn.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("SQLite FK violations")
    report["sqlite_foreign_keys_valid"] = True
    write_json(path / "validation.json", report)
    return report
