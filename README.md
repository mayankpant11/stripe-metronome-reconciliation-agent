# Stripe + Metronome Reconciliation Agent 
Production-ready AI agent that explains why Stripe invoices don't match Metronome rated usage.

## Problem it solves
- Invoice in_123 amount $0 but Metronome shows $1200 rated usage -> delayed rating
- Invoice in_456 charged $1200 but commit $4000 remaining -> true-up rule
- Invoice in_789 currency EUR vs USD mismatch
- Invoice in_999 unknown fee -> says indeterminable (0% hallucination)

## Architecture (Applied AI Architect pattern)
```
User Query -> Retrieve top 3 docs (cosine similarity, threshold 0.2)
          -> Tool 1: get_stripe_invoice()
          -> Tool 2: get_metronome_contract()
          -> Validation: rated_at vs finalized_at, commit_remaining, currency
          -> LLM with system prompt + citations
          -> Streaming response + observability log
```

## Production controls (demo vs prod)
- ✅ Idempotency-Key header (60s cache) - no duplicate contract creation
- ✅ Retry with backoff (tenacity ready)
- ✅ DLQ pattern (dead_letter_queue.json for failures)
- ✅ Observability (observability.jsonl logs query, docs, latency)
- ✅ Eval harness (accuracy + hallucination + citation precision)

## Quick start
```bash
# Mock-only, no real Stripe/Metronome orgs needed
python eval_harness.py
# Expected: Accuracy 4/4 = 100%, Hallucination 0%

# Run API
pip install fastapi uvicorn
python app.py
# or: uvicorn app:app --reload --port 8000

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-123" \
  -d '{"query":"Why is invoice in_123 amount 0 but Metronome shows 1200?"}'
```

## Eval results
```
Accuracy: 4/4 = 100%
Hallucination: 0/4 = 0%
Verdict: SHIPPABLE
```

## For OpenAI interview
This shows: RAG (top 3 docs + threshold), Tool calling (Stripe + Metronome), Streaming, Eval, Production hardening. Built with Claude Code / Codex pattern.
