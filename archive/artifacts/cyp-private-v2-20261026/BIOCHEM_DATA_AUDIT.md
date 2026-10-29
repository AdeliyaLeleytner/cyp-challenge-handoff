# Private biochemical estimand and source-data audit

Private research only. No fits, paid resources, ADMET prediction calls, public uploads or messages were made. Retrieval was limited to official metadata/protocols, one-to-ten-record activity samples and a1.1MB assay-annotation workbook, not bulk measurement collections. Root owns scholarly literature review; this report does not claim a completed literature review or a causal explanation of the previous leaderboard regression.

## What is being predicted

The target is the organizer’s fitted **direct-arm pIC50 for a specific biochemical assay**, not a universal molecular affinity, Ki, clinical DDI liability or substrate/non-substrate label. The official announcement establishes recombinant enzyme assays, inactive versus active NADPH preincubation, different reporter substrates/readouts, sparse hit-follow-up training and dense analog-expanded testing. In particular, the primary screen used the active/TDI condition. [Official announcement](https://openadmet.ghost.io/announcing-openadmets-cyp-inhibition-blind-challenge/); private capture: `biochem_sources/official-challenge-announcement.html`.

| Challenge target | Verified probe/readout | Still unverified for this exact challenge release |
|---|---|---|
| CYP1A2 | EOMCC, fluorescence | Probe concentration/Km, enzyme loading, detailed timing/buffer/dilution |
| CYP2C9 | EOMCC, fluorescence | Same gaps |
| CYP3A4 | DBOMF, fluorescence | Same gaps; older sibling protocol is not automatic confirmation |
| CYP2D6 | Dextromethorphan parent depletion, Echo-MS | Probe concentration, reaction/preincubation timing and signal-normalization equation |

The direct arm omits NADPH during preincubation; the active arm includes it. That is an operational condition contrast. It does not, by itself, establish a compound’s microscopic inhibition mechanism or provide kinact/KI. Catalysis during the subsequent readout and substrate dependence remain relevant. The dataset’s pIC50 name also does not settle whether the fitted concentration parameter represents absolute50% inhibition or half of a free fitted amplitude; partial curves make that distinction consequential.

The announced test selection purchased ten nearest in-stock analogs for each of25 potent hits from each of1A2/2C9/3A4. CYP2D6 was not a seed-selection target, although all750 compounds were subsequently assayed across the panel. This is a program-specific analog-expansion estimand, not unrelated-scaffold or clinical generalization. Treat proxy clusters as proxies for unavailable organizer series assignments.

## What the released quantities support

**Direct pIC50 and intervals.** Preserve the organizer’s point estimate, reported95% interval and std separately. Bayesian curve fitting is described, so these are not automatically “three replicate IC50 measurements” or independent Gaussian error bars. Priors, joint parameter covariance, exact curve equation and replicate layout were not established here. A low fitted pIC50 or wide interval can reflect a weak/extrapolated curve; it is not an explicit inequality field and must not be silently replaced by a point at4 or by a made-up censoring bound.

**Single concentration.** The local released table has17,504 rows:4,376 molecule IDs×4 enzymes. Every row records `concentration_m=4.95049505e-05`, approximately49.505µM. This is the recorded field, not proof that nominal preincubation and reaction concentrations are identical. An internal name such as `act100` is not enough to infer a100µM reaction concentration. `log2fc_estimate` is a fitted, variance-stabilized/spatially corrected plate contrast, with SE, p-value and FDR fields. Negative contrast denotes inhibition in the release’s convention; do not assume that exponentiating it recovers an uncorrected remaining-activity fraction.

`cohens_d` has exactly one value within each plate: nine unique values for nine plates per CYP. All values are negative and nearly uncorrelated with compound log2fc. This is consistent with a plate/control quality statistic, not a per-compound potency effect; its precise definition remains unverified. Plate IDs/QC cannot become ordinary blind-test molecular features.

**Emax.** The staged `emax_vs_pos_ctrl_direct_inhibition` values are all negative and mostly near−1. They are not directly a0–1 maximal-inhibition fraction. Its denominator, baseline/control direction and relation to the fitted curve parameter have not been established. Preserve the original scale and uncertainty. The older sibling release instead explicitly supplies `emax_log2fc`; that is a different named quantity, not a justified conversion formula for the challenge’s Emax column.

**TDI.** The official Boolean labels are operational IC50-shift classifications, not proof of irreversible/covalent inhibition. Unknown labels remain unknown. The TDI file repeats the primary direct values exactly where both are present and supplies **zero additional finite direct-arm labels** among its1,240 extra IDs. It adds active-condition measurements. Many extra3A4 IDs carry a negative TDI label while lacking a released direct value; do not invert the merged Boolean label into a direct-potency bound.

### Actual coverage, using the frozen staged source tables

| Endpoint | Direct finite | Below4 | CI entirely below4 | Median interval width | TDI-arm finite |
|---|---:|---:|---:|---:|---:|
| 1A2 |1,412|232|109|0.32833|1,413|
| 2C9 |1,285|259|69|0.52576|1,285|
| 2D6 |1,493|129|77|0.27161|1,497|
| 3A4 |2,335|944|640|0.37915|3,583|

There are530 direct-table IDs without a released single record; **all530 have3A4 direct labels and none of the other three direct labels**. There is one single-only ID. Missingness therefore has endpoint/program structure; a blank is not a negative. The reason a particular record is absent—selection, unrun condition, failed fit/QC or release decision—is not uniquely identifiable from the mask.

Emax/direct-pIC50 Spearman associations are−0.394,−0.407,+0.770,−0.462 for1A2/2C9/2D6/3A4. The MS endpoint has the opposite association, warning against a shared biological interpretation of the numeric Emax scale. This is an empirical association, not an explanation of the normalization.

Version caution: the cached Workbench Emax table has6,146 IDs, including Emax-only OCNT-2329004. The live Hugging Face size API reports6,145; the file history says “Remove Cisplatin,” while the dataset card still says6,146. Do not silently update the preserved incumbent. The sibling release’s reactivity card says2,442 rows, while live size metadata reports2,446. Counts below distinguish measured metadata from older prose. [Dataset card](https://huggingface.co/datasets/openadmet/cyp-challenge-train-test); snapshots: `official-table-audit.json`, `current-challenge-size.json`, `TDI-label-coverage.json`, `single-plate-QC-diagnostic.json`.

## Why a single point is not a direct-IC50 label

Under an explicitly assumed Hill response, inhibition fraction could be written

`I(c) = Emax * c^h / (K^h + c^h)`.

Then `K = c * (Emax/I - 1)^(1/h)`, where K is the half-amplitude concentration. At the same I=0.2 and h=1, Emax=1 gives K=4c, whereas Emax=0.25 gives K=0.25c; the latter never reaches absolute50% inhibition. Unknown efficacy, slope and signal normalization therefore prevent a unique inversion. An absolute50% threshold bound can be valid under a known monotone, same-condition fractional-inhibition assay, but those conditions have not been established for these released screen values.

Here the screen also uses +NADPH preincubation, while the target is the direct arm. Bioactivation can increase inhibition and metabolic loss can reduce it. Thus even a well-defined active-condition fractional response would not automatically bound direct potency. No bounds were invented in this audit.

Similarly, `IC50=Ki*(1+[S]/Km)` is a conditional rapidly reversible competitive-inhibition model, not a universal conversion. Unknown probe loading/free concentrations, preparation, partial efficacy or time dependence prevent wholesale Ki→IC50 pooling. Keep Ki as its own endpoint or use a justified context model.

## Existing external pools: concrete semantic/provenance issues

The cached ChEMBL table contains25,841 compound rows and80,926 aggregate measurement counts, but lacks per-record assay/document ID, endpoint type/relation, species, probe, concentration and timing. Its maximum-confidence histogram is15,319 at9 and10,522 at8. A maximum score does not describe every contributing measurement, and score8 is not itself proof of bad/nonhuman data.

A concrete cell illustrates the problem: CHEMBL10/1A2 has cached value5.7,n=3,SD0.4041451884. The official API exposes two AC50 pChEMBL values6.20/5.40 from a PubChem-imported assay and one IC50 value5.70 from DrugMatrix. Their median and sample SD exactly reconstruct the cached cell. Consequently, that column is not uniformly an assay-specific pIC50, and its SD is not necessarily replicate measurement uncertainty. This is a verified example, not a reconstruction of every curation rule. [Activity query](https://www.ebi.ac.uk/chembl/api/data/activity.json?target_chembl_id=CHEMBL3356&molecule_chembl_id=CHEMBL10&limit=10); `mixed-endpoint-aggregate-proof.json`.

Human target-ID queries also return homolog/nonexperimental assays: sampled CHEMBL666153/660388/665756 describe guinea-pig-heart contexts; CHEMBL665887 describes an in-silico Ki. Others document HLM,10µM bufuralol or100µM tolbutamide. Therefore target species/ID and assay typeA/B do not establish an experimental human recombinant inhibition estimand. These samples are not a prevalence estimate and do not prove every such row entered the old aggregate. [Example assay](https://www.ebi.ac.uk/chembl/api/data/assay/CHEMBL665887.json); `assay-context-query-index.json`.

For Veith/AID1851, official assay metadata specifies human recombinant insect-cell CYPs, pro-luciferin substrates at their stated Km, a60min reaction and subsequent luciferase detection. Its Potency field is AC50/half-maximal efficacy; it includes extrapolated fits and explicit curve-quality fields. “Max_Response” is the maximum observed response, usually at the top dose—not automatically fitted Emax or direct IC50. The cached85,535 rows are17,107 SIDs×5 CYPs (16,546 unique CIDs); inactivity and missing fitted potency are distinct. Some `ac50_um` cells contain a1,000,000 sentinel while fit-log potency is absent; never log-transform every numeric cell blindly. The native clipping of response tails is a modeling choice, not evidence that every outlier is optical interference. [AID1851 metadata](https://pubchem.ncbi.nlm.nih.gov/rest/pug/assay/aid/1851/description/JSON).

Chemical provenance remains essential. The earlier audit found28 narrowly proposed/approved source-quarantine requests, distinct from output-service exceptions. Preserve original and prepared SMILES, exact stereochemistry/isotopes/proton states and source IDs. Do not drop unusual elements merely because they are unusual, merge stereoisomers with a connectivity prefix, or equate a metal-complex assay with a retained ligand fragment. Current audits provide concrete exceptions, not a blanket certification of all original assay annotations.

## Useful obtainable data, beyond blindly adding the present pools

See `BIOCHEM_SOURCE_INVENTORY.csv` for retrieval routes and limits. The priority is new **information**, not inflated counts from re-exported measurements.

1. Raw assay-specific/censored ChEMBL records: preserve IC50/AC50/Potency/Ki and qualifiers separately, join assay metadata and exclude/separate nonexperimental or incompatible contexts. The saved relation-count queries are pre-filter/pre-dedup record counts, not new human compounds.
2. BindingDB: measured affinity records with explicit type/qualifier and provenance can add useful patent/curator records, but imports overlap ChEMBL/PubChem. Its documented UniProt REST route is potency-cutoff filtered and does not expose all assay context; do not mistake it for an unbiased negative pool. No target-wide download was done. [Web services](https://www.bindingdb.org/rwd/bind/BindingDBRESTfulAPI.jsp).
3. EPA invitrodb4.3: current annotation metadata confirms four export-ready human NVS CYP endpoints, with different probes and assay timings. AEIDs323/337/339/345 use CEC/MFC/AMMC/DBF respectively, not the challenge’s exact probe set. The metadata includes species, enzyme source, detection, response direction and QC; response records still need retrieval/deduplication. Only the1.1MB annotation workbook was downloaded. [Official release portal](https://www.epa.gov/comptox-tools/exploring-toxcast-data).
4. Reporter counterscreens: PubChem411/588342/1006 have72,359/364,105/195,634 tested SIDs. They can test interference hypotheses for coupled luciferase sources, not supply CYP-negative labels. Filtered-by-SID/CID retrieval is available; no response corpus was fetched. [PUG-REST routes](https://pubchem.ncbi.nlm.nih.gov/docs/bioassays).
5. The same-platform Octant sibling release provides1,340 active-preincubation3A4 inhibition summaries,16,931 inhibition wells,2,446 reactivity rows,19,344 reactivity wells and11,353 ionization-profile rows (live size metadata). It is promising for metabolic-fate/QC hypotheses but must be overlap-checked; active-preincubation potency is not the direct target. Its older3A4 protocol uses DBOMF2µM, enzyme5nM and30min preincubation plus30min reaction; those values are not established for every current challenge arm. Candidate ionization amenability is not equivalent to detectability of the fixed dextromethorphan probe. [Release](https://huggingface.co/datasets/openadmet/Octant_CYP_inhibition_reactivity_blog_release); [pinned protocols](https://github.com/OpenADMET/Octant_CYP_blog_post/tree/58b3d6a63d25b18bee0b68af07cf1a5b30e6cf0d/protocols).
6. TDC Carbon-Mangels substrate labels contain666/664/667 drugs for2C9/2D6/3A4. These are substrate classifications, not inhibition potencies. TDC Veith inhibition datasets are repackagings of the already represented source, not new independent measurements. [Dataset documentation](https://tdcommons.ai/single_pred_tasks/adme/).

No new unique-compound total is claimed without exact structure/assay/source overlap analysis. Required ingestion fields are source/version/record ID, raw and standardized structure, biological target and species/variant, enzyme preparation, probe/loading, inhibitor dose/unit/relation, preincubation/cofactor/reaction timing, measured response/direction, fit/efficacy/curve-quality fields, document provenance and duplicate lineage. Missing metadata remains missing rather than guessed.

## Consequence for the next private experiments

`HYPOTHESES_DATA.md` proposes three competing tests: assay-context/censoring information versus mere coverage; correct-condition signed metabolic-fate auxiliaries versus fit/QC coupling; and reporter-specific nuisance versus genuine promiscuous binding. Each keeps the incumbent identity fixed, masks heldout compounds across all experimental endpoints and retains adverse outcomes. These test specific biological/data explanations; they do not yet establish a large deployment improvement or a new molecular mechanism.

Open questions that materially block mechanistic inversion are the exact current probe/dose grids, dilution/preincubation conventions, Emax equation/control definitions, raw-signal transformation, curve definition/priors and missingness reasons. We have not contacted organizers or published anything to resolve them.
