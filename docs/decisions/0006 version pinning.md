# ADR 0006 — Pin Dependency Versions in requirements.txt

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-05-30 |
| **Phase** | 5 (Baseline Build) — applied at first dependency add |
| **Related** | ADR 0002 (Stack selection) |

## Context

`requirements.txt` initially listed dependencies unpinned (`openai`, `pyyaml`, `python-dotenv`). Unpinned dependencies install whatever version the package index offers at install time. For a learning project this is convenient but creates two real risks as the project matures:

1. **Reproducibility breakdown.** A fresh checkout six months from now installs newer versions of the same packages. APIs may have changed; quality measurements taken today may not be reproducible on a future machine. The `AI_Delivery_Lifecycle.md` reproducibility principle says "every artifact regenerates from a script or a documented command" — unpinned dependencies violate this.

2. **Silent SDK drift.** Microsoft's deprecation of the classic AzureOpenAI client in favour of the OpenAI v1 endpoint (caught during W3 infrastructure setup) is exactly the shape of change unpinned dependencies make invisible until something breaks at the worst possible moment.

A new dependency (`chromadb`) is being added in Phase 5. This is the natural moment to commit to a version-management discipline.

## Decision

**Fully pin every direct dependency in `requirements.txt` using `==`.**

Current state:
```
chromadb==1.5.9
openai==2.38.0
python-dotenv==1.2.2
PyYAML==6.0.3
```

Each new install follows the same pattern:
1. `pip install <package>` (in active venv)
2. `pip freeze | grep -i "^<package>=="` to get the exact pinned line
3. Append to `requirements.txt`
4. Commit `requirements.txt` immediately

## Consequences

**Positive.**
- Reproducibility — a fresh checkout produces the same environment as today
- Drift detection — version updates become deliberate, documented events
- Safer upgrades — when a dependency is upgraded, the change is visible in a diff and can be tested
- Aligned with hardening discipline that Phase 7 will require anyway; doing it now means no late refactor

**Negative.**
- Slightly more friction at install time (must add the version line after each install)
- Transitive dependencies are still unpinned (only direct deps captured); a fully locked environment would require `pip-tools`, `poetry`, or `uv` — deferred until project scale justifies it
- Stale-version risk — pinned versions don't auto-receive security patches; periodic upgrade discipline required

## Revisit triggers

- **Phase 7 (Hardening).** Consider migrating to `uv` or `pip-tools` for full lock-file discipline including transitive dependencies. Required if delivering for regulated industries.
- **Quarterly upgrade pass.** Schedule a deliberate review of pinned versions; upgrade where safe, ADR major changes.
- **Security advisory.** Any CVE on a pinned dependency triggers immediate review and upgrade decision.

## Notes for the playbook

This decision is RAG-non-specific — applies to any AI delivery project. Worth promoting to the playbook's Phase 3 DoD as a generic check: *"All direct dependencies pinned in a deterministic format (`==` for pip, lock file for poetry/uv)."* Update `RAG_Solution_Delivery_Playbook.md` Phase 3 DoD in next revision.