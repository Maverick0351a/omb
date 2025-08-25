from __future__ import annotations
import argparse, os, json
from .signing import Ed25519Signer, b64u_decode
from .meter import JSONLMeter, UsageIn, meter_for_env
from .export import bundle_for
from .verify import verify_bundle, verify_sur

# --- CLI helpers ---

def _signer_from_env() -> Ed25519Signer:
    priv = os.getenv("OMB_PRIVATE_KEY_B64")
    kid = os.getenv("OMB_KID")
    if not priv or not kid:
        print("Missing OMB_PRIVATE_KEY_B64 or OMB_KID in environment", flush=True)
        raise SystemExit(1)
    return Ed25519Signer(priv_b64=priv, kid=kid)

# --- commands ---

def cmd_record(args):
    signer = _signer_from_env()
    meter = meter_for_env(signer)
    usage = UsageIn(tenant_id=args.tenant, subject=args.subject, action=args.action, quantity=args.quantity, meta=json.loads(args.meta) if args.meta else None)
    sur = meter.record(usage)
    print(json.dumps(sur.model_dump(), indent=2))

def cmd_export(args):
    signer = _signer_from_env()
    meter = meter_for_env(signer)
    recs = meter.list_for_tenant(args.tenant, args.since, args.until)
    bundle = bundle_for(recs, args.tenant, signer)
    print(json.dumps(bundle, indent=2))

def cmd_verify(args):
    with open(args.path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if 'records' in data:
        ok = verify_bundle(data)
    else:
        ok = verify_sur(data)
    print("OK" if ok else "FAIL")
    raise SystemExit(0 if ok else 1)

def build_parser():
    p = argparse.ArgumentParser(prog='omb-cli')
    sub = p.add_subparsers(dest='cmd', required=True)

    p_rec = sub.add_parser('record', help='Record a usage event')
    p_rec.add_argument('--tenant', required=True)
    p_rec.add_argument('--subject', required=True)
    p_rec.add_argument('--action', required=True)
    p_rec.add_argument('--quantity', required=True, type=int)
    p_rec.add_argument('--meta', required=False, help='JSON string metadata')
    p_rec.set_defaults(func=cmd_record)

    p_exp = sub.add_parser('export', help='Export signed bundle')
    p_exp.add_argument('--tenant', required=True)
    p_exp.add_argument('--since', required=False)
    p_exp.add_argument('--until', required=False)
    p_exp.set_defaults(func=cmd_export)

    p_ver = sub.add_parser('verify', help='Verify a SUR or bundle JSON file')
    p_ver.add_argument('path')
    p_ver.set_defaults(func=cmd_verify)
    return p

def main(argv=None):  # pragma: no cover - tiny wrapper
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)

if __name__ == '__main__':  # pragma: no cover
    main()
