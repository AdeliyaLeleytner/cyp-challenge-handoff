# Existing external-measurement availability for blind750

**There is no broad exact-label availability lever in the currently saved pools. Exactly1of750blind molecules has matched public assay records; its maximum-response measurements are already in our current training table.** Additional cached PubChem potency values exist for that molecule and many external training compounds, but they are AC50-derived, assay-specific outcomes—not hidden challenge direct-pIC50 labels and not a ready lookup replacement.

This audit used only existing files:25,841ChEMBL aggregate rows,85,535PubChem/Veith rows(17,107SIDs×5isoforms), the780-record typed P4panel, official training/auxiliary tables, the exact blind750structures, approved identity mappings, currentP7/P7R common31,641-row table and the saved corrected own750/briford529outer-training tables. No new download, fit, spend, leaderboard query or prediction reverse engineering occurred.

## Identity levels and counts

| Matching policy | ChEMBL blind molecules | PubChem blind molecules | PubChem source rows |
|---|---:|---:|---:|
| Exact canonical isomeric graph of saved original source SMILES |0|1|5|
| Exact isomeric graph of historically prepared source SMILES |0|1|5|
| Exact plus previously reviewed stereo-preserving equivalence groups |0|1|5|
| Broader normalized/uncharged parent with stereo ignored |0|1|5|
| Same broader operation applied independently to original source forms |0|1|5|

Allrows outside the32421request queue were included in the raw-source checks:963distinct prepared ChEMBL graphs and871PubChem graphs did not have a queue entry, so their broader keys were computed explicitly rather than silently omitted. No additional blind matches appeared. The typedP4raw-activity panel has0exact blind matches. Official released inhibition, TDI, single-concentration andEmax tables also have0exact blind-structure matches.

The broad key deliberately ignores stereo and removes parent-form/charge distinctions; it is an audit candidate relation, **not proof of the same chemical entity or assay transferability**. It retains bond orders and is not unrestricted tautomer canonicalization. Approved equivalence uses only the13previously reviewed stereo-preserving groups; no new tautomer or stereoisomer was merged. These levels are not necessarily nested, because a reviewed tautomer can differ in bond order despite being outside the stereo-free connectivity key. Counts always refer to unique blind molecules, not five independent compounds because fiveCYP measurements exist.

“Original source” here means the saved source’s molecular representation. It does not certify the physical experimental salt, stereoisomer composition or formulation. Allsource/request strings are retained in the detail artifact.

## The one concrete blind match

**OCNT-0496981** matches PubChem **SID14743815/CID3605061**, current training alias **VEITH-RWZAIHHFBKOVIK**. Exact shared encoded graph:

`O=C(Nc1nc2ccccc2s1)C1COc2ccccc2O1`

Both source and blind representations leave one possible stereocentre unspecified; exact encoded identity does not establish identical experimental enantiomer/racemate composition.

| CYP | Cached AC50(µM) | Cached pAC50(legacy column namedpic50) | Max_Response | Current18-task table uses |
|---|---:|---:|---:|---|
|1A2|1.58489|5.80|−115.8030|Max_Response|
|2C9|1.58489|5.80|−112.7160|Max_Response|
|2D6|11.2202|4.95|−46.3438|Max_Response|
|3A4|missing|missing|−6.2837|Max_Response|
|2C19(auxiliary)|3.98107|5.40|−126.7806|Max_Response|

AllfiveMax_Response cells are already retained in the fullP7/P7R common table. The public row is in training forP7rotations0/1/2, stopping for3 and the source-row test partition for4; table retention does not mean everyindividual model sees it in training. No official direct label is supplied for this blind molecule. Cached PubChem pAC50 is not an existing target head in the eighteen-task recipe.

The saved primary PubChem **AID1851** description explicitly defines “Potency” as the concentration at half-maximal efficacy(AC50), including possible extrapolated fits, and Max_Response as maximum observed activity, usually at the highest tested concentration. The historical`pic50` column equals−Fit_LogAC50; its column name does not change the estimand. The2D6curve has partial maximum response(about−46%), illustrating why half-amplitudeAC50 cannot automatically become absolute50%-inhibitionIC50. Missing3A4potency is not an exact low-potency target or an inferred bound.

