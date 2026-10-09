import sys
sys.path.insert(0, ".")

from processing.document_processor import extract_all_documents
from tools.legal_tools import extract_clauses, is_contract, verify_quote
from agents.legal_agent import build_legal_subgraph

def test_legal():
    docs = extract_all_documents("documents")
    by_name = {d["document"]: d for d in docs}
    contract = by_name["05_customer_agreement.txt"]

    # 1. contract detected, financial documents are not
    assert is_contract(contract)
    financial_docs = [d for d in docs if any(d["document"].startswith(p) for p in ("01_", "02_", "03_", "04_"))]
    assert not any(is_contract(d) for d in financial_docs)
    assert len(contract["pages"]) == 3, len(contract["pages"])
    print("1 ok  contract detected, 3 pages read")

    # 2. clauses found on the correct pages
    hits = {h["clause_id"]: h for h in extract_clauses(contract)}
    assert hits["auto_renewal"]["page"] == 1, hits["auto_renewal"]
    assert hits["termination_convenience"]["page"] == 2
    assert hits["assignment"]["page"] == 2
    assert hits["change_of_control"]["page"] == 3
    print("2 ok  clauses mapped to correct pages")

    # 3. every quote really exists on its page
    for h in hits.values():
        assert verify_quote(h["quote"], contract["pages"][h["page"] - 1]), h
    assert not verify_quote("this sentence is invented", contract["pages"][0])
    print("3 ok  quotes verified against the page text")

    # 4. full workstream: findings, severity, evidence, missing clause
    out = build_legal_subgraph().invoke({"documents": [contract] + financial_docs, "findings": [], "status": "STARTED"})
    f = out["findings"]
    cats = {x["category"]: x for x in f}
    assert cats["Change of Control"]["severity"] == "HIGH"
    assert cats["Change of Control"]["evidence"][0]["page"] == 3
    assert cats["Change of Control"]["finding_id"].startswith("LEG-")
    missing = [x for x in f if x["type"] == "MISSING_CLAUSE"]
    assert [m["description"] for m in missing] == ["Limitation of Liability clause was not found in 05_customer_agreement.txt."], missing
    assert not any("Governing Law" in x["description"] for x in f)
    print("4 ok  findings: HIGH change of control p.3, missing liability clause")

    # 5. no contracts -> missing-document finding, no crash
    out = build_legal_subgraph().invoke({"documents": financial_docs, "findings": []})
    assert [x["type"] for x in out["findings"]] == ["MISSING_DOCUMENT"]
    print("5 ok  no contracts -> single missing-document finding")

    print("ALL LEGAL TESTS PASSED")


if __name__ == "__main__":
    test_legal()

