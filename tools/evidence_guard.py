# tools/evidence_guard.py

import re


# Claims that the AI is not allowed to introduce unless they are explicitly
# supported by the supplied evidence.
UNSUPPORTED_TERMS = [
    "fraud",
    "fraudulent",
    "misreporting",
    "manipulation",
    "illegal",
    "intentional",
    "deliberate",
    "revenue recognition",
    "inventory management",
    "accounting error",
    "accounting errors",
    "financial process",
    "financial processes",
    "internal control",
    "internal controls",
    "actual revenue",
    "true revenue",
    "incorrect revenue",
    "wrong revenue",
    "incorrect value",
    "wrong value",
    "error in",
    "errors in",
    "ensure accuracy",
    "inaccurate",
    "could indicate",
    "may indicate",
    "might indicate",
    "potential issue",
    "potential error",
    "possible error",
    "understatement",
    "overstatement",
]


def normalize_text(text: str) -> str:
    """
    Normalize text for safe comparison.
    """
    if not text:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(text).strip().lower(),
    )


def contains_unsupported_claim(text: str):
    """
    Return unsupported terms found in the supplied text.
    """
    normalized = normalize_text(text)

    found = []

    for term in UNSUPPORTED_TERMS:
        if term in normalized:
            found.append(term)

    return sorted(set(found))


def evidence_values(finding: dict):
    """
    Extract numeric values explicitly supplied by the finding evidence.
    """
    values = []

    for evidence in finding.get("evidence", []):
        if "value" in evidence:
            try:
                values.append(float(evidence["value"]))
            except (TypeError, ValueError):
                pass

    return values


def evidence_documents(finding: dict):
    """
    Return the document names explicitly supplied as evidence.
    """
    documents = []

    for evidence in finding.get("evidence", []):
        document = evidence.get("document")

        if document:
            documents.append(str(document))

    return sorted(set(documents))


