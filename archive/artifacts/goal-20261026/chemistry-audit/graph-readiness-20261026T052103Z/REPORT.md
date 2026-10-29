# Readiness scan: frozen30,860 outcomes, not final acquisition

The stable2026-10-26 05:19:17UTC snapshot has30,860 of32,421 requested outcomes, with1,561 still pending at that time. Both complete raw and numeric files were frozen and SHA-verified against the manifest. The approved Cl/N/Sb policy and exact bindings were verified. No API requests, model runs or rentals were made.

**There are zero exact isomeric collision groups among requests and zero among sanitizable returned structures.** All requests and rows remain separate. There is one new, valid-but-different returned graph outside the current conservative gate. All4,905 official training and750 official blinded-test inputs remain finite and chemistry-eligible; the new case is external-only.

The gate reports two terminal service rejections (Cl,N), one reviewed numeric-but-unresolved Sb structure, and30,857 other numeric rows. Of those,30,856 currently pass chemistry eligibility; one requires the exact review below. The strict relations are30,843 identical isomeric graphs,10 ordinary charge/protonation normalizations,3 functional-group normalizations, the reviewed Sb exception, two non-predicted rejections and this new proton-placement difference. There are53 literal SMILES differences, which are not automatically chemical differences. No additional gate/numeric/probability/alert/MW issue was found.

## Exact internal proton-transfer case

Request ID `c144a5ae385f54b47f0a911da7ebb3ae9830ac594eb61a8654cf52535823ae26`, alias `VEITH-TYCFVQWEOAKDSC` in `union18` and `2d6isoform6`:

- Requested: `[N-]=[NH+]N=CC(=O)c1c[nH]c(=O)[nH]c1=O`
- Returned: `N=NN=CC(=O)c1c[nH]c(=O)[nH]c1=O`

Both structures sanitize, are closed-shell, and have formulaC6H5N5O3,14heavy atoms,5hydrogens, net charge0 and exact mass195.03923902. An explicit atom-index bijection i→i verifies every heavy-atom bond, bond order, aromatic flag, element, isotope and encoded stereochemical property is unchanged. Neither input encodes atom or double-bond stereochemistry. Only two atoms change: terminal atom0 gains one H and changes charge−1→0; central atom1 loses one H and changes charge+1→0. This is an internal proton transfer neutralizing a charge pair, not atom loss, a stereochemical inversion or an invalid returned graph.

The two isomeric graphs and standard InChI keys are nevertheless different. Default Normalize, Reionize, Uncharger and ChargeParent do not equate them. Strict stereo-preserving tautomer enumeration completes for each (12states) and retains different canonical forms. Therefore the current gate correctly does not silently equate them.

The saved source record (SID4252875/CID3246134, five Veith assay rows) has original azido SMILES `C1=C(C(=O)NC(=O)N1)C(=O)CN=[N+]=[N-]`. Its completed33-state RDKit enumeration chooses the requested representation. This establishes the recorded upstream representation path; it does not prove the dominant physical microstate or actual assay-species interconversion. No live database call was made.

## Proposed disposition, pending parent review

I recommend a **narrowly bound, explicitly recorded proton-transfer standardization for feature use**. This is defensible under the existing policy allowing documented service-standardized graphs: the feature convention changes only proton/charge placement, preserves the entire heavy-atom graph and encoded stereo, and yields a valid closed-shell graph with the same composition. Do not describe the two strings as identical molecular graphs or claim verified physical equilibrium. The remaining physical/source-species uncertainty is retained in the proof.

The proposal must bind this one request ID, exact requested/returned strings, exact atom changes and raw-rowSHA `23581c841427c031deba5ce32c6a08315519a42ef5eb22ea0e6fdd47a0f49646`. It should preserve all numeric, probability, MW, formal-charge and alert-index checks. It must not introduce a general forced-neutralization rule, merge rows, rewrite source molecules, or approve other tautomers/protomers. The source-supervision quarantine is unchanged. If parent review accepts this convention, this row can become feature-eligible without adding it to the exclusion union; otherwise the existing gate remains blocked for it rather than silently approving it.

Exact evidence: `proton-transfer-case/exact-graph-proof.json`, `exact-transformation-proposal.json` and `saved-source-rows.csv`. The source/member IDs have no official aliases or frozen own750/briford529 heldout IDs. Canonical collision evidence remains empty. No policy, binding, auditor, collector or training data was changed by this scan.

`summary.json`, `graph-ledger.csv`, `graph-differences.csv`, `unlisted-issues.csv` and exact raw/feature issue rows retain the complete result. This is a readiness check on one immutable partial snapshot; the final32,421-outcome audit remains required.
