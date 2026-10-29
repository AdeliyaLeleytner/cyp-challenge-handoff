# Next frozen-representation hypothesis — preparation, not a fit

**Proposal:** compare the existing frozen ADME600 representation with **Atom-JEPA's last256-dimensional molecular block**, using the same TabICL regressor, fold-local PCA128, two estimators and seed42. This is a genuinely untried representation/readout route here. Both representations receive the same new readout, so an encoder effect is not confused with replacing TabPFN by TabICL. Keep Monroe as an alternative rather than silently substituting it.

## What is actually available

The inspected adlvdl source is pinned at `5ab3d7c9792e09da3fd10a18971a6696bdd62ecb`. Its `src/cyp/encoders.py` provides frozen extraction code; `notebooks/16_encoders.py` specifies the matched readout. The published Git tree includes:

- `experiments/17_regression_ensemble/blind_embeddings/monroe.npy`:2,160,128bytes.
- `.../atom_jepa.npy`:6,144,128bytes.
- Raw training banks named `monroe_<SMILES-hash>.npy` / `atom_jepa_<SMILES-hash>.npy` are **absent from this pinned tree**. The extractor writes them locally after sorting unique exact SMILES.
- `experiments/16_encoders/oof.parquet` and per-fold/seed caches are **fitted predictions**, not frozen representation matrices. They cannot be evaluated as new predictors on our different holdouts or repurposed as leakage-free features.

The blind arrays' sizes agree with the source-declared750×720 float32 Monroe and750×8×256 float32 Atom-JEPA outputs, but their binary headers and row mapping have not been independently downloaded/verified. Size agreement is not an identity certificate. We have not downloaded any feature bank or model weights.

**Monroe has a concrete weight route:** `https://media.githubusercontent.com/media/blazejba/monroe/main/checkpoint/weights.pt`, approximately300MB, expected SHA256 `df996e8e98b12a3cda5fe5acbef3e1e9a4ea31946d3736461cd07e53a5bf205a`. The source explicitly warns that the raw GitHub URL returns an LFS pointer. Config is fetched from `blazejba/monroe/main/checkpoint/config.json`; the source package/config revision still needs pinning, and upstream weight/license scope was not independently verified in this bounded inspection.

**Atom-JEPA currently resolves through** `AtomJEPA.from_pretrained("molecules")`, dependency `atom-jepa[rdkit]>=0.3`. The inspected challenge wrapper does not pin the resolved model/config/weight revision or hash. Resolving the official loader is the next preparation gate, not permission to install or infer.

Our actual CYP virtualenv has NumPy2.5.4, Torch2.8.0 and scikit-learn1.9.1, but no TabICL, Atom-JEPA, Monroe or PyG installation. No matching model cache directories were found under the local HF cache. Thus **there is no complete matched feature route ready to fit immediately**; staged training representations remain necessary.

## Provenance, identity and licensing

According to the inspected challenge source, Monroe pretrains on PM6 properties, PCBA assays and denoising; Atom-JEPA uses masked latent prediction on conformers. These descriptions are source-code provenance claims, not a literature review performed here. Both are molecule-only3D representations, not protein-conditioned docking scores.

Monroe's audit script explicitly checks PCBA CYP assays410/883/884/891/899/1851. It publishes a16.7KB overlap table, not fetched during the no-download phase. Exact overlap counts remain unverified. Related CYP assay exposure on matching compounds is not the same as seeing the challenge's newly measured direct labels, but can make training-compound CV and novel-analogue transfer differ. Its audit uses connectivity keys; future checks must distinguish exact stereo-preserving identity from broader connectivity matches.

Inference must freeze one feature bank before readout fitting. Preserve exact SMILES/IDs/order, checkpoint/config/code hashes, conformer generation settings and fallback/error rows. The Monroe wrapper checks missing encoder keys and documents an unseeded-conformer/flat2D fallback issue; it also supplies a separately seeded conformer route. Do not silently change molecular graph/stereo through an InChI round-trip, mix conformer recipes, drop failed molecules, or recompute random conformers within CV.

The adlvdl implementation has a verified MIT license. Its comments describe TabICL code/weights as Apache2.0, but the exact upstream readout checkpoint and encoder code/weight licenses still need official-version verification. Repo-code permission does not automatically establish model-weight or training-data scope. No publication is contemplated.

Scigantic's inspected release primarily supplies Chemprop/CheMeleon training code, training tables and fitted prediction caches; it does not provide these new raw training embeddings. Stir_bar supports capped, per-source embedding legs and warns against correlated tabular ensemble crowding, but its write-up is not an accessible Monroe/Atom-JEPA feature bank. Their selected public scores do not qualify our proposed route.

## Matched bounded experiment, only after staging is authorized

Use the same reviewed official train/test fold identities for both representations; train only on allowed training rows and never load another team's challenge-fitted predictor. Project PCA on each training fold only; use the identical128-dimensional cap and TabICL settings in both arms. Do not add ADMET120, concatenate encoders, sweep layers or tune placement in this first contrast. Atom-JEPA last block is predeclared; ADME600 is the credible existing-information control. Forty endpoint calls cover two representations×five folds×four endpoints, with all five pooled/per-CYP metrics and paired structural uncertainty. Keep OOF, old outer diagnostics and any prospective panel distinct. A later blend must hold the exact incumbent artifact fixed and fit coefficients using eligible OOF data only.

Mechanism: self-supervised3D local-environment information may improve conditional ordering not supplied by the existing ADME representation. Competing explanation: flexible tabular readout and pretraining overlap, rather than new representation information, account for apparent gains. A gain that disappears under a matched readout or is confined to related-assay pretraining overlaps does not establish general transfer to the analogue test. Zero or negative benefit remains plausible; no hidden-score improvement is forecast.

The author reports roughly an hour of CPU work for both encoders' training-set embedding and about5seconds/3.9GB for a2335-row TabICL128×2 configuration. These are planning evidence, not measurements on this host. A future32-molecule identity/runtime smoke should precede a whole-bank generation. Once banks and generic TabICL weights are cached,40 small readouts should be CPU-scale; memory and finite-output checks are essential. Their code requires NumPy≥2.4 after a documented classification NaN problem with2.2.6; isolate encoder/Torch and tabular/LightGBM processes as our own previous runtime issues also require.

**Current decision:** promising untried route, but less immediately ready than P8a's existing inputs. No fits, paid resources, large downloads or public actions were performed. Small implementation files were fetched during the initially permitted source inspection; no further downloads occurred after the temporary tighter instruction. Root has now authorized official Atom-JEPA loader/metadata resolution only; any resulting pins will be appended below before a bank smoke is proposed.

## Updated authorization/status

Official Atom-JEPA pins and licenses were resolved in `representation-prep/ATOM_JEPA_PINS.json`. Root then authorized P9a staging: the156,380,852-byte weight was downloaded and content-hash verified, with5.47MB of isolated missing-dependency wheels. No packages were installed and no inference ran. P9a is now paused per the newer user priority; see `p9a/STATUS.json`. Package0.3 distinguishes `layers="last"` (after final normalization) from `layers="all"[-1]` (pre-finalnorm block8); author caches must not be mixed across those conventions.
