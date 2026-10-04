from typing import Dict


def calculate_difference(value_a: float, value_b: float) -> Dict:
    difference = abs(value_a - value_b)

    if difference == 0:
        status = "PASS"
    elif difference >= 20:
        status = "HIGH"
    elif difference >= 5:
        status = "MEDIUM"
    else:
        status = "LOW"

    return {
        "value_a": value_a,
        "value_b": value_b,
        "difference": difference,
        "status": status,
    }


def check_revenue_consistency(
    income_statement_revenue: float,
    revenue_report_total: float,
) -> Dict:

    result = calculate_difference(
        income_statement_revenue,
        revenue_report_total,
    )

    return {
        "check": "Revenue Consistency",
        "category": "Revenue",
        **result,
    }


def check_income_statement(
    revenue: float,
    cogs: float,
    gross_profit: float,
    operating_expenses: float,
    operating_profit: float,
    finance_cost: float,
    pbt: float,
    tax: float,
    pat: float,
):
    checks = []

    checks.append({
        "check": "Gross Profit",
        "expected": revenue - cogs,
        "actual": gross_profit,
        "status": "PASS" if revenue - cogs == gross_profit else "REVIEW_REQUIRED"
    })

    checks.append({
        "check": "Operating Profit",
        "expected": gross_profit - operating_expenses,
        "actual": operating_profit,
        "status": "PASS"
        if gross_profit - operating_expenses == operating_profit
        else "REVIEW_REQUIRED"
    })

    checks.append({
        "check": "Profit Before Tax",
        "expected": operating_profit - finance_cost,
        "actual": pbt,
        "status": "PASS"
        if operating_profit - finance_cost == pbt
        else "REVIEW_REQUIRED"
    })

    checks.append({
        "check": "Profit After Tax",
        "expected": pbt - tax,
        "actual": pat,
        "status": "PASS"
        if pbt - tax == pat
        else "REVIEW_REQUIRED"
    })

    return checks


def check_balance_sheet(
    total_assets: float,
    total_liabilities_equity: float,
):
    return {
        "check": "Balance Sheet Equation",
        "expected": total_assets,
        "actual": total_liabilities_equity,
        "status": "PASS"
        if total_assets == total_liabilities_equity
        else "REVIEW_REQUIRED",
    }


def check_cash_flow(
    opening_cash: float,
    net_change: float,
    closing_cash: float,
):
    expected = opening_cash + net_change

    return {
        "check": "Cash Flow Closing Cash",
        "expected": expected,
        "actual": closing_cash,
        "status": "PASS"
        if expected == closing_cash
        else "REVIEW_REQUIRED",
    }


# ---------------------------------------------------------------
# Objective reconciliation checks (arithmetic / cross-document)
# ---------------------------------------------------------------

TOLERANCE = 0.01


def _have(*values):
    return all(v is not None for v in values)


