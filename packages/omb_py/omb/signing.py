from __future__ import annotations
import base64, json, hashlib
from dataclasses import dataclass
from typing import Any, Dict
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

# --- helpers ---

def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def b64u_decode(data: str) -> bytes:
    # Strict validation: raise on invalid chars
    pad = '=' * (-len(data) % 4)
    raw = data + pad
    try:
        return base64.urlsafe_b64decode(raw.encode('utf-8'))
    except Exception as e:  # pragma: no cover - rarely triggered
        raise ValueError('invalid base64url input') from e

CANONICAL_JSON_SEPARATORS = (',', ':')

def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=CANONICAL_JSON_SEPARATORS, ensure_ascii=False).encode('utf-8')

def sha256_cid(data: bytes) -> str:
    return 'sha256:' + hashlib.sha256(data).hexdigest()

@dataclass
class Ed25519Signer:
    priv_b64: str
    kid: str

    def __post_init__(self):
        raw = b64u_decode(self.pr  iv_b64)  # type: ignore[attr-defined]
        if len(raw) != 32:
            raise ValueError('invalid private key length')
        self._sk = Ed25519PrivateKey.from_private_bytes(raw)
        self._vk = self._sk.public_key()

    @property
    def public_key_b64(self) -> str:
        return b64u(self._vk.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw))

    def sign(self, message: bytes) -> str:
        return b64u(self._sk.sign(message))

    def verify(self, message: bytes, sig_b64: str) -> bool:
        try:
            self._vk.verify(b64u_decode(sig_b64), message)
            return True
        except Exception:
            return False

    @property
    def jwk(self) -> Dict[str, str]:
        return {"kty": "OKP", "crv": "Ed25519", "x": self.public_key_b64, "kid": self.kid}

    @property
    def jwks(self) -> Dict[str, Any]:
        return {"keys": [self.jwk]}

def verify(pub_b64: str, message: bytes, sig_b64: str) -> bool:
    try:
        vk = Ed25519PublicKey.from_public_bytes(b64u_decode(pub_b64))
        vk.verify(b64u_decode(sig_b64), message)
        return True
    except Exception:
        return False
