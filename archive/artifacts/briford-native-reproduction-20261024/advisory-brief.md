# Independent Claude consultation
Round:1

## User request
"сделай точь-в-точь воспроизведение bridford, нам нужно хотя бы приблизиться к нему на лидерборде"
Prior standing authorization: rent what is needed on Vast for fast work; submit challenge solutions. Previous pipeline scored.7521 vs briford.4378. User now explicitly requests faithful briford reproduction, including calibration, superseding the previous train-only adaptation.

## Authoritative context and constraints
2026-10-24 Europe/Moscow. Current campaign root. Read-only advice. Codex owns decisions. No credentials, contacts or training by advisor. AvailableVastcredit~6.075USD, no topup authorization. Planned bounded20fold run, reserve>=1.5USD, exports before destroy. No live campaign rentals yet. Earlier submission accepted00:10:09UTC;12h cooldown means earliest new send12:10:10UTC today. Current local time~12:25Moscow. No silent assumption that historical data/checkpoints are available.

## Current state and evidence
- review-code/briford_native.py is committed b230a63 in ORXproject6678888c-9305-4203-9fce-6bdaed527e9a, experiment4ef0bd8c-6593-4ac7-9a44-e7206315a1db. Preparation succeeded localORXrun3f276a29-e9f5-4ab9-9362-52cfca2793cb. No model fits yet.
- review-code/native/ contains unchanged author assembly scripts, trainingcore, datapoint/inferencehelpers, scaffold split, ensembleassembly, calibration. Transport-only API stubs capture dataframes/modelconfigs and replace cloud storage. Native model scripts calculate taskweights globally; native train_chemprop_fold will fit each member's own full merged pool, seed42+fold. Native model predictions fp32.20models, no secondseed or learned stack.
- The author's historical blog specifies18-head union,8headmtaux,6head2D6specialist,1head2D6single. Native18-head model script is pinned971f6a7f24d86e59bab219347c3e14c006ae4e35. Remaining functions8c72c7559471febaf0962fd551b4eaab8db3a136. Later same-name model code at34689b/8c72 has26heads although stale docstring says18. Do not conflate them.
- prepared/manifest.json and four prepared/{member}.json: native data assembly yielded union18=31670rows (matching historical model docstring), mtaux8=4905,2d6isoform6=23264,2d6single=1493. Totalunionbeforeheadfilter32877. Each member gets native whole-scaffold5fold partition on its own data. Original extra parent purges removed; native InChIKey connectivity join and public shared labels preserved.
- prepared/native_overlap_audit.json: one publicVeith connectivity group overlaps actualTEST, no hiddenTESTlabels loaded. This is reported, not silently removed from native recipe. All sources public; earlier user explicitly authorized open data.
- sources/parquet-availability.json: all6preferredparquetURLs404, soCSVfallbackmatchesnativePublicData.get. sources/public-s3-versions-status.json: anonymoushistoricalobjectversionlist403. OfficialdataobjectsAug17; publicChEMBL/VeithobjectLastModifiedSep2 afterAug28score; semantic change not established, historical bytes unavailable. Native counts matching does not prove exact olddata.
- Native historical model/container versions not fully pinned upstream; plan uses existing reproducible torch2.6/CUDA12.4,chemprop2.2.1,lightning2.5.5,rdkit2026.9.1,pandas2.3.3,numpy2.2.6,scipy1.16.2,sklearn1.7.2 environment. Known limits recorded in config.
- Final native workflow: flatmean of5foldpredictions per component, native cyp_ensemble_submit.py flatmean across2members or4for2D6, native oof_pearson across commonlabelledIDs, publishedOOF_TO_BLIND multipliers, place(strae=True), recalibrate includingfloor1.0. Original author's training-onlyholdout score cannot be treated as independent evidence for these board-derived constants.

## Work performed
Fetched source throughGitHubconnector, inspected historical commits, checked publicdataformats/versionaccess, executed native assembly and folds in trackedpreparationrun. Read code for a storage-only adapter; no paidcompute yet. LocalCVmodelresult notavailable yet.

## Questions
1. Does this bounded native-source execution preserve the requested recipe, and what decision-critical discrepancies or checks remain before model training/submission?
2. How should unavoidable historical-data/environment limits and public-board-derived placement be represented without overclaiming an exact score reproduction?

## Known missing
Original privatecheckpoints/OOF, originaldataobjectversions, originalimagepackagelock, exacthistoricalseed-specificoutputs. Advisorcannot train or obtain these.

## Codex position
withheld for independent first-round assessment.

## Confidentiality
No secrets,credentials,privatekeys,.env or unrelatedpersonaldata.