Assay context: human recombinant CYP from insect-cell/baculovirus preparations, pro-luciferin conversion with luciferase detection, NADPH-supported reaction for60minutes followed by20minutes detection incubation. Declared probes/concentrations include1A2Luc-ME100µM,2C9Luc-H100µM,2D6Luc-ME EGE30µM and3A4Luc-PPXE25µM. These differ from the challenge’s EOMCC/DBOMF/dextromethorphan readouts and its explicit direct versus active preincubation arms. No matching−NADPH preincubation observation is established by this public protocol. Source-specific activity signs, efficacy and curve quality must remain separate.

The saved AIDdescription identifies assayversion1/revision2, but contains no per-record experimental/deposition/publication timestamp. The raw wide pools also lack per-measurement dates. A source-manifest note says the historical storage objects were replaced2026-09-02; that is an object-history statement, **not the measurement date or a complete time-cutoff provenance certificate**. No missing date was inferred from a filemtime or from the nameVeith.

## ChEMBL: do not relabel an untyped aggregate as directIC50

The wide ChEMBL pool retains compound IDs, original/prepared strings, per-CYP aggregate values/counts/SD and maximum confidence score. It does not retain each contributing assay’s type, relation, units, species/preparation, probe, date or document. It therefore cannot distinguish IC50,AC50,Ki or other pChEMBL-compatible estimands cell bycell. Ki would require mechanism/[S]/Km information to relate toIC50; none is restored by aggregation.

There is an existing concrete positive control: CHEMBL10/CYP1A2aggregate5.7,n3,SD0.404145 is reproduced by AC50p-values6.2and5.4 plusIC50p-value5.7. Source IDs arePubChem(src7) andDrugMatrix(src15). This proves AC50/IC50pooling in at least one cell; it does not prove that every cell includesKi or establish unknown source types. ChEMBL’s cross-assay SD is not replicate uncertainty. The newtypedP4panel preserves its record-level source/unit/relation/document context but contains no exact blind750match.

Thus the existingpool has **0matched ChEMBL compounds forblind750**, even under the broader key examined. No ChEMBL IC50/AC50/Ki value is newly claimed for a blind compound in this audit. This is a statement about saved data, not proof that the entire current public database lacks such measurements.

## What full training retains versus local validation removes

Compare only public-assay auxiliary cells actually present in the current31,641-row fulltable, then inspect whether their rows survive the saved correctedouter union18tables:

| Cohort | Exact matched heldout compounds with public auxiliaries | Including approved equivalence | Public matching rows retained in correctedouter training |
|---|---:|---:|---:|
|Own750|44/750(5.87%)|48/750(6.40%)|0|
|Briford529|13/529(2.46%)|16/529(3.02%)|0|
|Blind750|1/750(0.13%)|1/750(0.13%)|The public row is retained in the fulltable|

Within the exact matches, own750has37compounds with ChEMBL aggregate cells(86cells) and38with PubChemMax_Response(190cells); these sets overlap. Briford529has12with ChEMBL(30cells) and11withMax_Response(55cells). Adding approved equivalents gives41/40compounds for own750 and15/14forbriford529, respectively. Counts are not additive across sources or identity levels.

Concrete approved-equivalence cases removed from outer training include ownOCNT-0022129↔CHEMBL42 andbrifordOCNT-0497994↔CHEMBL1480. Their raw structures differ by reviewed proton/bond placement; the exact strings and surviving fulltable assay values are retained in outer-public-availability-detail.csv. This does not license collapsing arbitrary tautomers.

A broader-only case is brifordheldout **OCNT-0494161** versus fulltable **OCNT-1911794**: their encoded stereochemistry differs. The latter row has public assay cells including a legacy2D6pChEMBL aggregate7.38 andMax_Response−76.925, but is removed by the connectivity-based outer purge. This is a conservative removal of a different stereoisomer, **not evidence that both are the same compound**. Broader connectivity yields14public rows for13brifordheldout compounds, adding this one row beyond exact matches. It should remain a separately reported conservative-policy case rather than an automatic identity merge.

