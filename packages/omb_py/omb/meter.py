from __future__ import annotations
import os, json, datetime, hashlib, sqlite3, logging
from dataclasses import dataclass
from typing import Optional, List, Iterable, Any
from pydantic import BaseModel, Field, ConfigDict, validator
from .signing import canonical_json, sha256_cid, b64u

log = logging.getLogger("omb.meter")

CANONICAL_JSON_SEPARATORS = (',', ':')

class UsageIn(BaseModel):
    tenant_id: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    action: str = Field(min_length=1)
    quantity: int = Field(gt=0)
    ts: Optional[str] = Field(default=None, description="ISO8601 timestamp; if absent server uses now")
    meta: Optional[dict] = None

class SignedUsageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cid: str
    tenant_id: str
    subject: str
    action: str
    quantity: int
    ts: str
    meta: Optional[dict] = None
    sur_sig: str
    kid: str

    @validator('cid')
    def _cid_prefix(cls, v):  # noqa: N805
        if not v.startswith('sha256:'):
            raise ValueError('cid must start with sha256:')
        return v

# --- JSONL backend ---

@dataclass
class JSONLMeter:
    signer: Any
    path: str = "usage.jsonl"

    def record(self, usage: UsageIn) -> SignedUsageRecord:
        now = datetime.datetime.now(datetime.timezone.utc)
        ts = usage.ts or now.isoformat()
        body = {
            "tenant_id": usage.tenant_id,
            "subject": usage.subject,
            "action": usage.action,
            "quantity": usage.quantity,
            "ts": ts,
        }
        if usage.meta is not None:
            body["meta"] = usage.meta
        cid = sha256_cid(canonical_json(body))
        msg = f"{cid}|{usage.tenant_id}|{ts}".encode("utf-8")
        sig = self.signer.sign(msg)
        sur = {"cid": cid, **body, "sur_sig": sig, "kid": self.signer.kid}
        try:
            with open(self.path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(sur, separators=CANONICAL_JSON_SEPARATORS, sort_keys=True) + '\n')
        except Exception as e:  # pragma: no cover - disk errors rare
            log.warning("persistence failure: %s", e)
        return SignedUsageRecord(**sur)

    def list_for_tenant(self, tenant_id: str, since_iso: Optional[str] = None, until_iso: Optional[str] = None) -> List[SignedUsageRecord]:
        out: List[SignedUsageRecord] = []
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except Exception:
                        log.debug("skip malformed json line")
                        continue
                    if data.get('tenant_id') != tenant_id:
                        continue
                    ts = data.get('ts')
                    if since_iso and ts < since_iso:
                        continue
                    if until_iso and ts > until_iso:
                        continue
                    try:
                        out.append(SignedUsageRecord(**data))
                    except Exception:
                        log.debug("skip malformed record object")
        except FileNotFoundError:
            pass
        return out

# --- SQLite backend (optional) ---

class SQLiteMeter:
    def __init__(self, signer: Any, path: str = "usage.sqlite"):
        self.signer = signer
        self.path = path
        self._ensure()

    def _ensure(self):
        conn = sqlite3.connect(self.path)
        try:
            conn.execute("CREATE TABLE IF NOT EXISTS usage (tenant_id TEXT, subject TEXT, action TEXT, quantity INTEGER, ts TEXT, meta TEXT, cid TEXT, sur_sig TEXT, kid TEXT)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_tenant_ts ON usage(tenant_id, ts)")
            conn.commit()
        finally:
            conn.close()

    def record(self, usage: UsageIn) -> SignedUsageRecord:
        now = datetime.datetime.now(datetime.timezone.utc)
        ts = usage.ts or now.isoformat()
        body = {
            "tenant_id": usage.tenant_id,
            "subject": usage.subject,
            "action": usage.action,
            "quantity": usage.quantity,
            "ts": ts,
        }
        if usage.meta is not None:
            body["meta"] = usage.meta
        cid = sha256_cid(canonical_json(body))
        msg = f"{cid}|{usage.tenant_id}|{ts}".encode("utf-8")
        sig = self.signer.sign(msg)
        sur = {"cid": cid, **body, "sur_sig": sig, "kid": self.signer.kid}
        conn = sqlite3.connect(self.path)
        try:
            conn.execute("INSERT INTO usage VALUES (?,?,?,?,?,?,?,?,?)", (
                usage.tenant_id, usage.subject, usage.action, usage.quantity, ts, json.dumps(usage.meta) if usage.meta is not None else None, cid, sig, self.signer.kid
            ))
            conn.commit()
        finally:
            conn.close()
        return SignedUsageRecord(**sur)

    def list_for_tenant(self, tenant_id: str, since_iso: Optional[str] = None, until_iso: Optional[str] = None) -> List[SignedUsageRecord]:
        conn = sqlite3.connect(self.path)
        try:
            q = "SELECT cid, tenant_id, subject, action, quantity, ts, meta, sur_sig, kid FROM usage WHERE tenant_id=?"
            params: list[Any] = [tenant_id]
            if since_iso:
                q += " AND ts>=?"
                params.append(since_iso)
            if until_iso:
                q += " AND ts<=?"
                params.append(until_iso)
            q += " ORDER BY ts"
            out: List[SignedUsageRecord] = []
            for row in conn.execute(q, params):
                meta_raw = row[6]
                meta = json.loads(meta_raw) if meta_raw else None
                out.append(SignedUsageRecord(
                    cid=row[0], tenant_id=row[1], subject=row[2], action=row[3], quantity=row[4], ts=row[5], meta=meta, sur_sig=row[7], kid=row[8]
                ))
            return out
        finally:
            conn.close()

# --- factory ---

def meter_for_env(signer: Any):
    backend = os.getenv("OMB_STORE", "jsonl").lower()
    if backend == "sqlite":
        return SQLiteMeter(signer, os.getenv("OMB_SQLITE_PATH", "usage.sqlite"))
    return JSONLMeter(signer, os.getenv("OMB_LOCAL_SUR_PATH", "usage.jsonl"))