def reconciliation_checks(x):
    """Return a list of MISMATCHES found by objective checks.

    Each item: category, description, a/b = {doc, field, value}, difference, status.
    """

    inc = x.get("income", {})
    bal = x.get("balance_detail", {})
    cf = x.get("cash_detail", {})
    rev = x.get("revenue", {})
    note = x.get("rev_note", {})

    found = []

    def compare(category, description, a, b):
        if not _have(a["value"], b["value"]):
            return
        result = calculate_difference(a["value"], b["value"])
        if result["difference"] > TOLERANCE:
            found.append({
                "category": category,
                "description": description,
                "a": a,
                "b": b,
                "difference": result["difference"],
                "status": result["status"],
            })

    # 1. Quarterly revenue adds up to the report total
    q = [rev.get("Q1"), rev.get("Q2"), rev.get("Q3"), rev.get("Q4")]
    if _have(*q):
        compare(
            "Revenue",
            "The sum of the quarterly revenues does not match the "
            "Total Revenue in the Quarterly Revenue Report.",
            {"doc": "revenue_report", "field": "Sum of Q1-Q4", "value": sum(q)},
            {"doc": "revenue_report", "field": "Total Revenue", "value": rev.get("Total Revenue")},
        )

    # 2. Management note vs report total
    compare(
        "Revenue",
        "Reported Annual Revenue in the management note does not match "
        "the Total Revenue in the Quarterly Revenue Report.",
        {"doc": "revenue_report", "field": "Reported Annual Revenue",
         "value": note.get("Reported Annual Revenue")},
        {"doc": "revenue_report", "field": "Total Revenue", "value": rev.get("Total Revenue")},
    )

    # 3. Asset lines add up to Total Assets
    assets = [bal.get(k) for k in ("Cash", "Accounts Receivable", "Inventory", "PPE", "Other Assets")]
    if _have(*assets):
        compare(
            "Balance Sheet",
            "The listed asset lines do not add up to Total Assets.",
            {"doc": "balance_sheet", "field": "Sum of asset lines", "value": sum(assets)},
            {"doc": "balance_sheet", "field": "Total Assets", "value": bal.get("Total Assets")},
        )

    # 4. Liability and equity lines add up to the total
    liabs = [bal.get(k) for k in ("Accounts Payable", "Short-Term Debt", "Long-Term Debt",
                                  "Other Liabilities", "Equity")]
    if _have(*liabs):
        compare(
            "Balance Sheet",
            "The listed liability and equity lines do not add up to "
            "Total Liabilities and Equity.",
            {"doc": "balance_sheet", "field": "Sum of liability and equity lines", "value": sum(liabs)},
            {"doc": "balance_sheet", "field": "Total Liabilities and Equity",
             "value": bal.get("Total Liabilities and Equity")},
        )

    # 5. Operating + investing + financing = net change in cash
    flows = [cf.get("Net Cash from Operations"), cf.get("Net Cash from Investing"),
             cf.get("Net Cash from Financing")]
    if _have(*flows):
        compare(
            "Cash Flow",
            "Operating, investing and financing cash flows do not add up "
            "to the Net Change in Cash.",
            {"doc": "cash_flow", "field": "Sum of operating, investing and financing", "value": sum(flows)},
            {"doc": "cash_flow", "field": "Net Change in Cash", "value": cf.get("Net Change")},
        )

    # 6. Closing cash (cash flow) vs cash on the balance sheet
    compare(
        "Cash Flow",
        "Closing Cash in the Cash Flow Statement does not match Cash and "
        "Cash Equivalents in the Balance Sheet.",
        {"doc": "cash_flow", "field": "Closing Cash Balance", "value": cf.get("Closing Cash")},
        {"doc": "balance_sheet", "field": "Cash and Cash Equivalents", "value": bal.get("Cash")},
    )

    # 7. Net income (cash flow) vs profit after tax (income statement)
    compare(
        "Income Statement",
        "Net Income in the Cash Flow Statement does not match Profit "
        "After Tax in the Income Statement.",
        {"doc": "cash_flow", "field": "Net Income", "value": cf.get("Net Income")},
        {"doc": "income_statement", "field": "Profit After Tax", "value": inc.get("PAT")},
    )

    return found


# ---------------------------------------------------------------
# Key metrics (information only: no risk flags, no thresholds)
# ---------------------------------------------------------------

def compute_metrics(x):
    """Return a list of {name, value, unit, formula} that can be computed."""

    inc = x.get("income", {})
    bal = x.get("balance_detail", {})
    cf = x.get("cash_detail", {})

    metrics = []

    def add(name, value, unit, formula):
        if value is not None:
            metrics.append({"name": name, "value": round(value, 2), "unit": unit, "formula": formula})

    def ratio(a, b, scale=1.0):
        if _have(a, b) and b != 0:
            return a / b * scale
        return None

    add("Gross margin", ratio(inc.get("Gross Profit"), inc.get("Revenue"), 100), "%",
        "Gross Profit / Revenue (Income Statement)")
    add("Operating margin", ratio(inc.get("Operating Profit"), inc.get("Revenue"), 100), "%",
        "Operating Profit / Revenue (Income Statement)")
    add("Net margin", ratio(inc.get("PAT"), inc.get("Revenue"), 100), "%",
        "Profit After Tax / Revenue (Income Statement)")
    add("Interest cover", ratio(inc.get("Operating Profit"), inc.get("Finance Cost")), "x",
        "Operating Profit / Finance Cost")

    debt = None
    if _have(bal.get("Short-Term Debt"), bal.get("Long-Term Debt")):
        debt = bal["Short-Term Debt"] + bal["Long-Term Debt"]

    add("Total debt", debt, "Cr", "Short-Term Debt + Long-Term Debt")
    add("Debt to equity", ratio(debt, bal.get("Equity")), "x", "Total debt / Shareholders' Equity")

    if _have(debt, bal.get("Cash")):
        add("Net debt", debt - bal["Cash"], "Cr", "Total debt - Cash and Cash Equivalents")

    if _have(cf.get("Net Cash from Operations"), cf.get("Capital Expenditure")):
        add("Free cash flow",
            cf["Net Cash from Operations"] - abs(cf["Capital Expenditure"]), "Cr",
            "Net Cash from Operations - Capital Expenditure")

    return metrics