An availability-preserving validation experiment could legitimately retain independently obtained public cross-assay measurements while masking the challenge’s heldout target, provided origin/date/type/probe provenance and the allowed-data rules are established. That would estimate **new-assay prediction for compounds already measured elsewhere**. The present purged setup instead estimates transfer to molecules without those exact public measurements. Neither question is inherently invalid. However, the observed blind750has farless exact support than these developmental holdouts, so keeping all such external measurements in validation would risk making validation **more optimistic**, not obviously more realistic for this target. This audit does not justify reverting the purges to improve local scores.

The broad stereoisomer purge could be reconsidered in a narrowly declared validation-policy experiment, but its one concrete extra row is not a general top10lever. The original approvedcold-validation comparisons remain untouched.

## A real but separate unused-data opportunity

The fullsaved PubChem pool contains the following finite legacy pAC50 cells, all matching−Fit_LogAC50:

| CYP | Finite fitted potency records | Max_Response records |
|---|---:|---:|
|1A2|9833|17107|
|2C9|8311|17107|
|2D6|5969|17107|
|3A4|9377|17107|
|2C19|9544|17107|

These total43,034potency **records**, not43,034new compounds or necessarily usable exactIC50labels. Distinct SIDs/CIDs can represent duplicated chemistry. The rawAC50 field includes1e6sentinels(37/20/13/6/29bythe displayed isoform order); some fitted-log potencies lack a populated rawAC50 field. Efficacy, curve class, R², extrapolation and sourceidentity need record-level review before selecting a loss or training target. Do not blindly logsentinels, callmissinginactive, or renameAC50asIC50.

The current18-head model uses five PubChem maximum-response tasks, not these five potency tasks. The addendum below quantifies the substantial overlap with existing ChEMBL targets. A future **explicitly assay-typed auxiliary potency** experiment could test whether curve-position information improves transfer beyond maximum response, with matched compounds, label masks, loss mass and source purges; it must not count duplicate observations as new independent data. Its possible value is generalization from more informative existing assay supervision, **not widespread exactblind label lookup**. No such ingestion or fit is authorized or performed here.

ADMETlab outputs, Atom-JEPA features and other pretrained predictions are not experimental CYP measurements and were not counted as public assay availability. Official training auxiliary data are likewise not hidden challenge labels; their exactblind overlaps were0.

## Rules, privacy and practical decision

The saved official Space rules explicitly permit external data and pretrained models, with proprietary-data disclosure. That supports considering genuinely public cross-assay records even when a blind structure overlaps. It neither grants access to hidden challenge labels nor proves any untyped aggregate is biologically appropriate. Conversely, structure overlap alone is not automatically misconduct when the task is prediction under a different assay. Keep raw sourceprovenance and disclose the estimand/overlap in any future authorized report.

**Recommended next decision:** do not spend on a broad exact-match shortcut or relax validation purges based on these counts. The only exact blind molecule already has public maximum-response supervision; an incremental typedpotency branch is a concrete existing-data hypothesis for parent review. If additionalpublicrecord acquisition is proposed, it must be bounded by source/type/probe/date and independently audited rather than assumed from a coarse connectivity match. No new acquisition, fit, handlabel, submission or publicwrite occurred.

Evidence folder: external-availability/. SUMMARY.json binds source hashes; blind-coverage-counts.csv and blind-source-matches.json preserve everymatch; blind-current-training-public-targets.csv shows retained cells; outer-public-availability-detail.csv and*-summary/by-source.csv show actualpurges; official-auxiliary-overlap.json checks the released auxiliarytables; pubchem-label-availability.csv preserves potentialpotency counts/sentinels. The pAC50positivecase’s exact original/prepared/test SMILES are preserved. No inputs were edited.

## Finishing addendum: fitted-potency inventory and the Scigantic22-task distinction

