import base64, os, secrets

def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip('=')

priv = secrets.token_bytes(32)
print('Set these environment variables:')
print('  OMB_PRIVATE_KEY_B64=' + b64u(priv))
print('  OMB_KID=' + b64u(secrets.token_bytes(8)))
