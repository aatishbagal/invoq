# Audit resolution note

Date: 2026-09-22. Housekeeping prompt: R.8.

This note records remediation of findings in the
[2026-09-17 codebase audit](invoq-audit-2026-09-17.md). It supplements the audit;
it is not a new security audit or a release approval.

## Reference documents

The three planning documents requested by the audit are already tracked at
their canonical paths, having been added in commit `04e87ba`:

- [Project specification](../specification.md)
- [Development prompts and version roadmaps](../development-prompts.md)
- [Literature review](../literature-review.md)

R.8 preserves their current contents byte-for-byte. No duplicate copies or
content revisions are needed. `docs/audits/` already exists. This closes the
missing-reference finding in section 2 and the restoration portion of next
step 5. The requested full roadmap comparison and re-audit remain follow-up
work; the planning documents are not evidence that planned features exist.

## Remediation mapping

| Prompt | Finding addressed and resolution | Implementation commits |
| --- | --- | --- |
| R.0 | Immediate execution exposure: default-on remediation mode requires manual approval for every allowed MCP command or script, including SAFE calls. This is containment, not closure of the classifier bypasses. Package version lookup also uses installed metadata without an invented version fallback. | `2f48302`, `d88f8b4`, `c4090d0` |
| R.1 | Critical SAFE-classification bypasses and direct writes: fail-closed parsing and argument policies reject embedded execution, expansions, unsupported syntax, and mutation bypasses; ordinary redirects require confirmation. Whole-script validation was added. | `75a4dd5`, `f57df3a` |
| R.2 | Critical registry execution bypass: typed capabilities route all execution tools through server-owned validation and confirmation; arbitrary Python handlers and direct registry execution are refused. | `407ee28`, `5f98c7b` |
| R.3 | High-risk mismatch between script validation and execution: scripts are restricted to independently validated, single-line literal commands joined by `&&`; arbitrary Bash constructs are rejected. | `9ab46cb` |
| R.4 | Unenforced input schemas: strict schemas validate every registered tool before dispatch, including aliases and edited commands, enforcing command/script length and file-line limits. | `7cabb90` |
| R.5 | Misleading execution configuration: unused settings are removed; legacy execution sections are rejected with migration guidance. No privilege-bypass feature is implemented. | `7a3bf90`, `8bdf278` |
| R.6 | Blocked-pattern and execution-path coverage gaps: adversarial regressions cover canonical blocks, obfuscations, audit bypasses, confirmation, edits, and MCP dispatch. Test dependencies and isolated CI runs are declared. | `19e6133`, `b74582c` |
| R.7 | Observable documentation drift: debug and extensions explicitly report that they are unimplemented; the ignored ask flag and default Git extension are removed; manual Ollama installation and intentional cross-platform metadata are documented and regression-tested. | `6355c9e`, `d1760a8`, `d18e1e7` |

The reported bypasses are addressed within the restricted execution contract;
this does not establish an OS sandbox or unrestricted shell safety. The
[tool capability policy](../security-tool-capabilities.md) records remaining
filesystem containment, resource, and disclosure gaps. The extension framework,
debug workflow, and released cross-platform execution support remain incomplete.
Broader setup, platform, and lifecycle coverage gaps require further review.

## Verification record

R.7 completed with 877 security tests and 907 full-suite tests passing, including
25 documentation-drift tests. R.8 changes only documentation and the required
patch-version metadata in `pyproject.toml`; no tests are rerun, as requested.
Existing tests and the three planning documents are unchanged by R.8.
