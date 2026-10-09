import sys
sys.path.insert(0, ".")

from models import gateway
import agents.financial_agent as fa

GOOD = ('{"issue": "Revenue does not match", "why_it_matters": "Values differ and need review", '
        '"what_should_be_reviewed": "Review both documents", "evidence_conclusion": "A 20 Cr difference exists"}')


class Fake:
    def __init__(self, text):
        self.text = text

    def generate(self, system, prompt, max_new_tokens=300):
        return self.text


def ask(text):
    gateway.set_backend(Fake(text))
    return gateway.ask_reasoning("prompt")


def test_gateway():
    r, e = ask(GOOD)
    assert r and e is None and r["issue"].startswith("Revenue")
    print("1 ok  clean JSON")

    r, e = ask("Sure! Here you go:\n```json\n" + GOOD + "\n```\nHope that helps.")
    assert r and e is None
    print("2 ok  fenced JSON with extra text")

    r, e = ask("I cannot answer that.")
    assert r is None and "valid JSON" in e
    print("3 ok  garbage -> None")

    r, e = ask('{"issue": "Revenue does not match"}')
    assert r is None and "structure" in e
    print("4 ok  missing fields -> None")

    r, e = ask('{"issue": "Revenue does not match", ')
    assert r is None
    print("5 ok  broken JSON -> None")

    gateway.set_backend(Fake("nonsense"))
    state = {"findings": [{
        "finding_id": "FIN-001", "category": "Revenue", "severity": "HIGH",
        "status": "REVIEW_REQUIRED",
        "description": "Revenue reported in the Income Statement does not match the Total Revenue.",
        "impact": "x",
        "evidence": [
            {"document": "a.txt", "page": 1, "field": "Revenue", "value": 100.0},
            {"document": "b.txt", "page": 1, "field": "Total Revenue", "value": 120.0},
        ],
    }]}
    out = fa.reason_node(state)["findings"][0]
    assert out["evidence_guard"]["status"] == "REJECTED_AND_REPLACED"
    assert "20.00" in out["ai_reasoning"]["evidence_conclusion"]
    print("6 ok  bad model output -> safe reasoning")

    LIST_JSON = ('{"issue": "Revenue does not match", "why_it_matters": "Values differ and need review", '
                 '"what_should_be_reviewed": ["a.txt", "b.txt"], "evidence_conclusion": "A 20 Cr difference exists"}')
    r, e = ask(LIST_JSON)
    assert r and e is None and r["what_should_be_reviewed"] == "a.txt, b.txt"
    print("7 ok  list value joined into text")

    print("ALL GATEWAY TESTS PASSED")


if __name__ == "__main__":
    test_gateway()

