from processing.document_processor import extract_all_documents

from tools.document_tools import (
    extract_income_statement,
    extract_balance_sheet,
    extract_cash_flow,
    extract_revenue_report,
)

documents = extract_all_documents("documents")

for document in documents:

    name = document["document"]
    text = document["text"]

    print("\n" + "=" * 60)
    print(name)
    print("=" * 60)

    if name == "01_income_statement.txt":
        print(extract_income_statement(text))

    elif name == "02_balance_sheet.txt":
        print(extract_balance_sheet(text))

    elif name == "03_cash_flow_statement.txt":
        print(extract_cash_flow(text))

    elif name == "04_revenue_report.txt":
        print(extract_revenue_report(text))
