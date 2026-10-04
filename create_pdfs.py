from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from pathlib import Path

OUT = Path("documents")
OUT.mkdir(exist_ok=True)

styles = getSampleStyleSheet()


def create_pdf(filename, title, subtitle, sections):

    path = OUT / filename

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    story = []

    story.append(
        Paragraph(
            "AsterNova Technologies Pvt. Ltd.",
            styles["Title"]
        )
    )

    story.append(
        Paragraph(
            title,
            styles["Heading2"]
        )
    )

    story.append(
        Paragraph(
            subtitle,
            styles["Normal"]
        )
    )

    story.append(Spacer(1, 20))

    for section_title, rows in sections:

        story.append(
            Paragraph(
                section_title,
                styles["Heading3"]
            )
        )

        table_data = [["Particular", "FY 2025-26"]]

        for row in rows:
            table_data.append(list(row))

        table = Table(
            table_data,
            colWidths=[4.2 * inch, 1.5 * inch]
        )

        table.setStyle(
            TableStyle([
                ("GRID", (0,0), (-1,-1), 0.5, colors.black),
                ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                ("ALIGN", (1,1), (-1,-1), "RIGHT"),
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                ("BOTTOMPADDING", (0,0), (-1,-1), 6),
                ("TOPPADDING", (0,0), (-1,-1), 6),
            ])
        )

        story.append(table)
        story.append(Spacer(1, 15))

    doc.build(story)

    print(f"Created: {path}")


# ------------------------------------------------------------
# 01 Income Statement
# ------------------------------------------------------------

create_pdf(
    "01_income_statement.pdf",
    "Income Statement",
    "Financial Year 2025-26 | Amounts in ₹ Crore",
    [
        (
            "Statement of Profit and Loss",
            [
                ("Revenue", "100.00"),
                ("Cost of Goods Sold", "58.00"),
                ("Gross Profit", "42.00"),
                ("Operating Expenses", "27.00"),
                ("Operating Profit", "15.00"),
                ("Finance Cost", "3.00"),
                ("Profit Before Tax", "12.00"),
                ("Tax Expense", "3.00"),
                ("Profit After Tax", "9.00"),
            ],
        ),
        (
            "Notes",
            [
                ("Reporting Currency", "INR"),
                ("Reporting Period", "FY 2025-26"),
            ],
        ),
    ],
)


# ------------------------------------------------------------
# 02 Balance Sheet
# ------------------------------------------------------------

create_pdf(
    "02_balance_sheet.pdf",
    "Balance Sheet",
    "As at 31 March 2026 | Amounts in ₹ Crore",
    [
        (
            "Assets",
            [
                ("Cash and Cash Equivalents", "18.00"),
                ("Accounts Receivable", "24.00"),
                ("Inventory", "12.00"),
                ("Property, Plant and Equipment", "46.00"),
                ("Other Assets", "10.00"),
                ("Total Assets", "110.00"),
            ],
        ),
        (
            "Liabilities and Equity",
            [
                ("Accounts Payable", "16.00"),
                ("Short-Term Debt", "14.00"),
                ("Long-Term Debt", "30.00"),
                ("Other Liabilities", "10.00"),
                ("Shareholders' Equity", "40.00"),
                ("Total Liabilities and Equity", "110.00"),
            ],
        ),
    ],
)


# ------------------------------------------------------------
# 03 Cash Flow Statement
# ------------------------------------------------------------

create_pdf(
    "03_cash_flow_statement.pdf",
    "Cash Flow Statement",
    "Financial Year 2025-26 | Amounts in ₹ Crore",
    [
        (
            "Cash Flows from Operating Activities",
            [
                ("Net Income", "9.00"),
                ("Depreciation", "5.00"),
                ("Increase in Working Capital", "-4.00"),
                ("Net Cash from Operations", "10.00"),
            ],
        ),
        (
            "Cash Flows from Investing Activities",
            [
                ("Capital Expenditure", "-12.00"),
                ("Net Cash from Investing", "-12.00"),
            ],
        ),
        (
            "Cash Flows from Financing Activities",
            [
                ("Debt Raised", "8.00"),
                ("Debt Repayment", "-3.00"),
                ("Net Cash from Financing", "5.00"),
            ],
        ),
        (
            "Cash Movement",
            [
                ("Net Change in Cash", "3.00"),
                ("Opening Cash Balance", "15.00"),
                ("Closing Cash Balance", "18.00"),
            ],
        ),
    ],
)


# ------------------------------------------------------------
# 04 Quarterly Revenue Report
# ------------------------------------------------------------

create_pdf(
    "04_revenue_report.pdf",
    "Quarterly Revenue Report",
    "Financial Year 2025-26 | Amounts in ₹ Crore",
    [
        (
            "Quarterly Revenue",
            [
                ("Q1 FY2025-26", "24.00"),
                ("Q2 FY2025-26", "25.00"),
                ("Q3 FY2025-26", "28.00"),
                ("Q4 FY2025-26", "43.00"),
                ("Total Revenue", "120.00"),
            ],
        ),
        (
            "Management Note",
            [
                ("Reported Annual Revenue", "120.00"),
                ("Currency", "INR"),
            ],
        ),
    ],
)

print("")
print("ALL 4 PDFs CREATED SUCCESSFULLY")