The bounded global audit substantially narrows the apparent “43knewpotencies” opportunity. **Finite fitted-log values are not automatically inhibition labels, and most source values already overlap the current ChEMBL auxiliary targets.** No new training targets were materialized.

### Mechanical availability and qualifiers

All43,034finite legacy`pic50` values equal−Fit_LogAC50. Of these,40,508also have a positive, non-sentinel rawAC50 and a negative numerical curve code;2,526have positive curve codes and missing rawPotency. The latter generally have positive responses and must not silently become inhibition-potency labels. This sign grouping is preserved from the source encoding; it is not a complete mapping of everycurvecode to a verified quality class.

| CYP | Finite fitted pAC50 | Negative-code + positive nonsentinel rawAC50 | Positive-code fitted values/rawAC50missing | RawAC50=1e6sentinels | Candidate graphs in currenttable | Candidate graphs without current ChEMBL target |
|---|---:|---:|---:|---:|---:|---:|
|1A2|9833|9793|40|37|9180|21|
|2C9|8311|7294|1017|20|6948|15|
|2D6|5969|5675|294|13|5151|14|
|3A4|9377|8814|563|6|8208|7|
|2C19|9544|8932|612|29|8551|16|

“Candidate” means mechanically identifiable fitted-potency records/graphs, **not biologically validated directIC50**. All105rawAC50sentinels have missing fittedpAC50 in this cache. They must not be transformed into artificial exactpotency0. Among the40,508negative-coded candidates,12have a positiveMax_Response(0/1/2/4/5for1A2/2C9/2D6/3A4/2C19) and deserve explicit direction-consistency review. Removing onlythat flag would leave40,496direction-consistent records, not a new training authorization or a declaration that the othercurves are reliable.

Curve quality remains heterogeneous. Numerical classes include−1.1,−1.2,−1.3,−1.4,−2.1,−2.2,−2.3,−2.4and−3, as well as positivecodes in the separate group. The saved schema explains complete versus partial curves and efficacy>80%versus lower efficacy, but the cached wide table does not retain each textualCurve_Description. We therefore preserve raw numericcode counts rather than invent an unverified lookup or select a “good class” posthoc.

Negative-coded candidateR² minima are0.3138–0.3626 and medians0.9561–0.9878 acrossCYPs; allhave recordedR² andHill slope. A good fittedR² does not make a partial/asymptote-extrapolatedAC50 an absolute50%inhibitionIC50 or supply a confidenceinterval.2,786/1,757/2,122/2,385/1,085negative-coded candidate records have absoluteMax_Response<50%for1A2/2C9/2D6/3A4/2C19. The2D6fittedpAC50range reaches2.05, illustrating that fittedcurve position need not lie comfortably inside the tested concentration range. No R² cutoff, efficacy cutoff or potency clipping was invented.

### Exact overlap and duplicate-supervision risk

Of the43,034finite fitted records,39,580match a **current nonmissing ChEMBL target at the same prepared isomeric graph andCYP**.38,569of those39,580(97.45%)have exactly the same numeric target value. Restricting to the negative-coded/nonsentinel candidates leaves38,562matching records,37,600with the same value. This is strong evidence that treating the two sources as wholesale independent information would double-count much existing supervision. Numerical equality alone does not establish that every record is the same experiment; the saved ChEMBL aggregate lacks the record/assayIDs needed to certify each duplicate. The independently reconstructed CHEMBL10example already establishes that PubChemAC50observations do enter the nominal ChEMBL “pIC50” aggregate pipeline.

The more relevant **new label-cell count on current molecules** is73prepared-graph×CYPcells after the negative-code/nonsentinel restriction:57across thefour primaryCYPs and16for2C19. These counts use exact preparedgraphs and preserve the difference from raworiginalgraphs. Sourcegraphs outside the currenttable may reflect curation/representation differences or omittedmolecules; they are not automatically new valid compounds.

