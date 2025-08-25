from __future__ import annotations
import datetime, json
from typing import List, Dict, Any
from .signing import canonical_json, sha256_cid
from .meter import SignedUsageRecord

CANONICAL_JSON_SEPARATORS = (',', ':')

def bundle_for(records: List[SignedUsageRecord], tenant_id: str, signer) -> Dict[str, Any]:
    recs = [r.model_dump() for r in records]
    body = {"records": recs, "tenant_id": tenant_id, "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    cid = sha256_cid(canonical_json(body))
    sig = signer.sign(f"{cid}|{tenant_id}|{body['exported_at']}".encode('utf-8'))
    return body | {"cid": cid, "sig": sig, "kid": signer.kid}
