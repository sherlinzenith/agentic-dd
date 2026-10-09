import re


def extract_number(text, label):
    """
    Extract a number appearing immediately after a label.
    Example:
        Revenue 100.00
        Total Assets 110.00
    """

    pattern = rf"{re.escape(label)}\s+(-?[\d,.]+)"

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    return float(
        match.group(1).replace(",", "")
    )


def extract_income_statement(text):

    return {
        "Revenue": extract_number(
            text,
            "Revenue"
        ),

        "COGS": extract_number(
            text,
            "Cost of Goods Sold"
        ),

        "Gross Profit": extract_number(
            text,
            "Gross Profit"
        ),

        "Operating Expenses": extract_number(
            text,
            "Operating Expenses"
        ),

        "Operating Profit": extract_number(
            text,
            "Operating Profit"
        ),

        "Finance Cost": extract_number(
            text,
            "Finance Cost"
        ),

        "PBT": extract_number(
            text,
            "Profit Before Tax"
        ),

        "Tax": extract_number(
            text,
            "Tax Expense"
        ),

        "PAT": extract_number(
            text,
            "Profit After Tax"
        ),
    }


def extract_balance_sheet(text):

    return {
        "Cash": extract_number(
            text,
            "Cash and Cash Equivalents"
        ),

        "Total Assets": extract_number(
            text,
            "Total Assets"
        ),

        "Total Liabilities and Equity": extract_number(
            text,
            "Total Liabilities and Equity"
        ),
    }


def extract_cash_flow(text):

    return {
        "Opening Cash": extract_number(
            text,
            "Opening Cash Balance"
        ),

        "Net Change": extract_number(
            text,
            "Net Change in Cash"
        ),

        "Closing Cash": extract_number(
            text,
            "Closing Cash Balance"
        ),
    }


def extract_quarter(text, quarter):
    """Find a line like 'Q1 FY2025-26 24.00' or multi-line cell 'Q1 FY2025-26\n24.00' and return the number."""

    match = re.search(
        rf"{quarter}\b(?:[^\n]*\n\s*|[^\n]*?\s+)(-?[\d,]+\.\d+)",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    return float(match.group(1).replace(",", ""))


def extract_revenue_report(text):

    return {
        "Q1": extract_quarter(text, "Q1"),
        "Q2": extract_quarter(text, "Q2"),
        "Q3": extract_quarter(text, "Q3"),
        "Q4": extract_quarter(text, "Q4"),
        "Total Revenue": extract_number(text, "Total Revenue"),
    }


def _first(text, labels):
    for label in labels:
        value = extract_number(text, label)
        if value is not None:
            return value
    return None


def extract_balance_details(text):

    return {
        "Cash": _first(text, ["Cash and Cash Equivalents"]),
        "Accounts Receivable": _first(text, ["Accounts Receivable"]),
        "Inventory": _first(text, ["Inventory"]),
        "PPE": _first(text, ["Property, Plant and Equipment"]),
        "Other Assets": _first(text, ["Other Assets"]),
        "Total Assets": _first(text, ["Total Assets"]),
        "Accounts Payable": _first(text, ["Accounts Payable"]),
        "Short-Term Debt": _first(text, ["Short-Term Debt"]),
        "Long-Term Debt": _first(text, ["Long-Term Debt"]),
        "Other Liabilities": _first(text, ["Other Liabilities"]),
        "Equity": _first(text, ["Shareholders' Equity", "Shareholders\u2019 Equity", "Total Equity"]),
        "Total Liabilities and Equity": _first(text, ["Total Liabilities and Equity"]),
    }


def extract_cash_flow_details(text):

    return {
        "Net Income": _first(text, ["Net Income"]),
        "Net Cash from Operations": _first(text, ["Net Cash from Operations"]),
        "Capital Expenditure": _first(text, ["Capital Expenditure"]),
        "Net Cash from Investing": _first(text, ["Net Cash from Investing"]),
        "Net Cash from Financing": _first(text, ["Net Cash from Financing"]),
        "Net Change": _first(text, ["Net Change in Cash"]),
        "Closing Cash": _first(text, ["Closing Cash Balance"]),
    }


def extract_revenue_note(text):

    return {
        "Reported Annual Revenue": _first(text, ["Reported Annual Revenue"]),
    }
