# Copilot Usage Notes

This repo uses GitHub Copilot under the ODIN organization guidelines. Suggestions are reviewed for:

1. Security hygiene (no hardcoded secrets)
2. Licensing clarity (original or Apache-2 compatible)
3. Style consistency (PEP8 + Ruff rules)

Key commands / scripts:

- `scripts/gen_keys.py` – generate an Ed25519 keypair (base64url, unpadded)
- `scripts/bump_version.py <new_version>` – update version across package & changelog placeholder

CI enforces lint, type-check, tests, build, and (on release tags) publish.
