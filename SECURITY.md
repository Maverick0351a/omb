# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Only the latest minor version receives security updates.

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | ✅ (latest)         |

## Reporting a Vulnerability

Please email security@odin.org with details. We will acknowledge receipt within 2 business days and provide a timeline for a fix after triage. If you require encrypted email, request our PGP key in your initial message.

## Security Design Notes

- Ed25519 signatures over canonical JSON avoid ambiguity and downgrade attacks.
- Canonical form uses UTF-8, sorted keys, compact separators (`,`, `:`) without whitespace.
- CIDs are prefixed with `sha256:` then lowercase hex of SHA-256 digest.
- SUR message format: `{sur_cid}|{tenant_id}|{ts}`
- Bundle message format: `{bundle_cid}|{tenant_id}|{exported_at}`
- Base64url is unpadded; decoder enforces strict validation (rejects invalid chars).
- Retention trimming is server-side only (no client-supplied deletion hints).
- SQLite backend optional; default JSONL append-only for auditability.
- Stripe integration is optional and behind environment configuration.

## Key Management

Rotate Ed25519 keys periodically. Publish new public keys via JWKS before rotating private keys out of service. Old keys should be retained until signatures they produced have aged out of all verification windows.

## Hardening Wishlist

- Key rotation helper CLI commands.
- Multi-signer verification (trust set) for bundles.
- Replay detection cache for SUR submissions (if client-signed events added later).
- Optional transparency log integration.
