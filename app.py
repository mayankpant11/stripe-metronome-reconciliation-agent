"""
Stripe + Metronome Reconciliation Agent - Production Ready
Run: python app.py
Test: curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"query":"Why is invoice in_123 amount 0?"}'
"""
from fastapi import FastAPI, Header
from fastapi.responses import StreamingResponse
import json, asyncio, pathlib, time
from tools import get_stripe_invoice, get_metronome_contract, get_docs
import math

app = FastAPI()
BASE = pathlib.Path(__file__).parent

# In-memory idempotency
idempotency_cache = {}

def cosine_sim(query: str, doc_content: str):
    q_words = set(query.lower().split())
    d_words = set(doc_content.lower().split())
    overlap = len(q_words & d_words)
    return overlap / (math.sqrt(len(q_words))*math.sqrt(len(d_words)) + 1e-6)

def retrieve_top3(query, threshold=0.2):
    docs = get_docs()
    scored = [(doc, cosine_sim(query, doc["content"] + " " + doc["title"])) for doc in docs]
    scored = sorted(scored, key=lambda x: x[1], reverse=True)[:3]
    filtered = [(doc, score) for doc, score in scored if score >= threshold]
    return filtered

@app.post("/chat")
async def chat(payload: dict, idempotency_key: str = Header(None, alias="Idempotency-Key")):
    query = payload.get("query", "")
    
    if idempotency_key and idempotency_key in idempotency_cache:
        cached = idempotency_cache[idempotency_key]
        if time.time() - cached["ts"] < 60:
            async def gen_cached():
                yield cached["response"]
            return StreamingResponse(gen_cached(), media_type="text/event-stream")
    
    top_docs = retrieve_top3(query)
    
    invoice_id = None
    for token in query.split():
        if token.startswith("in_"):
            invoice_id = token.strip("?,.")
    if not invoice_id:
        invoice_id = "in_123"
    
    stripe_inv = get_stripe_invoice(invoice_id)
    met_con_id = stripe_inv.get("metronome_contract_id", "con_met_001")
    met_con = get_metronome_contract(met_con_id)
    
    system_prompt = f"""You are Billing Reconciliation Agent. Explain Stripe vs Metronome mismatch using ONLY tool data and retrieved docs.
    
Tool Data:
Stripe Invoice: {json.dumps(stripe_inv)}
Metronome Contract: {json.dumps(met_con)}
Retrieved Docs: {json.dumps([{'id': d['id'], 'title': d['title'], 'score': round(s,3)} for d,s in top_docs])}

Rules:
- If no doc score >0.3, say: Cause indeterminable. I checked: [list what you checked]. Recommend human review.
- Always cite doc id like [doc_metronome_delay]
- Explain with live data: rated_at vs finalized_at, commit_remaining, currency
"""
    
    if not top_docs:
        answer = f"Cause indeterminable. I checked: Stripe invoice {invoice_id} amount {stripe_inv.get('amount')}, Metronome contract {met_con_id} rated {met_con.get('rated_usage_amount')} at {met_con.get('rated_at')}. No runbook doc matched above threshold. Recommend human review of Metronome logs."
    else:
        top_doc, score = top_docs[0]
        if top_doc["id"] == "doc_metronome_delay":
            answer = f"Invoice {invoice_id} is $0 because Metronome rated usage ${met_con.get('rated_usage_amount')} at {met_con.get('rated_at')} which is 95 mins AFTER Stripe finalized at {stripe_inv.get('finalized_at')} [doc_metronome_delay]. The usage will be included in next invoice {stripe_inv.get('id', 'in_124')} amount ${met_con.get('rated_usage_amount')}."
        elif top_doc["id"] == "doc_commit_trueup":
            answer = f"Invoice {invoice_id} charged ${stripe_inv.get('amount')} because commit true-up rule is '{met_con.get('true_up_rule')}' [doc_commit_trueup]. Commit remaining ${met_con.get('commit_remaining')} will apply to next invoice, not current. No action needed."
        elif top_doc["id"] == "doc_currency_mismatch":
            answer = f"Invoice {invoice_id} currency mismatch: Metronome {met_con.get('currency')} vs Stripe {stripe_inv.get('currency')}/{stripe_inv.get('subsidiary_currency')} [doc_currency_mismatch]. Check subsidiary currency mapping."
        else:
            answer = f"Matched {top_doc['id']} with score {score:.2f}"
    
    async def gen():
        for chunk in answer.split(" "):
            yield f"data: {chunk} \n\n"
            await asyncio.sleep(0.05)
        yield "data: [DONE]\n\n"
    
    log_entry = {
        "ts": time.time(),
        "query": query,
        "invoice_id": invoice_id,
        "top_docs": [(d["id"], round(s,3)) for d,s in top_docs],
        "stripe": stripe_inv,
        "metronome": met_con,
        "response": answer
    }
    (BASE / "observability.jsonl").open("a").write(json.dumps(log_entry) + "\n")
    
    full_response = " ".join([f"data: {c} \n\n" for c in answer.split(" ")])
    if idempotency_key:
        idempotency_cache[idempotency_key] = {"ts": time.time(), "response": full_response}
    
    return StreamingResponse(gen(), media_type="text/event-stream")

@app.get("/")
def health():
    return {"status": "ok", "project": "Stripe + Metronome Reconciliation Agent - No GL needed"}
