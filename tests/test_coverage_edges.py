import os, json, tempfile, datetime, io, sys
import pytest
from omb.signing import Ed25519Signer, b64u, b64u_decode
from omb.meter import UsageIn, JSONLMeter, meter_for_env
from omb.export import bundle_for
from omb.verify import verify_bundle, verify_sur

PRIV = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='
KID = 'kid123'

def test_invalid_b64_decode():
    with pytest.raises(ValueError):
        b64u_decode('@@@')

def test_malformed_json_line(tmp_path):
    signer = Ed25519Signer(priv_b64=PRIV, kid=KID)
    path = tmp_path / 'usage.jsonl'
    with open(path, 'w', encoding='utf-8') as f:
        f.write('{bad json}\n')
    meter = JSONLMeter(signer, path=path)
    assert meter.list_for_tenant('x') == []

def test_naive_timestamp(tmp_path):
    signer = Ed25519Signer(priv_b64=PRIV, kid=KID)
    meter = JSONLMeter(signer, path=tmp_path / 'usage.jsonl')
    naive_ts = datetime.datetime.utcnow().isoformat()  # naive
    sur = meter.record(UsageIn(tenant_id='t1', subject='s', action='a', quantity=1, ts=naive_ts))
    assert sur.ts == naive_ts

def test_persistence_failure(monkeypatch, tmp_path):
    signer = Ed25519Signer(priv_b64=PRIV, kid=KID)
    meter = JSONLMeter(signer, path=tmp_path / 'usage.jsonl')
    def bad_open(*a, **k):
        raise IOError('disk full')
    monkeypatch.setattr('builtins.open', bad_open)
    sur = meter.record(UsageIn(tenant_id='t1', subject='s', action='a', quantity=1))
    assert sur.cid.startswith('sha256:')

def test_verify_failures(tmp_path):
    signer = Ed25519Signer(priv_b64=PRIV, kid=KID)
    meter = JSONLMeter(signer, path=tmp_path / 'usage.jsonl')
    sur = meter.record(UsageIn(tenant_id='t1', subject='s', action='a', quantity=1))
    data = sur.model_dump()
    data['cid'] = 'sha256:deadbeef'
    assert not verify_sur(data)

def test_bundle_tamper(tmp_path):
    signer = Ed25519Signer(priv_b64=PRIV, kid=KID)
    meter = JSONLMeter(signer, path=tmp_path / 'usage.jsonl')
    meter.record(UsageIn(tenant_id='t1', subject='s', action='a', quantity=1))
    recs = meter.list_for_tenant('t1')
    bundle = bundle_for(recs, 't1', signer)
    bundle['records'][0]['quantity'] = 999
    assert not verify_bundle(bundle)
