PRAGMA foreign_keys = ON;

CREATE TABLE "companies" ("company_id" TEXT PRIMARY KEY, "legal_name" TEXT, "tax_id" TEXT, "legal_form" TEXT, "sector" TEXT, "region" TEXT, "company_age_months" INTEGER, "headcount" INTEGER, "is_synthetic" INTEGER, "is_fixture" INTEGER);

CREATE TABLE "clients" ("client_id" TEXT PRIMARY KEY, "display_name" TEXT, "is_synthetic" INTEGER);

CREATE TABLE "employees" ("employee_id" TEXT PRIMARY KEY, "display_name" TEXT, "role" TEXT);

CREATE TABLE "products" ("product_id" TEXT PRIMARY KEY, "name" TEXT, "min_amount" REAL, "max_amount" REAL, "annual_rate" REAL, "allowed_terms" TEXT, "purpose" TEXT);

CREATE TABLE "memberships" ("membership_id" TEXT PRIMARY KEY, "company_id" TEXT, "client_id" TEXT, "role" TEXT, "ownership_percent" REAL, FOREIGN KEY ("company_id") REFERENCES "companies" ("company_id"), FOREIGN KEY ("client_id") REFERENCES "clients" ("client_id"));

CREATE TABLE "profiles" ("company_age_months" INTEGER, "headcount" INTEGER, "monthly_revenue" REAL, "margin" REAL, "debt_to_revenue" REAL, "liquidity_months" REAL, "revenue_volatility" REAL, "overdue_days" INTEGER, "requested_to_revenue" REAL, "collateral_coverage" REAL, "sector" TEXT, "region" TEXT, "legal_form" TEXT, "product_id" TEXT, "term_months" INTEGER, "scenario" TEXT, "company_id" TEXT PRIMARY KEY, "is_fixture" INTEGER, "fixture_case" TEXT, FOREIGN KEY ("company_id") REFERENCES "companies" ("company_id"));

CREATE TABLE "financials_monthly" ("financial_id" TEXT PRIMARY KEY, "company_id" TEXT, "month" TEXT, "revenue" REAL, "expenses" REAL, "profit" REAL, "debt_balance" REAL, "cash_balance" REAL, "monthly_debt_payment" REAL, FOREIGN KEY ("company_id") REFERENCES "companies" ("company_id"));

CREATE TABLE "applications" ("application_id" TEXT PRIMARY KEY, "company_id" TEXT, "client_id" TEXT, "product_id" TEXT, "employee_id" TEXT, "requested_amount" REAL, "term_months" INTEGER, "purpose" TEXT, "status" TEXT, "documents_complete" INTEGER, "created_at" TEXT, "submitted_at" TEXT, FOREIGN KEY ("company_id") REFERENCES "companies" ("company_id"), FOREIGN KEY ("client_id") REFERENCES "clients" ("client_id"), FOREIGN KEY ("product_id") REFERENCES "products" ("product_id"), FOREIGN KEY ("employee_id") REFERENCES "employees" ("employee_id"));

CREATE TABLE "documents" ("document_id" TEXT PRIMARY KEY, "application_id" TEXT, "company_id" TEXT, "document_type" TEXT, "status" TEXT, "content_text" TEXT, "uploaded_at" TEXT, FOREIGN KEY ("application_id") REFERENCES "applications" ("application_id"), FOREIGN KEY ("company_id") REFERENCES "companies" ("company_id"));

CREATE TABLE "external_checks" ("check_id" TEXT PRIMARY KEY, "application_id" TEXT, "provider" TEXT, "status" TEXT, "payload_json" TEXT, "checked_at" TEXT, FOREIGN KEY ("application_id") REFERENCES "applications" ("application_id"));

CREATE TABLE "decisions" ("decision_id" TEXT PRIMARY KEY, "application_id" TEXT, "outcome" TEXT, "reason_code" TEXT, "risk_score_demo" REAL, "dscr" REAL, "offered_amount" REAL, "annual_rate" REAL, "term_months" INTEGER, "decided_at" TEXT, "policy_version" TEXT, FOREIGN KEY ("application_id") REFERENCES "applications" ("application_id"));

CREATE TABLE "application_events" ("event_id" TEXT PRIMARY KEY, "application_id" TEXT, "sequence" INTEGER, "from_status" TEXT, "to_status" TEXT, "occurred_at" TEXT, FOREIGN KEY ("application_id") REFERENCES "applications" ("application_id"));

CREATE TABLE "loans" ("loan_id" TEXT PRIMARY KEY, "application_id" TEXT, "disbursed_amount" REAL, "annual_rate" REAL, "term_months" INTEGER, "monthly_payment" REAL, "issued_at" TEXT, "is_mock" INTEGER, FOREIGN KEY ("application_id") REFERENCES "applications" ("application_id"));

CREATE TABLE "company_links" ("link_id" TEXT PRIMARY KEY, "source_company_id" TEXT, "target_company_id" TEXT, "relation" TEXT, "decoder_score" REAL, FOREIGN KEY ("source_company_id") REFERENCES "companies" ("company_id"), FOREIGN KEY ("target_company_id") REFERENCES "companies" ("company_id"));
