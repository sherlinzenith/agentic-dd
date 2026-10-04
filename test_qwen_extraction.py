from models.qwen_model import ask_qwen

prompt = """
Read the following financial document.

Extract the following fields:
- Revenue
- COGS
- Gross Profit
- Operating Expenses
- Operating Profit
- Finance Cost
- PBT
- Tax
- PAT

Return ONLY the extracted values in this format:

Revenue: <value>
COGS: <value>
Gross Profit: <value>
Operating Expenses: <value>
Operating Profit: <value>
Finance Cost: <value>
PBT: <value>
Tax: <value>
PAT: <value>

Document:

Revenue: 100.00
COGS: 58.00
Gross Profit: 42.00
Operating Expenses: 27.00
Operating Profit: 15.00
Finance Cost: 3.00
PBT: 12.00
Tax: 3.00
PAT: 9.00
"""

result = ask_qwen(prompt)

print("\n===== QWEN EXTRACTION =====")
print(result)
