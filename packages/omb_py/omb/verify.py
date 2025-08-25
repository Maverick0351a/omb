from __future__ import annotations
from typing import Dict, Any
from .signing import canonical_json, sha256_cid, verify as verify_sig

def verify_sur(sur: Dict[str, Any]) -> bool:
    body = {k: sur[k] for k in ["tenant_id", "subject", "action", "quantity", "ts"] if k in sur}
    if "meta" in sur:
        body["meta"] = sur["meta"]
    expected_cid = sha256_cid(canonical_json(body))
    if expected_cid != sur.get("cid"):
        return False
    msg = f"{sur['cid']}|{sur['tenant_id']}|{sur['ts']}".encode('utf-8')
    return verify_sig(sur.get("kid", ""), msg, sur.get("sur_sig", "")) if sur.get("kid") else True

def verify_bundle(bundle: Dict[str, Any]) -> bool:
    recs = bundle.get("records")
    if not isinstance(recs, list):
        return False
    if any(not verify_sur(r) for r in recs):
        return False
    body = {"records": recs, "tenant_id": bundle.get("tenant_id"), "exported_at": bundle.get("exported_at")}
    cid = sha256_cid(canonical_json(body))
    if cid != bundle.get("cid"):
        return False
    msg = f"{cid}|{body['tenant_id']}|{body['exported_at']}".encode('utf-8')
    return verify_sig(bundle.get("kid", ""), msg, bundle.get("sig", ""))
