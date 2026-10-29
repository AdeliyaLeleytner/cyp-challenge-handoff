# P9a — authorized private CPU embedding-bank smoke

Hypothesis: the pinned Atom-JEPA molecular encoder can produce reproducible256-dimensional frozen features for a structurally diverse32-compound official train/blind sample without changing graph identity. This is feasibility/runtime evidence, not a downstream accuracy comparison.

Use16 train and16 blind IDs chosen deterministically from structures only, covering size extremes, charges, fragments, specified/unspecified stereo, rings and unusual elements. Preserve original SMILES and exact IDs. No labels are loaded for selection. Record all32 outcomes, including failures; partial coverage is not a complete bank. No silent neutralization, parent extraction, fragment/stereo removal or zero filling.

Pins/license/size are in ../representation-prep/ATOM_JEPA_PINS.json: package0.3.0 MIT, exactwheelSHA; officialHF molecularcheckpoint revision8f7514f...,156380852bytes, LFS SHA04061526..., modelCC-BY-4.0. Download this one pinned weight, verifycontenthash, loadlocalfiles withoffline mode. Reuse existingTorch2.8/NumPy2.5.4/RDKit2026.9.1; materialize onlymissinglightdependencies in an isolatedtarget. No secondTorchstack or shared-venv mutation. Total newP9assets below1GiB.

Geometry is one explicit-H ETKDGv3 conformer, seed42, chiralityenforced, MMFF94 maximum500iterations, matchingpackage protocol; recordconvergence and graph/stereo checks. Failures are explicit. Coordinates are generated representations, not experimental bindingposes. No fallbackgeometry/chemical normalization is introduced.

Inference usesCPU,fp32,no cuEquivariance,no compilation,no gradient updates, lastblock afterfinalnorm,degree0 atommean. Savecoordinates andatomorder, checkfiniteNx256 forsuccessfulrows, repeatability and reorderparity withfixedatol=rtol1e-5. Compareidentity/order/coverage withthe existingADME600bank, not coordinatevalues acrossdifferentrepresentations. NoPCA/readoutfit inthissmoke.

All inference runs through a committedORX child withbashrun.sh. The inference child, includingload/geometry/verification, is cappedat600seconds; timeout/slowcases are measured stagingevidence, notpermission forendlessretries. No full5655bank,paidlease,publication,notifications orleaderboard action. A later matchedADME600-versusAtomJEPA TabICL/PCA128 comparison needs separateauthorization.
