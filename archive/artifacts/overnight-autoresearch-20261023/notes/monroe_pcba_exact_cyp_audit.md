# Monroe PCBA: exact challenge-CYP provenance audit

Broad regex counts334TRAIN/25TEST overstate exposure to the four challenge enzymes. Actual nonmissing binary labels in inhibition-oriented CYP2C9/2D6/3A4 assays overlap139TRAIN compounds by exact InChI,35 of own750,8 of briford529, and4 actualTEST compounds. Conservative exact-or-parent counts are225/51/14/4. This confirms rawPCBA domain-label intersections; it does not prove those rows or heads were used by the published checkpoint.

All input files below were checked against the completed audit hashes. Classification uses saved primary PubChem descriptions, target accessions and, for ambiguous records, full protocol/comments. The analysis read all1332 returned assay descriptions and reviewed the42 broad matches; a separate scan of target accessions found exactly the seven single-isoform challenge-enzyme assays below. No network mutation, model fit or live source edit occurred.

## Assay identity and necessary retention filters

All eight relevant columns satisfy raw counts≥100positive,≥100negative,≥1000total. None can be declared impossible to retain under these necessary thresholds. Their presence among the final1089 heads remains unknown; passing on all raw rows is not sufficient after train splitting and exclusions.

| AID | Interpretation | Positive | Negative | Total | Retention |
|---|---|---:|---:|---:|---|
| [410](https://pubchem.ncbi.nlm.nih.gov/bioassay/410) | CYP1A2 activity; direction-qualified | 4176 | 3613 | 7789 | Possible, unconfirmed |
| [777](https://pubchem.ncbi.nlm.nih.gov/bioassay/777) | CYP2C9 inhibition | 18730 | 77128 | 95858 | Possible, unconfirmed |
| [883](https://pubchem.ncbi.nlm.nih.gov/bioassay/883) | CYP2C9 inhibition/substrate | 1273 | 6885 | 8158 | Possible, unconfirmed |
| [884](https://pubchem.ncbi.nlm.nih.gov/bioassay/884) | CYP3A4 inhibition/substrate | 3439 | 7039 | 10478 | Possible, unconfirmed |
| [891](https://pubchem.ncbi.nlm.nih.gov/bioassay/891) | CYP2D6 inhibition/substrate | 1623 | 6265 | 7888 | Possible, unconfirmed |
| [885](https://pubchem.ncbi.nlm.nih.gov/bioassay/885) | CYP3A4 activation | 165 | 12687 | 12852 | Possible, unconfirmed |
| [1024](https://pubchem.ncbi.nlm.nih.gov/bioassay/1024) | CYP2C9 activation; title discrepancy | 1368 | 94490 | 95858 | Possible, unconfirmed |
| [1851](https://pubchem.ncbi.nlm.nih.gov/bioassay/1851) | Five-CYP panel; isoform unresolved | 6700 | 9844 | 16544 | Possible, unconfirmed |

- AID410 uses human CYP1A2 and furafylline inhibition normalization, but the original assay has an Activity Direction field absent from PCBA. Treat it as same-enzyme activity rather than asserting every positive is an inhibitor.
- AIDs883/884/891 can respond to inhibitors and competing substrates. Their binary outcomes are relevant enzyme activity labels, not the challenge quantitative pIC50 measurements.
- AID1024 says2A9 in the title; targetNP_000762.2, reagent list, protocol and activity criterion explicitly identify2C9 activation. The title discrepancy is retained in the audit.
- AID1851 covers1A2/2C9/2C19/2D6/3A4; its single PCBA column omits PanelID and PanelTarget. No isoform-specific outcome is inferred.

## Nonmissing label overlaps for potentially retained inhibitory assays

GroupAIDs777/883/884/891. Counts are unique official compounds with an actual finite0/1 PCBA label; missing labels never count as negatives. Adding410 does not add any compounds to this union.

| Population | Exact InChI | Normalized parent | Either relation |
|---|---:|---:|---:|
| officialTRAIN | 139 | 222 | 225 |
| own750 | 35 | 51 | 51 |
| briford529 | 8 | 14 | 14 |
| actualTEST | 4 | 4 | 4 |

Including activation assays885/1024 and panel1851 yields:

| Population | Exact InChI | Normalized parent | Either relation |
|---|---:|---:|---:|
| officialTRAIN | 146 | 230 | 233 |
| own750 | 36 | 54 | 54 |
| briford529 | 9 | 15 | 15 |
| actualTEST | 4 | 4 | 4 |

Exact and parent sets are not necessarily nested: standard InChI can equate tautomers, while the parent key used here does not canonicalize tautomers. Parent matching also removes salts/charge/stereochemistry. Seventeen compounds have differing0/1 labels across these looser parent matches; no conflict occurs for exact-InChI matches in the eight relevant assays.

## Where the same official endpoint is actually measured

For strictAIDs777/883/884/891 and observed challenge labels for that same CYP, own750 has24exact compounds/29target-pairs, or36exact-or-parent compounds/44pairs; briford529 has8exact compounds/9pairs, or12exact-or-parent compounds/14pairs. Including410 yields25/34 and39/52 on own750;8/9 and13/16 on briford529. Thus a raw activity overlap does not automatically mean its corresponding challenge endpoint contributes to evaluation. ActualTEST endpoints are blinded.

## Four actualTEST exact matches

| Official ID | CYP2C9 inhibition777 | CYP2C9 activation1024 | Five-CYP panel1851 | PCBA row |
|---|---:|---:|---:|---:|
| OCNT-0496981 | 1.0 | 0.0 | 1.0 | 1418377 |
| OCNT-2461740 | 1.0 | 0.0 | missing | 954835 |
| OCNT-2535626 | 0.0 | 0.0 | missing | 681949 |
| OCNT-2535776 | 1.0 | 0.0 | missing | 554124 |

## Broad matches excluded from the challenge-enzyme counts

- OtherP450s:778/899 are CYP2C19;743083/743139 are aromatase/CYP19A1. They are biologically related but different targets.
- Sixteen assays measure nuclear-receptor signaling/promoter reporters or viability counter-screens (CAR,PXR,AHR,SF1,LRH1,DAF12), not isolated challenge-CYP catalytic activity.
- Fourteen other matches are G6PD/AChE counterscreens, cytochrome-c or other non-P450 background/reagents, cyclophilinCyP-40, or the CypHer dye. EachAID and classification rationale is retained in the JSON.

## Eligibility evidence and remaining uncertainty

The smaller counts do not establish clean supervised pretraining. Even the strict inhibitory group retains4exact actualTEST matches and35/8exact matches in the two evaluated holdouts. However, historical checkpoint exposure is unresolved: the exact1089-head list, actual benchmark exclusions, historical hash split/version, InChI dedup survivor and graph-construction survivors are not published. The correct statement is potential same-enzyme supervised exposure in the raw pretraining source, not proven leakage of challenge pIC50 labels. Keep Monroe explicitly qualified unless that membership uncertainty is resolved.

Detailed machine-readable evidence: [monroe_pcba_exact_cyp_audit.json](/Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023/notes/monroe_pcba_exact_cyp_audit.json); matched IDs, outcomes and raw-row pointers: [monroe_pcba_exact_cyp_matches.csv](/Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023/notes/monroe_pcba_exact_cyp_matches.csv).
Frozen cohort SHA256: `eee1078503c7793f8f1c1fcc788dd4db9225a6d682202930f9bb972bbe6bd82a`. Matched-row gzip SHA256: `eb9b26bb677a2503a84950d51e9e0fea1e90155c69af82ed72e8ca765ced841f`. Full input hashes are in the JSON.
