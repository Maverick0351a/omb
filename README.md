# OMB — ODIN Meter & Billing

Verifiable usage metering & signed export bundles with optional Stripe monetization. Build trust by letting customers independently verify their billed usage.

## About
OMB (ODIN Meter & Billing) provides a lightweight library and reference API for generating cryptographically signed usage records and export bundles. It targets platforms that need transparent, verifiable usage-based billing or auditing without heavy vendor lock-in.

Key goals:
- Deterministic content IDs (CIDs) over canonical JSON payloads.
- Ed25519 signatures for per-record (SUR) and bundle integrity.
- Pluggable storage (JSONL append-only default, SQLite prototype) with a simple abstraction you can replace with your datastore.
- Minimal FastAPI service exposing metering, export, and (optional) Stripe billing stubs.
- Clear verification helpers so any party with your JWKS can re-compute CIDs and validate signatures offline.

Website: https://www.odinsecure.ai

## Features
- Signed Usage Records (SUR) with base64url Ed25519 signatures.
- Signed export bundles (aggregate of SURs) for tenant reconciliation.
- Canonical JSON + sha256 content identifiers (sha256:hex) ensure deterministic hashing.
- CLI (`omb-cli`) for record / export / verify workflows.
- Optional Stripe integration stubs (checkout session, future usage reporting paths).
- High test coverage (97%) with strict lint (Ruff) & type checking (mypy).
- Publish-ready PyPI package (`omb-py`).

## Installation
```bash
pip install omb-py
```

Or clone for local development:
```bash
git clone https://github.com/Maverick0351a/omb.git
cd omb
python -m venv .venv
# Windows PowerShell:
. .venv/Scripts/Activate.ps1
pip install -e packages/omb_py[dev]
pip install -r services/omb_api/requirements.txt
```

## Quick Start (Library)
```python
from omb.signing import Ed25519Signer
from omb.meter import JSONLMeter, UsageIn
from omb.export import bundle_for

# (Generate once) create a key pair externally or via scripts/gen_keys.py
priv_b64 = "<base64url_ed25519_private_key>"
KID = "ed25519-<short-hash>"
signer = Ed25519Signer(priv_b64=priv_b64, kid=KID)
meter = JSONLMeter(signer=signer)

sur = meter.record(UsageIn(tenant_id="acme", resource="api.call", quantity=1))
print(sur.sur_cid, sur.sur_sig)

records = meter.list_for_tenant("acme")
bundle = bundle_for(records, "acme", signer)
print(bundle["bundle_cid"], bundle["bundle_sig"])
```

## CLI
```bash
# Record usage
OMB_PRIVATE_KEY_B64=... OMB_KID=... omb-cli record --tenant acme --resource api.call

# Export bundle
OMB_PRIVATE_KEY_B64=... OMB_KID=... omb-cli export --tenant acme > bundle.json

# Verify bundle
OMB_PRIVATE_KEY_B64=... OMB_KID=... omb-cli verify < bundle.json
```

## FastAPI Service
Run the reference API (after setting env vars `OMB_PRIVATE_KEY_B64`, `OMB_KID`):
```bash
uvicorn services.omb_api.main:app --host 127.0.0.1 --port 8095 --reload
```
Endpoints (selected):
- `POST /v1/meter` — record usage
- `GET /v1/usage/{tenant}/export` — export signed bundle
- `GET /.well-known/jwks.json` — JWKS with current public key
- `POST /v1/billing/stripe/checkout` — Stripe checkout stub

## Verification Model
For each usage record (SUR):
1. Build base dict excluding signature fields.
2. Compute `sur_cid = sha256(canonical_json(base))`.
3. Sign `message = f"{sur_cid}|{tenant_id}|{ts}"` with Ed25519 -> `sur_sig`.

For bundles:
1. Build `{tenant_id, exported_at, records:[...record dicts...]}`.
2. `bundle_cid = sha256(canonical_json(bundle_without_sig))`.
3. Sign `f"{bundle_cid}|{tenant_id}|{exported_at}"` -> `bundle_sig`.

Anyone with the public key can:
- Recompute each record CID and compare to `sur_cid`.
- Recompute bundle CID and verify `bundle_sig`.

## Configuration (Environment Variables)
| Variable | Purpose |
|----------|---------|
| OMB_PRIVATE_KEY_B64 | Base64url Ed25519 private key |
| OMB_KID | Key identifier (kid) |
| OMB_LOCAL_SUR_PATH | JSONL file path (default ./data/usage.jsonl) |
| OMB_STORE | `jsonl` (default) or `sqlite` |
| OMB_SQLITE_PATH | SQLite path when OMB_STORE=sqlite |
| OMB_RETENTION_MAX_AGE_SECONDS | Optional retention trim window |
| STRIPE_SECRET_KEY | Enable Stripe endpoints when set |
| STRIPE_PRICE_ID | Checkout price ID |

## Development
Quality gates:
```bash
python -m pytest -q --disable-warnings --cov=packages/omb_py/omb
python -m ruff check packages/omb_py/omb
python -m mypy packages/omb_py/omb
```

Version bump & release tagging:
```bash
python scripts/bump_version.py patch
# edit CHANGELOG.md
git commit -am "release: vX.Y.Z"
git tag omb-vX.Y.Z
git push --follow-tags origin main
```

## Roadmap
- 1.0: formal spec doc, multi-key rotation, stronger auth/rate limiting.
- Stripe usage aggregation & webhook signature verification.
- Additional storage backends (Postgres, S3 append logs).
- Benchmarks & async I/O path.

## Security
See `SECURITY.md`. Signatures are Ed25519 over deterministic canonical JSON; altering any field breaks verification.

## License
Apache-2.0

## Tags
`usage-metering` `billing` `ed25519` `cryptography` `signed-data` `content-addressed` `pydantic` `fastapi` `stripe` `cli` `python-library` `observability` `auditing`
