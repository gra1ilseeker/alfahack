from sqlalchemy.orm import Session
from app.models import Metric, DashboardSnapshot


def compute_dashboard(db: Session, profile_id: int) -> dict:
    metrics = db.query(Metric).filter(Metric.profile_id == profile_id).all()
    revenue = sum(m.revenue for m in metrics)
    expenses = sum(m.expenses for m in metrics)
    cash_flow = sum(m.cash_flow for m in metrics)
    margin = (revenue - expenses) / revenue if revenue else 0
    stability_index = cash_flow + margin
    summary = {
        "revenue": revenue,
        "expenses": expenses,
        "cash_flow": cash_flow,
        "margin": margin,
    }
    snapshot = DashboardSnapshot(profile_id=profile_id, snapshot_json=summary)
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return {"summary": summary, "stability_index": stability_index}
