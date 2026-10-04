"""Detect the type of a financial document from its CONTENT (file name is only a weak hint)."""

# type -> (title phrases [weight 3 if in first lines], body phrases [weight 1])
RULES = {
    "income_statement": (
        ["income statement", "statement of profit and loss", "profit and loss"],
        ["gross profit", "cost of goods sold", "operating profit",
         "profit before tax", "profit after tax", "finance cost"],
    ),
    "balance_sheet": (
        ["balance sheet"],
        ["total assets", "total liabilities and equity", "shareholders' equity",
         "accounts payable", "accounts receivable"],
    ),
    "cash_flow": (
        ["cash flow statement", "statement of cash flows"],
        ["operating activities", "investing activities", "financing activities",
         "closing cash", "opening cash"],
    ),
    "revenue_report": (
        ["quarterly revenue", "revenue report"],
        ["reported annual revenue", "q1", "q2", "q3", "q4", "total revenue"],
    ),
}

FILENAME_HINTS = {
    "income_statement": ["income", "profit", "p&l", "pnl"],
    "balance_sheet": ["balance", "bs"],
    "cash_flow": ["cash", "cf"],
    "revenue_report": ["revenue", "sales"],
}

MIN_SCORE = 3


def classify_document(document: dict) -> dict:
    """Return {"document", "type", "confidence", "reason"} for one document."""

    name = document.get("document", "")
    text = (document.get("text") or "").lower()
    head = " ".join(text.splitlines()[:6])

    best_type, best_score, best_reason = "unclassified", 0, []

    for doc_type, (titles, body) in RULES.items():
        score, reason = 0, []

        for phrase in titles:
            if phrase in head:
                score += 3
                reason.append(f"title '{phrase}'")

        for phrase in body:
            if phrase in text:
                score += 1
                reason.append(f"'{phrase}'")

        lowered = name.lower()
        if any(h in lowered for h in FILENAME_HINTS[doc_type]):
            score += 1
            reason.append("file name hint")

        if score > best_score:
            best_type, best_score, best_reason = doc_type, score, reason

    if best_score < MIN_SCORE:
        return {
            "document": name,
            "type": "unclassified",
            "confidence": 0.0,
            "reason": "not enough matching content",
        }

    return {
        "document": name,
        "type": best_type,
        "confidence": round(min(1.0, best_score / 6), 2),
        "reason": ", ".join(best_reason[:4]),
    }


def classify_documents(documents: list) -> list:
    return [classify_document(d) for d in documents]
