# Exact N service-rejection evidence — pending parent review

The requested SMILES `N`, request ID `8ce86a6ae65d3692e7305e2c58ac62eebd97d3d943e093f577da25c36988246b`, received the literal **`Invalid Molecule` in all120 raw endpoints**. Returned service SMILES is also `N`. Its120 base numeric values are blank, and every corresponding categorical rejection indicator equals1.0. This is a documented terminal service outcome, not a successful numeric prediction and not a reason to resubmit or impute values. Lack of carbon is not used as a validity rule.

The source response is in the frozen27,060-outcome manifest at `chemistry-audit/incremental-20261026T043702Z/collection-manifest.json`. Exact immutable shard:

`/Users/adeliyaleleytner/Downloads/ADMETlab-Chrome-direct-500/probes/shifter-continuous-20261026T004048-0140/run/batches/001/result.csv`

SHA256: `570cbbb354ea8dd2dbec26f9d3e544859f72b1c9ef69c9dda3ff5e322311b710`.

The shard hash was verified and its exact row retained. A single stable newer28,560-outcome numeric snapshot was read and its complete feature-file SHA checked; only N's row and that manifest were saved. This confirms actual flags, not merely what conversion should produce. `evidence/N-source-evidence.json` binds raw row/shard, numeric row/file, manifests and source ID map. The original shard copy and exact raw/feature row CSVs are included.

Aliases are `VEITH-QGZKDVFQNNGYKY` in `union18` and `2d6isoform6`. There are no official training or test aliases. The request already belongs to the approved28-request original-source quarantine: earlier source work showed that two Pt/Ru substance records were collapsed to this ammonia representation. Source-supervision disposition and service outcome remain distinct facts.

This candidate adds only the observed N rejection to the existing Cl rejection. The separate Sb feature-identity exclusion is unchanged. Thus the proposed exact outcome policy contains **two terminal rejections and one numeric-but-unresolved graph**; the fresh matched full-pool exclusion union remains **29 unique requests**, and official affected rows remain zero. No rejection is inferred for any other carbon-free or unusual-element structure.

All previously approved policy, rejection, binding and audit files were preserved. Their existing hashes still match the frozen bindings. Copies of the unchanged audit code/schema live under `final-output-audit-v2/`; its schema/version remains `final-output-v2`. The new candidate policy has `approval_status=pending_parent_review`, and its wrapper's `policy_sha256` is deliberately **null**, so it cannot pass as approved. Parent review must precede promotion or final-agent consumption. Further actual exceptions may be batched into a new reviewed final policy when acquisition finishes; do not overwrite old experiment-bound files.

Four focused checks passed: old policy rejects unlisted N; the candidate recognizes exact N as rejected and ineligible, not numeric; altered raw evidence fails; incorrect category flags fail. Core audit code and endpoint schema are unchanged. `focused-checks.json` records these results. No collector changes, requests, training or full-completion claims were made.
