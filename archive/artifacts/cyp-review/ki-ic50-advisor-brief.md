# Independent Claude consultation

Round: 1

## User request

а как аппроксимировать Ki к IC50 или наоборот для этой задачи? у нас так будет больше данных

Prior context: user wants a simple sequential Russian explanation and competitive strategy for OpenADMET CYP Direct Inhibition. She has asked about pIC50, interval-aware ST-RAE, auxiliary assays, external data and ESM. No models trained or external-data curation performed. Prior consultation concerned ESM, not Ki conversion.

## Authoritative context and constraints

2026-10-23 Europe/Moscow, current CYP Inhibition workspace. Deadline Nov 3. Advisory question; no compute, publication or submission. Use user's independent-advice protocol. Please keep this consultation narrow and brief, rely on supplied primary evidence and read-only files; no broad literature search needed.

## Current state

Four fixed human CYP endpoints (1A2,2C9,2D6,3A4). Main train 4905 compounds and 6525 observed pIC50 cells, with experimental credible intervals; hidden outcomes for 750 test compounds. Scorer is interval-distance L1 normalized by the same error of evaluated-set mean, macro-averaged over targets. Missing intervals need not prevent using external labels in a different training objective. Single-dose file concentration 49.5 uM refers to TEST INHIBITOR, not probe substrate.

## Evidence and source map

- sources/dataset_README.md; sources/tutorial_evaluation_custom_scoring_functions.py and sources/config.py for task.
- Official assay announcement https://openadmet.ghost.io/announcing-openadmets-cyp-inhibition-blind-challenge/ names CYP3A4 DBOMF; CYP1A2/2C9 EOMCC; CYP2D6 dextromethorphan with Echo-MS parent depletion. Direct arm preincubation lacks NADPH, TDI arm has NADPH. Recombinant biochemical assays. Actual substrate concentrations, matched Km, depletion and inhibition mechanism per molecule have not been established from inspected materials. Manufacturer defaults must not be assumed to match the scaled assay.
- Primary original research Jang et al. Nat Commun 2025 https://pmc.ncbi.nlm.nih.gov/articles/PMC12141731/ DOI 10.1038/s41467-025-60468-z, Results Eqs 1-2: initial-rate mixed inhibition has v=Vmax*S/[Km*(1+I/Kic)+S*(1+I/Kiu)], and 1/IC50=[Km/(Km+S)]/Kic + [S/(Km+S)]/Kiu. Classical competitive limit yields IC50=Ki*(1+S/Km). Paper discusses mechanism/parameter identifiability, including CYP3A4 examples. Relevant results and assumptions inspected, not a systematic full-paper audit.
- Primary CYP retrospective study DOI 10.1124/dmd.115.066597, title 'The Reliability of Estimating Ki Values for Direct, Reversible Inhibition of Cytochrome P450 Enzymes from Corresponding IC50 Values: A Retrospective Analysis of 343 Experiments'. Publisher abstract https://dmd.aspetjournals.org/article/S0090-9556%2824%2910221-8/abstract states tested Ki=IC50/2 under S=Km, short 5-min incubation, HLM <=0.1 mg/ml to limit depletion, metabolism-dependent inhibition and nonspecific binding. Full-text access 403; do not infer results not in abstract.
- Assay Guidance Manual https://www.ncbi.nlm.nih.gov/books/NBK91993/?report=classic distinguishes relative IC50 (half of compound maximal effect) from absolute IC50 (50% total activity). Need to avoid assuming arbitrary fitted midpoint equals the classical kinetic IC50 for partial inhibition.

## Work already performed

Reviewed local assay/scorer metadata; retrieved primary kinetic equations and assay description. No external Ki records downloaded. No paired-label calibration fit. No empirical data augmentation benefit measured.

## Questions for independent assessment

1. What conversions and assumptions can be explained accurately, and what is currently supportable for this challenge's assay values?
2. How should externally reported Ki be used to add learning signal, and what minimal comparison would test whether it helps the actual pIC50 task?

## Known missing or inaccessible information

Challenge substrate concentrations/Km and actual constructs, per-inhibitor mechanism, raw curves, free versus total concentrations; external record endpoint semantics, sources and overlaps; full text of 343-experiment paper. No permission to contact organizers has been given.

## Codex position

withheld for independent first-round assessment.

## Confidentiality check

Only current user request and public scientific/project information. No secrets or unrelated personal data.
