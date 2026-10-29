# Independent Claude consultation
Round: 1

## User request
«сравни вот эту таблицу со всеми нашими данными. ты же их всех объединил? проанализируй эти данные, их статистику и биологические характеристики/значения. Сравни все это с данными от briford и https://github.com/lachrymator/openadmet-cyp-challenge-public. сделай большую сравнительную таблицу с графиками и тд».
The user provided chembl_CYP_final_ChEMBL_37.csv. Asked about schema/preparation script, user replied «Нет». Earlier campaign had distinct data/model combinations, not one global training table. No new training/submission requested.

## Authoritative context and constraints
Date2026-10-24, Moscow timezone. Workspace is CYP Inhibition; consultation root is its dedicated artifacts/data-comparison-20261024 directory. Read-only advisor, no compute launches, network publishing, source edits or arbitrary scientific success thresholds. Codex owns conclusions. Scope is a large comparative data workbook/report with figures; preserve uncertainty, adverse cases, source distinctions and exact counts. User has not authorized guessing y/task/bound/flag semantics.

## Current state
Analysis covers15 data views, including officialTRAIN/TEST/auxiliary tables, briford public raw snapshots and actually-used filtered subsets, Tox21 andBindingDB experiments, earlierJeremy external subsets, and userChEMBL37. Python independently normalizes structures with FragmentParent+Uncharger+SanitizeMol, stereo-preserving key and separate nonstereo parent, no tautomer canonicalization. Source rows, labels, exact normalizedstructures, parents andscaffolds are counted separately.

## Evidence and source map
- analyse.py: full analysis implementation; summary.json and quality.json: main computed facts and limitations.
- tables/dataset_comparison.csv, pairwise_overlap.csv: per-source dimensions and overlap.
- tables/user_target_task_relation.csv, user_flags.csv, chemical_statistics.csv: label and chemistry distributions.
- tables/paired_activity_statistics.csv: matched user numeric y vs existing source numeric values, bytask andCYP, bothstereo andparentidentity.
- tables/test_similarity_summary.csv, test_coverage_increment.csv: all750TEST queries, exhaustive Morgan2048/radius2 comparison. Different referencepool sizes explicitly disclosed.
- sources/lachrymator-README.md and lachrymator-tree.json: pinned repository6afb664e6fb22c516952e020273ba91442f426db. Write-up andfiguresonly, no molecule table ortrainingcode.
- sources/briford-blog.html and prior briford source snapshots in /Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023/reference_audit: liveauthorclaims vs actual archivedinputfiles. Blog currently says24918ChEMBLskeletons and16546Veithcompounds; our normalization of archived rawfiles gives24925 and16132parents. Report must not conflate source snapshots/normalization or pretend an exact private-training reproduction.
- sources/uniprot-summary.json: fresh officialaccession/gene/humanorganism confirmation.
- sources/paper-27063220.txt: retrieved originalPubMedmetadata/abstract. FullPMC browser access failed CAPTCHA; do notpretend fullpaperread.
- ChEMBL primaryFAQ: https://chembl.gitbook.io/chembl-interface-documentation/frequently-asked-questions/chembl-data-questions . Specifies pChEMBL=-logM for multiple endpoints, only equalitypoints, and PubChem integration includingAID1851.

## Work already performed
Current v2analysis completed,15views,66117unique rawSMILES, one unparsable sourceSMILES. v1had aRingInfo initialization defect on481acyclic parentfragments; repaired withChem.SanitizeMol beforeMurcko/descriptors andreran allanalysis. No userstructures invalid; suppliedInChIKeys match RDKitrawInChIKeys exactly. Nine vectorPDF/SVGfigures created; visualQA/workbookauthoring stillongoing. No modeltraining, liveleaderboardquery orsubmission inthis task.

## Questions for independent assessment
1. Which biological/data-comparison conclusions are supported by these files, and which claims require missing metadata or different evidence?
2. What materially affects the interpretation of new information versus duplicated chemistry/labels and TEST neighbourhood coverage?
3. What should the comparative table explicitly distinguish to make it useful for choosing a future training dataset?

## Known missing or inaccessible information
No user preparationcode, units/aggregation definitions, originalassayIDs orprotocol metadata. any_preinc is a providedflag, notverified TDI. Lachrymator molecule/table/splits unavailable fromrepo; exactoverlaps cannot be computed. Historicbriford modelweights/OOFunavailable. This is descriptive census, not a newlytrainedmodel comparison orproof of prospective performance.

## Codex position
withheld for independent first-round assessment.

## Confidentiality check
No secrets,credentials,privatekeys,.envcontents or unnecessary personalinformation inthis brief. Filepaths are scoped to relevant research evidence.
