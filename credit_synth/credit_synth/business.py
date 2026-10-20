"""Deterministic fictional credit rules and relational materialization."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
import math
import numpy as np
import pandas as pd
from .schema import PRODUCTS, PRODUCT_MAP, project_profiles


def annuity(amount: float, annual_rate: float, months: int) -> float:
    if months <= 0 or amount < 0 or annual_rate < 0:
        raise ValueError("Invalid loan parameters")
    r = annual_rate / 12
    return amount / months if r == 0 else amount * r / (-math.expm1(-months * math.log1p(r)))


def credit_decision(p: dict, amount: float, term: int, rate: float, complete: bool) -> dict:
    cashflow = p["monthly_revenue"] * p["margin"]
    existing_payment = p["monthly_revenue"] * p["debt_to_revenue"] / 24
    payment = annuity(amount, rate, term)
    dscr = cashflow / max(existing_payment + payment, .01)
    # This is an illustrative score, NOT a calibrated PD and NOT bank policy.
    score = float(np.clip(15 + 7 * p["debt_to_revenue"] + .45 * p["overdue_days"]
                          + 35 * p["revenue_volatility"] - 35 * p["margin"]
                          - 2 * p["liquidity_months"], 0, 100))
    result = {"outcome": "REJECTED", "reason_code": "INSUFFICIENT_CASHFLOW",
              "risk_score_demo": round(score, 4), "dscr": round(dscr, 6),
              "offered_amount": None, "annual_rate": rate, "term_months": term}
    if not complete:
        result.update(outcome="NEEDS_INFO", reason_code="MISSING_DOCUMENTS", risk_score_demo=None, dscr=None)
    elif p["overdue_days"] >= 60:
        result["reason_code"] = "SEVERE_OVERDUE"
    elif p["company_age_months"] < 6:
        result["reason_code"] = "INSUFFICIENT_HISTORY"
    elif p["margin"] < .06 or dscr < .75:
        pass
    elif dscr >= 1.25 and p["overdue_days"] <= 10:
        result.update(outcome="APPROVED", reason_code="STANDARD_DEMO_RULES", offered_amount=amount)
    else:
        capacity = max(0., cashflow / 1.25 - existing_payment)
        offer = math.floor(min(capacity / annuity(1., rate, term), .85 * amount) / 1000) * 1000.
        if offer >= PRODUCT_MAP[p["product_id"]]["min_amount"]:
            result.update(outcome="COUNTER_OFFER", reason_code="REDUCED_LIMIT", offered_amount=offer)
    return result


def fixture_profiles() -> pd.DataFrame:
    base = {"scenario": "healthy", "sector": "services", "region": "central", "legal_form": "LLC",
            "product_id": "working_capital", "term_months": 24, "company_age_months": 48,
            "headcount": 12, "monthly_revenue": 2_000_000., "margin": .25, "debt_to_revenue": .4,
            "liquidity_months": 4., "revenue_volatility": .06, "overdue_days": 0,
            "requested_to_revenue": 1., "collateral_coverage": .8}
    rows = []
    for case in ["approved", "rejected", "needs_info", "counter_offer", "issued"]:
        p = dict(base, company_id=f"F_{case.upper()}", fixture_case=case, is_fixture=True)
        if case == "rejected":
            p.update(scenario="distressed", overdue_days=90, margin=.05, debt_to_revenue=4.)
        if case == "counter_offer":
            p.update(scenario="borderline", monthly_revenue=1_000_000., margin=.14,
                     debt_to_revenue=1., requested_to_revenue=2., overdue_days=14)
        rows.append(p)
    return project_profiles(pd.DataFrame(rows))[0]


def _records(rows, columns):
    return pd.DataFrame(rows, columns=columns)


def materialize(profiles: pd.DataFrame, seed: int, as_of: str) -> tuple[dict, list]:
    rng = np.random.default_rng(seed)
    reference_date = date.fromisoformat(as_of)
    start = datetime.combine(reference_date, datetime.min.time(), tzinfo=timezone.utc).replace(hour=9)
    months = pd.date_range(end=pd.Timestamp(reference_date.replace(day=1)) - pd.offsets.MonthBegin(1),
                           periods=12, freq="MS")
    rows = {k: [] for k in ["companies", "clients", "memberships", "financials_monthly", "applications",
                            "documents", "external_checks", "decisions", "application_events", "loans"]}
    fixtures = []
    employees = [{"employee_id": f"E{i:03d}", "display_name": f"Demo employee {i}",
                  "role": ["manager", "underwriter", "operator"][i % 3]} for i in range(6)]
    for i, p in enumerate(profiles.to_dict("records")):
        cid, uid, aid = p["company_id"], f"U{i:07d}", f"A{i:07d}"
        fixture_case = p.get("fixture_case", "")
        is_fixture = bool(p.get("is_fixture", False))
        rows["companies"].append({"company_id": cid, "legal_name": f"Синтетическая компания {i:07d}",
                                  "tax_id": f"SYNTHETIC-TAX-{i:07d}", "legal_form": p["legal_form"],
                                  "sector": p["sector"], "region": p["region"],
                                  "company_age_months": p["company_age_months"], "headcount": p["headcount"],
                                  "is_synthetic": True, "is_fixture": is_fixture})
        rows["clients"].append({"client_id": uid, "display_name": f"Тестовый владелец {i:07d}",
                                "is_synthetic": True})
        rows["memberships"].append({"membership_id": f"M{i:07d}", "company_id": cid,
                                    "client_id": uid, "role": "owner", "ownership_percent": 100.})
        # Normalize noise so twelve-month mean revenue matches the generated snapshot.
        seasonal = 1 + .08 * np.sin(np.arange(12) * 2 * np.pi / 12 + rng.uniform(0, 2 * np.pi))
        factors = seasonal * rng.lognormal(0, p["revenue_volatility"], 12)
        revenue = np.round(p["monthly_revenue"] * factors / factors.mean(), 2)
        margins = np.clip(p["margin"] + rng.normal(0, .01, 12), .01, .49)
        margins[-1] = p["margin"]  # snapshot cashflow is the reference, not a later observation
        for j, month in enumerate(months):
            expense = round(revenue[j] * (1 - margins[j]), 2)
            rows["financials_monthly"].append({
                "financial_id": f"FIN{i:07d}_{j:02d}", "company_id": cid, "month": month.date().isoformat(),
                "revenue": float(revenue[j]), "expenses": expense, "profit": round(revenue[j] - expense, 2),
                "debt_balance": round(p["monthly_revenue"] * p["debt_to_revenue"], 2),
                "cash_balance": round(p["monthly_revenue"] * p["margin"] * p["liquidity_months"], 2),
                "monthly_debt_payment": round(p["monthly_revenue"] * p["debt_to_revenue"] / 24, 2)})
        product = PRODUCT_MAP[p["product_id"]]
        amount = float(round(np.clip(p["monthly_revenue"] * p["requested_to_revenue"],
                                     product["min_amount"], product["max_amount"]), 2))
        complete = fixture_case != "needs_info" if is_fixture else bool(rng.random() > .12)
        decision = credit_decision(p, amount, int(p["term_months"]), product["annual_rate"], complete)
        path = ["DRAFT", "SUBMITTED", "VALIDATING"]
        if decision["outcome"] == "NEEDS_INFO":
            path.append("NEEDS_INFO")
        else:
            path.extend(["ENRICHING", "SCORING", decision["outcome"]])
        issued = (fixture_case == "issued" if is_fixture else bool(rng.random() < .35))
        if decision["outcome"] == "APPROVED" and issued:
            path.extend(["SIGNING", "ISSUED"])
        assigned = employees[i % len(employees)]["employee_id"]
        rows["applications"].append({
            "application_id": aid, "company_id": cid, "client_id": uid, "product_id": p["product_id"],
            "employee_id": assigned, "requested_amount": amount, "term_months": int(p["term_months"]),
            "purpose": product["purpose"], "status": path[-1], "documents_complete": complete,
            "created_at": start.isoformat(), "submitted_at": (start + timedelta(minutes=5)).isoformat()})
        decision_time = (start + timedelta(minutes=5 * (len(path) - 1 - (2 if path[-1] == "ISSUED" else 0))))
        rows["decisions"].append({"decision_id": f"DEC{i:07d}", "application_id": aid, **decision,
                                   "decided_at": decision_time.isoformat(), "policy_version": "fictional_demo_v1"})
        for j, kind in enumerate(["registration", "financial_statement", "bank_statement"]):
            present = complete or j != 2
            rows["documents"].append({
                "document_id": f"DOC{i:07d}_{j}", "application_id": aid, "company_id": cid,
                "document_type": kind, "status": "accepted" if present else "missing",
                "content_text": (f"СИНТЕТИЧЕСКИЙ ДОКУМЕНТ; {kind}; company={cid}; "
                                 f"as_of={as_of}; generated for local demo") if present else None,
                "uploaded_at": (start - timedelta(days=1)).isoformat() if present else None})
        if complete:
            for j, provider in enumerate(["FNS_MOCK", "BKI_MOCK"]):
                payload = {"registered": True} if j == 0 else {"overdue_days": int(p["overdue_days"]),
                    "existing_debt": round(p["monthly_revenue"] * p["debt_to_revenue"], 2)}
                rows["external_checks"].append({"check_id": f"CHK{i:07d}_{j}", "application_id": aid,
                                                 "provider": provider, "status": "completed_mock",
                                                 "payload_json": json.dumps(payload, sort_keys=True),
                                                 "checked_at": (start + timedelta(minutes=15)).isoformat()})
        for j, state in enumerate(path):
            rows["application_events"].append({"event_id": f"EV{i:07d}_{j}", "application_id": aid,
                                               "sequence": j, "from_status": path[j - 1] if j else None,
                                               "to_status": state,
                                               "occurred_at": (start + timedelta(minutes=5 * j)).isoformat()})
        if path[-1] == "ISSUED":
            rows["loans"].append({"loan_id": f"L{i:07d}", "application_id": aid,
                                   "disbursed_amount": decision["offered_amount"],
                                   "annual_rate": product["annual_rate"], "term_months": int(p["term_months"]),
                                   "monthly_payment": round(annuity(decision["offered_amount"],
                                                                      product["annual_rate"], int(p["term_months"])), 2),
                                   "issued_at": (start + timedelta(minutes=5 * (len(path) - 1))).isoformat(),
                                   "is_mock": True})
        if is_fixture:
            fixtures.append({"case": fixture_case, "company_id": cid, "client_id": uid,
                             "application_id": aid, "expected_status": fixture_case.upper(),
                             "actual_status": path[-1]})
    tables = {k: pd.DataFrame(v) for k, v in rows.items()}
    # Give empty optional tables a schema too.
    tables["loans"] = _records(rows["loans"], ["loan_id", "application_id", "disbursed_amount", "annual_rate",
                                               "term_months", "monthly_payment", "issued_at", "is_mock"])
    tables["external_checks"] = _records(rows["external_checks"], ["check_id", "application_id", "provider",
                                                                   "status", "payload_json", "checked_at"])
    tables["employees"] = pd.DataFrame(employees)
    tables["products"] = pd.DataFrame(PRODUCTS)
    tables["profiles"] = profiles.copy()
    return tables, fixtures
