from __future__ import annotations
import os, json, hashlib, datetime, secrets
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, Body, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from omb.signing import Ed25519Signer
from omb.meter import meter_for_env, UsageIn, canonical_json
from omb.export import bundle_for

app = FastAPI(
    title="OMB — Meter & Billing API",
    version="0.1.2",
    description="Verifiable usage metering & signed export bundles. Optional Stripe billing endpoints guarded by env flags.",
)

# --- Signer (env-driven) ---
OMB_PRIVATE_KEY_B64 = os.getenv("OMB_PRIVATE_KEY_B64")
OMB_KID = os.getenv("OMB_KID")

_signer: Optional[Ed25519Signer] = None
if OMB_PRIVATE_KEY_B64 and OMB_KID:
    try:
        _signer = Ed25519Signer(priv_b64=OMB_PRIVATE_KEY_B64, kid=OMB_KID)
    except Exception as e:  # pragma: no cover - startup failures
        _signer = None

_meter = meter_for_env(_signer) if _signer else None

class MeterRequest(UsageIn):
    """Usage meter request body with minimal server-side validation."""
    @validator("quantity")
    def _qty_positive(cls, v):  # noqa: N805
        if v <= 0:
            raise ValueError("quantity must be > 0")
        return v

class ErrorModel(BaseModel):
    detail: str

class RateLimitInfo(BaseModel):
    limit: int
    remaining: int
    reset_seconds: int

RATE_LIMIT_MAX = int(os.getenv("OMB_RATE_LIMIT_MAX", "500"))

_RATE_BUCKET: Dict[str, int] = {}

def rate_limiter(req: Request) -> None:
    ip = req.client.host if req.client else "anon"
    used = _RATE_BUCKET.get(ip, 0) + 1
    _RATE_BUCKET[ip] = used
    if used > RATE_LIMIT_MAX:
        raise HTTPException(429, f"rate limit exceeded ({RATE_LIMIT_MAX}/window)")

def signer_dependency() -> Ed25519Signer:
    if not _signer:
        raise HTTPException(503, "Signer not configured")
    return _signer

def meter_dependency() -> Any:
    if not _meter:
        raise HTTPException(503, "Store not configured")
    return _meter

@app.get("/healthz", response_model=Dict[str, Any])
def healthz():
    return {
        "ok": True,
        "signer": bool(_signer),
        "store": os.getenv("OMB_STORE", "jsonl"),
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "rate_limit_max": RATE_LIMIT_MAX,
    }

@app.get("/.well-known/jwks.json", responses={503: {"model": ErrorModel}})
def jwks(signer: Ed25519Signer = Depends(signer_dependency)):
    return signer.jwks

@app.post(
    "/v1/meter",
    responses={
        201: {"description": "Created SUR"},
        400: {"model": ErrorModel},
        429: {"model": ErrorModel},
        503: {"model": ErrorModel},
    },
    status_code=201,
)
def meter(req: MeterRequest, _: None = Depends(rate_limiter), signer: Ed25519Signer = Depends(signer_dependency), store=Depends(meter_dependency)):
    sur = store.record(req)
    body = sur.model_dump()
    resp_cid = "sha256:" + hashlib.sha256(canonical_json(body)).hexdigest()
    msg = f"{resp_cid}|{sur.tenant_id}|{sur.ts}".encode("utf-8")
    sig = signer.sign(msg)
    return body | {"_response": {"cid": resp_cid, "sig": sig, "kid": signer.kid}}

@app.get(
    "/v1/usage/{tenant_id}/export",
    responses={200: {"description": "Signed bundle"}, 503: {"model": ErrorModel}},
)
def export_usage(tenant_id: str, since: Optional[str] = None, until: Optional[str] = None, signer: Ed25519Signer = Depends(signer_dependency), store=Depends(meter_dependency)):
    items = store.list_for_tenant(tenant_id, since, until)
    bundle = bundle_for(items, tenant_id, signer)
    return bundle

# --- Stripe stubs (optional) ---
import stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_ENABLED = bool(stripe.api_key)
PLATFORM_FEE_BPS = int(os.getenv("OMB_PLATFORM_FEE_BPS", "0") or 0)

REPORT_WINDOW_SECONDS = int(os.getenv("OMB_REPORT_WINDOW_SECONDS", str(24*3600)))

class CheckoutReq(BaseModel):
    success_url: str = Field(example="https://example.com/success")
    cancel_url: str = Field(example="https://example.com/cancel")
    price_id: Optional[str] = Field(default=None, example="price_123")  # if omitted, uses STRIPE_PRICE_ID

@app.post("/v1/billing/stripe/checkout", responses={501: {"model": ErrorModel}, 400: {"model": ErrorModel}})
def create_checkout_session(req: CheckoutReq):
    if not STRIPE_ENABLED:
        raise HTTPException(501, "Stripe not configured")
    price = req.price_id or os.getenv("STRIPE_PRICE_ID")
    if not price:
        raise HTTPException(400, "Missing price_id/STRIPE_PRICE_ID")
    try:
        sess = stripe.checkout.Session.create(
            mode="subscription",
            success_url=req.success_url,
            cancel_url=req.cancel_url,
            line_items=[{"price": price, "quantity": 1}],
        )
        return {"id": sess.id, "url": sess.url}
    except Exception as e:  # pragma: no cover
        raise HTTPException(500, f"Stripe error: {e}")

@app.get("/v1/billing/report/{tenant}")
def billing_report(tenant: str, signer: Ed25519Signer = Depends(signer_dependency), store=Depends(meter_dependency)):
    if not STRIPE_ENABLED:
        raise HTTPException(501, "Stripe not configured")
    until = datetime.datetime.now(datetime.timezone.utc)
    since = until - datetime.timedelta(seconds=REPORT_WINDOW_SECONDS)
    items = store.list_for_tenant(tenant, since_iso=since.isoformat(), until_iso=until.isoformat())
    total = sum(i.quantity for i in items)
    return {
        "tenant": tenant,
        "window": {"since": since.isoformat(), "until": until.isoformat()},
        "total_quantity": total,
        "records": len(items),
    }

class StripeEvent(BaseModel):
    id: str
    type: str
    data: Dict[str, Any]

@app.post("/v1/billing/invoice/apply")
def invoice_apply(evt: StripeEvent):
    if not STRIPE_ENABLED:
        raise HTTPException(501, "Stripe not configured")
    # Stub: in production you'd verify the signature header using STRIPE_WEBHOOK_SECRET
    if evt.type == "invoice.finalized" and PLATFORM_FEE_BPS > 0:
        # This is a placeholder to show where a platform fee line item would be appended.
        return {"handled": True, "platform_fee_bps": PLATFORM_FEE_BPS}
    return {"handled": False}

@app.get("/v1/rate_limit")
def rate_limit_status():
    return {"limit": RATE_LIMIT_MAX, "buckets": len(_RATE_BUCKET)}
