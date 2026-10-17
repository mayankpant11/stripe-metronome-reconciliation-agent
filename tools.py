
import json, pathlib
BASE = pathlib.Path(__file__).parent

def load_json(name):
    return json.loads((BASE / name).read_text())

def get_stripe_invoice(invoice_id: str):
    """Tool: Get Stripe invoice by ID - mocked from stripe_invoices.json"""
    invoices = load_json("stripe_invoices.json")
    for inv in invoices:
        if inv["id"] == invoice_id:
            return inv
    return {"error": f"Invoice {invoice_id} not found"}

def get_metronome_contract(contract_id: str):
    """Tool: Get Metronome contract by ID - mocked from metronome_contracts.json"""
    contracts = load_json("metronome_contracts.json")
    for con in contracts:
        if con["id"] == contract_id:
            return con
    return {"error": f"Contract {contract_id} not found"}

def get_docs():
    return load_json("docs.json")
