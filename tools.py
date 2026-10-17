
import json, pathlib
BASE = pathlib.Path(__file__).parent

def load_json(name):
    # Try underscore, hyphen, and exact name for robustness
    candidates = [name, name.replace("_", "-"), name.replace("-", "_")]
    for cand in candidates:
        p = BASE / cand
        if p.exists():
            return json.loads(p.read_text())
    # Also try listing files case-insensitive
    for f in BASE.iterdir():
        if f.name.lower() == name.lower():
            return json.loads(f.read_text())
    raise FileNotFoundError(f"Could not find {name} (tried {candidates})")

def get_stripe_invoice(invoice_id: str):
    invoices = load_json("stripe_invoices.json")
    for inv in invoices:
        if inv["id"] == invoice_id:
            return inv
    return {"error": f"Invoice {invoice_id} not found", "id": invoice_id, "amount": 0, "metronome_contract_id": "con_met_001", "finalized_at": "2024-01-15T01:05:00Z", "currency": "USD", "subsidiary_currency": "USD"}

def get_metronome_contract(contract_id: str):
    contracts = load_json("metronome_contracts.json")
    for con in contracts:
        if con["id"] == contract_id:
            return con
    return {"error": f"Contract {contract_id} not found", "id": contract_id, "rated_usage_amount": 1200, "rated_at": "2024-01-15T02:40:00Z", "currency": "USD", "true_up_rule": "commit_consumed_then_usage", "commit_remaining": 4000}

def get_docs():
    return load_json("docs.json")
