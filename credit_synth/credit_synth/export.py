"""CSV + JSON + a SQLite database with enforced foreign keys."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
import pandas as pd
from .utils import write_json


PRIMARY_KEYS = {
    "companies": "company_id", "clients": "client_id", "employees": "employee_id", "products": "product_id",
    "memberships": "membership_id", "profiles": "company_id", "financials_monthly": "financial_id",
    "applications": "application_id", "documents": "document_id", "external_checks": "check_id",
    "decisions": "decision_id", "application_events": "event_id", "loans": "loan_id", "company_links": "link_id",
}
FOREIGN_KEYS = {
    "memberships": {"company_id": ("companies", "company_id"), "client_id": ("clients", "client_id")},
    "profiles": {"company_id": ("companies", "company_id")},
    "financials_monthly": {"company_id": ("companies", "company_id")},
    "applications": {"company_id": ("companies", "company_id"), "client_id": ("clients", "client_id"),
                     "product_id": ("products", "product_id"), "employee_id": ("employees", "employee_id")},
    "documents": {"application_id": ("applications", "application_id"), "company_id": ("companies", "company_id")},
    "external_checks": {"application_id": ("applications", "application_id")},
    "decisions": {"application_id": ("applications", "application_id")},
    "application_events": {"application_id": ("applications", "application_id")},
    "loans": {"application_id": ("applications", "application_id")},
    "company_links": {"source_company_id": ("companies", "company_id"),
                      "target_company_id": ("companies", "company_id")},
}


def write_dataset(out: Path, tables: dict, metadata: dict, fixtures: list) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        frame.to_csv(out / f"{name}.csv", index=False)
    serializable = {name: json.loads(frame.to_json(orient="records", force_ascii=False))
                    for name, frame in tables.items()}
    write_json(out / "dataset.json", {"metadata": metadata, "tables": serializable})
    write_json(out / "metadata.json", metadata)
    write_json(out / "fixtures.json", fixtures)
    db = out / "dataset.sqlite"
    # Build in a temporary path and replace only a complete, checked database.
    tmp_db = out / "dataset.sqlite.tmp"
    tmp_db.unlink(missing_ok=True)
    with sqlite3.connect(tmp_db) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        schema = []
        for name in PRIMARY_KEYS:
            frame = tables[name]
            columns = []
            for col in frame.columns:
                dtype = frame[col].dtype
                sql_type = "INTEGER" if pd.api.types.is_integer_dtype(dtype) or pd.api.types.is_bool_dtype(dtype) else (
                    "REAL" if pd.api.types.is_float_dtype(dtype) else "TEXT")
                columns.append(f'"{col}" {sql_type}' + (" PRIMARY KEY" if col == PRIMARY_KEYS[name] else ""))
            for col, (parent, parent_key) in FOREIGN_KEYS.get(name, {}).items():
                columns.append(f'FOREIGN KEY ("{col}") REFERENCES "{parent}" ("{parent_key}")')
            statement = f'CREATE TABLE "{name}" ({", ".join(columns)});'
            conn.execute(statement)
            schema.append(statement)
            if len(frame):
                fields = ", ".join(f'"{c}"' for c in frame.columns)
                placeholders = ", ".join("?" for _ in frame.columns)
                # Read values in explicit column order; JSON dictionaries are not an SQL schema.
                values = [tuple(record[c] for c in frame.columns) for record in serializable[name]]
                conn.executemany(f'INSERT INTO "{name}" ({fields}) VALUES ({placeholders})', values)
        if conn.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Foreign key check failed")
    tmp_db.replace(db)
    (out / "schema.sql").write_text("PRAGMA foreign_keys = ON;\n\n" + "\n\n".join(schema) + "\n")