def extract_financial_numbers(text: str):
    """
    Extract financial-looking numbers from AI reasoning.

    Important:
    - Ignore finding IDs such as FIN-001.
    - Ignore document names such as 01_income_statement.txt.
    - Ignore years such as 2025-26.
    - Ignore page numbers.
    """

    if not text:
        return []

    cleaned = str(text)

    # ---------------------------------------------------------
    # Remove finding IDs
    # Examples:
    # FIN-001
    # FIN-002
    # LEG-001
    # ---------------------------------------------------------
    cleaned = re.sub(
        r"\b[A-Z]{2,10}-\d+\b",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    # ---------------------------------------------------------
    # Remove document filenames
    # Examples:
    # 01_income_statement.txt
    # 04_revenue_report.txt
    # ---------------------------------------------------------
    cleaned = re.sub(
        r"\b\d+_[A-Za-z0-9_.-]+\.[A-Za-z0-9]+\b",
        "",
        cleaned,
    )

    # ---------------------------------------------------------
    # Remove years
    # Examples:
    # 2025
    # 2025-26
    # 2025/26
    # ---------------------------------------------------------
    cleaned = re.sub(
        r"\b20\d{2}(?:[-/]\d{2,4})?\b",
        "",
        cleaned,
    )

    # ---------------------------------------------------------
    # Remove page references
    # Examples:
    # Page 1
    # page 2
    # pages 1-2
    # ---------------------------------------------------------
    cleaned = re.sub(
        r"\bpages?\s+\d+(?:\s*[-–]\s*\d+)?\b",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    # ---------------------------------------------------------
    # Extract numbers.
    #
    # Supports:
    # 100
    # 100.00
    # 1,000
    # 1,000.00
    # -20.00
    # ---------------------------------------------------------
    matches = re.findall(
        r"(?<![A-Za-z0-9])[-+]?\d[\d,]*(?:\.\d+)?",
        cleaned,
    )

    numbers = []

    for value in matches:

        value = value.replace(",", "")

        try:
            number = float(value)
            numbers.append(number)
        except ValueError:
            continue

    return numbers


def validate_reasoning(reasoning: dict, finding: dict):
    """
    Validate AI-generated reasoning against the finding evidence.

    Returns:

        {
            "valid": True/False,
            "issues": [...]
        }
    """

    issues = []

    # ---------------------------------------------------------
    # 1. Validate basic JSON structure
    # ---------------------------------------------------------

    if not isinstance(reasoning, dict):
        return {
            "valid": False,
            "issues": ["AI reasoning is not a JSON object."],
        }

    required_fields = [
        "issue",
        "why_it_matters",
        "what_should_be_reviewed",
        "evidence_conclusion",
    ]

    for field in required_fields:
        if not reasoning.get(field):
            issues.append(
                f"Missing required reasoning field: {field}"
            )

    if issues:
        return {
            "valid": False,
            "issues": issues,
        }

    # ---------------------------------------------------------
    # Combine AI reasoning
    # ---------------------------------------------------------

    reasoning_text = " ".join(
        str(reasoning.get(field, ""))
        for field in required_fields
    )

    # ---------------------------------------------------------
    # 2. Check unsupported claims
    # ---------------------------------------------------------

    unsupported = contains_unsupported_claim(
        reasoning_text
    )

    if unsupported:
        issues.append(
            "Unsupported claims detected: "
            + ", ".join(unsupported)
        )

    # ---------------------------------------------------------
    # 3. Check that AI is actually discussing the finding
    # ---------------------------------------------------------

    finding_description = normalize_text(
        finding.get("description", "")
    )

    ai_issue = normalize_text(
        reasoning.get("issue", "")
    )

    if finding_description and ai_issue:

        finding_words = {
            word
            for word in re.findall(
                r"[a-zA-Z]{4,}",
                finding_description,
            )
        }

        ai_words = {
            word
            for word in re.findall(
                r"[a-zA-Z]{4,}",
                ai_issue,
            )
        }

        meaningful_overlap = (
            finding_words.intersection(ai_words)
        )

        if len(meaningful_overlap) < 2:

            issues.append(
                "AI reasoning does not sufficiently "
                "reference the identified finding."
            )

    # ---------------------------------------------------------
    # 4. Evidence document check
    # ---------------------------------------------------------

    supplied_documents = evidence_documents(
        finding
    )

    review_text = normalize_text(
        reasoning.get(
            "what_should_be_reviewed",
            "",
        )
    )

    if len(supplied_documents) >= 2:

        missing_documents = []

        for document in supplied_documents:

            if normalize_text(document) not in review_text:
                missing_documents.append(document)

        if missing_documents:

            issues.append(
                "Review section does not name supplied "
                "source documents: "
                + ", ".join(missing_documents)
            )

    # ---------------------------------------------------------
    # 5. Numeric evidence check
    # ---------------------------------------------------------

    allowed_values = evidence_values(finding)

    ai_numbers = extract_financial_numbers(
        reasoning_text
    )

    # The direct difference between two supplied values
    # is allowed.
    allowed_numbers = set(
        round(value, 6)
        for value in allowed_values
    )

    if len(allowed_values) >= 2:

        difference = abs(
            allowed_values[0] -
            allowed_values[1]
        )

        allowed_numbers.add(
            round(difference, 6)
        )

    for number in ai_numbers:

        normalized_number = round(
            number,
            6,
        )

        if normalized_number not in allowed_numbers:

            issues.append(
                "AI introduced unsupported numeric value: "
                + str(number)
            )

    # ---------------------------------------------------------
    # Final result
    # ---------------------------------------------------------

    return {
        "valid": len(issues) == 0,
        "issues": issues,
    }


def create_safe_reasoning(finding: dict):
    """
    Create deterministic reasoning using only supplied evidence.
    """

    description = finding.get(
        "description",
        "The supplied documents contain a discrepancy.",
    )

    documents = evidence_documents(
        finding
    )

    values = evidence_values(
        finding
    )

    if len(values) >= 2:

        difference = abs(
            values[0] -
            values[1]
        )

        difference_text = (
            f"{difference:.2f}"
        )

        if len(documents) >= 2:
            why_it_matters = (
                "The two supplied documents contain "
                "different values for the same financial "
                "metric and should be reconciled."
            )
        else:
            why_it_matters = (
                "The reported value does not match the value "
                "calculated from the other figures in the same "
                "document and should be reconciled."
            )

        review_text = (
            "Review "
            + " and ".join(documents)
            + " to determine the reason for the "
            + f"₹{difference_text} Cr difference."
        )

        evidence_conclusion = (
            "The supplied evidence confirms a "
            + f"₹{difference_text} Cr difference "
            "between the two reported values."
        )

    else:

        why_it_matters = (
            "The supplied evidence identifies a "
            "difference that should be reviewed."
        )

        review_text = (
            "Review the supplied source documents "
            "and supporting evidence."
        )

        evidence_conclusion = (
            "The supplied evidence supports the "
            "identified finding."
        )

    return {
        "issue": description,
        "why_it_matters": why_it_matters,
        "what_should_be_reviewed": review_text,
        "evidence_conclusion": evidence_conclusion,
    }