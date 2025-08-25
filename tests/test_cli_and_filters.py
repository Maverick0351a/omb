import os, json, subprocess, sys, tempfile, datetime, textwrap, pathlib
import pytest
from omb.signing import Ed25519Signer
from omb.meter import UsageIn, JSONLMeter
from omb.export import bundle_for

PRIV = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='
KID = 'kid123'

def test_cli_missing_env(tmp_path, monkeypatch):
    cmd = [sys.executable, '-m', 'omb.cli', 'record', '--tenant', 't1', '--subject', 's', '--action', 'a', '--quantity', '1']
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode != 0

def test_cli_roundtrip(tmp_path, monkeypatch):
    env = os.environ.copy()
    env['OMB_PRIVATE_KEY_B64'] = PRIV
    env['OMB_KID'] = KID
    env['OMB_LOCAL_SUR_PATH'] = str(tmp_path / 'usage.jsonl')
    subprocess.check_call([sys.executable, '-m', 'omb.cli', 'record', '--tenant', 't1', '--subject', 's', '--action', 'a', '--quantity', '1'], env=env)
    out = subprocess.check_output([sys.executable, '-m', 'omb.cli', 'export', '--tenant', 't1'], env=env, text=True)
    data = json.loads(out)
    assert 'records' in data

def test_cli_verify(tmp_path):
    env = os.environ.copy()
    env['OMB_PRIVATE_KEY_B64'] = PRIV
    env['OMB_KID'] = KID
    env['OMB_LOCAL_SUR_PATH'] = str(tmp_path / 'usage.jsonl')
    subprocess.check_call([sys.executable, '-m', 'omb.cli', 'record', '--tenant', 't1', '--subject', 's', '--action', 'a', '--quantity', '1'], env=env)
    bundle_json = subprocess.check_output([sys.executable, '-m', 'omb.cli', 'export', '--tenant', 't1'], env=env, text=True)
    path = tmp_path / 'bundle.json'
    path.write_text(bundle_json)
    subprocess.check_call([sys.executable, '-m', 'omb.cli', 'verify', str(path)], env=env)

def test_cli_verify_fail_exit(tmp_path):
    env = os.environ.copy()
    env['OMB_PRIVATE_KEY_B64'] = PRIV
    env['OMB_KID'] = KID
    env['OMB_LOCAL_SUR_PATH'] = str(tmp_path / 'usage.jsonl')
    subprocess.check_call([sys.executable, '-m', 'omb.cli', 'record', '--tenant', 't1', '--subject', 's', '--action', 'a', '--quantity', '1'], env=env)
    bundle_json = subprocess.check_output([sys.executable, '-m', 'omb.cli', 'export', '--tenant', 't1'], env=env, text=True)
    data = json.loads(bundle_json)
    data['records'][0]['quantity'] = 999
    bad_path = tmp_path / 'bad.json'
    bad_path.write_text(json.dumps(data))
    proc = subprocess.run([sys.executable, '-m', 'omb.cli', 'verify', str(bad_path)], env=env)
    assert proc.returncode != 0

def test_since_until_filters_jsonl(tmp_path):
    signer = Ed25519Signer(priv_b64=PRIV, kid=KID)
    meter = JSONLMeter(signer, path=tmp_path / 'usage.jsonl')
    now = datetime.datetime.now(datetime.timezone.utc)
    earlier = (now - datetime.timedelta(minutes=5)).isoformat()
    later = (now + datetime.timedelta(minutes=5)).isoformat()
    meter.record(UsageIn(tenant_id='t1', subject='s', action='a', quantity=1, ts=earlier))
    meter.record(UsageIn(tenant_id='t1', subject='s', action='a', quantity=1, ts=now.isoformat()))
    meter.record(UsageIn(tenant_id='t1', subject='s', action='a', quantity=1, ts=later))
    recs = meter.list_for_tenant('t1', since_iso=now.isoformat())
    assert len(recs) == 2
    recs2 = meter.list_for_tenant('t1', until_iso=now.isoformat())
    assert len(recs2) == 2
