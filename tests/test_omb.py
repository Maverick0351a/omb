import json, os, tempfile, datetime
from omb.signing import Ed25519Signer, canonical_json, sha256_cid, verify
from omb.meter import UsageIn, JSONLMeter, meter_for_env
from omb.export import bundle_for
from omb.verify import verify_bundle

PRIV = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='  # 32 zero bytes base64url
KID = 'kid123'

def test_sign_and_verify_sur(tmp_path):
    signer = Ed25519Signer(priv_b64=PRIV, kid=KID)
    meter = JSONLMeter(signer, path=tmp_path / 'usage.jsonl')
    sur = meter.record(UsageIn(tenant_id='t1', subject='s', action='a', quantity=1))
    body = {k: getattr(sur, k) for k in ['tenant_id','subject','action','quantity','ts']}
    cid = sha256_cid(canonical_json(body))
    assert cid == sur.cid
    msg = f"{cid}|{sur.tenant_id}|{sur.ts}".encode()
    assert signer.verify(msg, sur.sur_sig)

def test_bundle_roundtrip(tmp_path):
    signer = Ed25519Signer(priv_b64=PRIV, kid=KID)
    meter = JSONLMeter(signer, path=tmp_path / 'usage.jsonl')
    for i in range(3):
        meter.record(UsageIn(tenant_id='t1', subject='s', action='a', quantity=1))
    records = meter.list_for_tenant('t1')
    bundle = bundle_for(records, 't1', signer)
    assert verify_bundle(bundle)

def test_time_filters(tmp_path):
    signer = Ed25519Signer(priv_b64=PRIV, kid=KID)
    meter = JSONLMeter(signer, path=tmp_path / 'usage.jsonl')
    now = datetime.datetime.now(datetime.timezone.utc)
    early = (now - datetime.timedelta(minutes=10)).isoformat()
    late = (now + datetime.timedelta(minutes=10)).isoformat()
    meter.record(UsageIn(tenant_id='t1', subject='s', action='a', quantity=1, ts=early))
    meter.record(UsageIn(tenant_id='t1', subject='s', action='a', quantity=1, ts=now.isoformat()))
    meter.record(UsageIn(tenant_id='t1', subject='s', action='a', quantity=1, ts=late))
    res = meter.list_for_tenant('t1', since_iso=now.isoformat())
    assert len(res) == 2
    res2 = meter.list_for_tenant('t1', until_iso=now.isoformat())
    assert len(res2) == 2