Repeated sourcechemistry is substantial:663graph×CYPgroups contain1460fitted SIDrecords(797extra records beyond one pergroup);609of thosegroups have discordant fitted potencies. They span331preparedgraphs acrossendpoints. Some preparedgroups combine more than one savedoriginalgraph. These can represent repeated substances, different sourceforms or multiple observations; do not silentlyaverage them or call their dispersion replicateuncertainty. ExactSID/CID/original/prepared strings and per-record conflicts remain in potency-repeated-graph-records.csv and potency-current-ChEMBL-overlap.csv.

### What the inspected Scigantic22-task source actually does

At the already saved revision`e70a2920d611684c9aaff07400d951e2e79dd5f6`, `training/README.md` describes a31,669-row table with:

- four official directpIC50heads;
- four official single-screenlog2FCheads;
- five ChEMBL aggregate heads, including2C19;
- five AID1851Max_Responseheads;
- **four `cyp*_pic50_qhts` heads from AIDs410,883,884,891**, with15,070joinedlabels.

This is union18plusfourqHTSpotencyheads, not our proposedP8condition22(which adds active-preincubation heads), and not automatically “all43,034cachedAID1851potencies.” The README explicitly says blindOCNT-0496981has AID1851maximum-response supervision only and no potencylabel in that released table. It describes median joining byInChIKey connectivity, ignoringsalts, stereo andcharge. That identity convention requires separate scrutiny before adoption; it is broader than the exactgraph counts above.

The inspected `chemprop_22/train_interval.py` reads all targetcolumns from its trainingtable, applies the intervalloss to thefour scored heads andMAE to18auxiliaryheads, masks boundcarriers, and uses uniformweights in the saved amended code. Its CSV-loading code does not itself reconstruct the qHTSrawrecords or establish their filters. The cached `training/README.md` describes a separate `train_aux_ac50.py` arm with inverse-varianceweights; that specificscript/rawqHTSjoin-table builder was not among the previously inspected localfiles. No newfetch was made to fill that gap. The publishedensemble’s score cannot be attributed solely to theextraheads from these files.

Different citedAIDs do **not** prove independent experiments. The relationship of410/883/884/891to1851may include overlapping, component or reissued observations; the required rawrecord crosswalk is absent from the inspected cache. Do not add the15,070and43,034counts or call them independent new labels. A faithful22-task data reproduction needs the exact released table or rawrecord provenance/filtering, plus an explicit choice about its connectivity-based identitypolicy. Our P3/P7 eighteen-head experiments did not test that22-task table; our P8condition22is a different biological intervention.

### Decision: meaningful untried test, but not uncontrolled label expansion

A **matched endpoint-replacement test** on existing data is more immediately interpretable than simply appending potencyheads and calling the resulting loss-mass increase “new information.” A concrete future contrast would keep the same four qualified molecule×CYPcell masks and replace fourMax_Responseauxiliarytargets with assay-typedpAC50, while retaining2C19’s existingtask and allotherheads/rows/scales/coefficients. The amplitude-control arm must also mask itsMax_Responsecells to the same potency-available set; otherwise potencyversusamplitude is confounded by coverage. Keep the originalfull eighteen-head model as a separate practical reference, not the matched scientificcontrol. This would test curveposition versusmaximumeffect, not directIC50versusAC50equivalence.

Because much potency already matches the ChEMBLhead, report overlap-stratified behavior and fixedsource lossmass. An improvement could reflect source-conditioned repeated supervision or weighting, not additional independent measurements. A faithfulScigantic22-task reproduction is also untried here, but its exacttable/provenance and chemicaljoin choices are unresolved; it is not yet a ready drop-in experiment. Neither route is justified merely by “more labels.” Parent review is required before newingestion ortraining; this addendum performs neither.

Detailed artifacts: potency-global-inventory.csv, potency-curveclass-inventory.csv, negative-potency-qualifiers.csv, potency-repeated-graph-records.csv, potency-current-ChEMBL-overlap.csv, negative-potency-existing-ChEMBL-overlap.csv andPOTENCY_INVENTORY_RECEIPT.json. Originalrawpool andcurrenttrainingtable hashes are preserved; sourcecode/READMEhashes identify exactly what was inspected.
