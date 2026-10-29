# P7R version1: two-column unit-normalized feature stage

**Stage ready; no predictive model training or GPU use.** The separate versioned matrix changes exactly170numeric cells:Vol andDense for85retained molecules. All31,641molecules, exact input/service strings, IDs, labels and folds are preserved. The other118columns—and their complete fold-specific standardized vectors—are byte-identical to the original P7 inputs. The original feature cache is unchanged.

## Transformation and exact scope

The pinned public Scopy source revision is`ed2651583ee25c0a7f9767e3ed54452f81b3de79`, file SHA256`8789d590db551837902be5a533b027fdf7ac6ce08704d133f66b96e517fdcc4f`. Its molecular-volume calculator documents an Å³ atom-additive result but mixes decimal radii(H1.20,C1.70,etc.) with integer picometre-style values(B192,Si210,As185,Se190,Sb206,Hg155,etc.).

Version1 enumerates the source table’s integer-pm entries and divides **only those radii** by100. It retains the same hydrogen-completion, sum4πr³/3 and−5.92per-bond correction. It does not add a new radius, infer missing elements, choose a conformer or modify the stored molecular graph. For affected rows it recalculates the same empirical atom-additive approximation with consistent radius units, then setsDense=**recorded MW**/newVol. For all unaffected rows, originalVol/Dense values are preserved exactly rather than rewritten with insignificant floating-point differences.

This is a unit-normalized version of the existing descriptor—not experimental molecular volume, a validated3D/conformer volume, or a claim that the approximation accurately describes every element/chemical environment. Dense remains the service’s defined MW/Vol ratio, not an independently measured physical density. No molecule was declared invalid because it contains an unusual element.

## Whole-stage verification

Every one of31,641returned service graphs was parsed, hydrogen-completed for the descriptor calculation, and checked against the published radius table. All atoms had an explicit source radius; there were **zero unsupported-radius, parse, formula-mismatch or nonpositive-volume exceptions**. Explicit cases would have been preserved in `explicit-handling-cases.json` and prevented finalization, rather than skipped or silently approximated; that manifest is empty here.

The unrounded original formula reproduces all31,641recordedVol values, maximum relative discrepancy3.27×10⁻¹⁵(maximum absolute1.19×10⁻⁷ for the huge values). OriginalDense equals recordedMW/originalVol numerically on every row. The explicit tolerance for floating-point formula agreement was1e-12relative plus1e-9absolute; observed agreement is substantially tighter. No tolerance was tuned after seeing disagreement.

Only85rows contain an affected source-table element. Their newVol values are126.49–748.91 and newDense0.8505–1.8676. For example,CHEMBL113478(MW315.90) changesVol57,461,988.6874→222.119985 andDense0.0000054975→1.422204. Every affected row retains its exact request/service/model SMILES and request ID in changed-values.csv.

Verified invariants:

- Matrix remains float64[31641,120], same column order; onlycolumn60Vol andcolumn55Dense have changed bits.
- Exactly170cells differ; all118othercolumns are byte-identical, including signed-zero representation.
- rows.csv, table.csv and fold-manifest.json are byte copies of original P7 files; no labels, CI bounds, IDs, row order, SMILES or train/stop/test membership changed.
- In allfive training folds, StandardScaler means, variances and scales for118othercolumns are byte-identical. Their entire transformed float32 matrices, including stop/test rows, are also byte-identical.
- Normalization is calculated using the same post-purge training indices. OnlyVol/Dense scaler parameters and transformed coordinates change.
- All input and output hashes were rechecked after generation. Source/raw files are bound and were not edited.

## What the new scales do—and do not fix

Vol training means become370.09–378.94 and standard deviations112.38–116.09, replacing means71k–118k and standard deviations1.67–2.11million. Thus ordinary molecular-volume variation is no longer collapsed by the radius-unit defect.

This is intentionally **not a broad outlier cleanup**. CorrectedVol still reaches|z|≈16.66 for large retained molecules. Dense’s largest|z|can increase from16.94 to19.34 as removal of the near-zero artifacts shrinks its standard deviation. Other large coordinates—includingVDss,Flex,MDCK and rarecharge/alert values—are untouched. A downstream improvement cannot be promised from numerical consistency alone.

## Peer review of the four specific contrasts

Retain a fresh capacity/initialization-matched zero-descriptor graph control, original120fusion, Vol/Dense-masked fusion, and this two-column-unit-normalized fusion. All use the originalP7 eighteen-task recipe, identical rows/folds/labels and118unchangedfeatures. BroadCDF is not part of this first causal test.

- **Masked versus original:** tests the net effect of supplying these two original coordinates in this training recipe. It removes valid ordinary information as well as the defect; it does not show volume/density are generally unhelpful.
- **Unit-normalized versus original:** isolates this concrete source-table unit correction and the resulting legitimate refit of onlytheirtwo training normalizers. Changes to allrows’ standardizedVol/Dense are expected because the training moments change; that is part of repairing the feature, not an accidental118-column change.
- **Unit-normalized versus masked:** tests whether restored, unit-consistent descriptor information helps relative to withholding the two coordinates. A benefit supports useful information in the corrected approximation; no benefit may indicate graph redundancy, insufficient sample benefit or remaining optimization effects.
- **Each fusion versus zero:** retains the practical reference. Even if the unit correction improves over originalfusion, it may still fail to beat graph-only because the other118features and their optimization/assay mismatches are unchanged.

Preserve the same parameter initialization and factor-independent random setup. Zero/masked features mean zero in standardized coordinates, not raw zero. No posthoc clipping, special unusual-element exclusion, new loss, teacher inference or broader scaling branch belongs in this contrast. Allfive metrics/perCYP and contrary outcomes should remain visible. No result has been measured yet.

## Versioned files and bindings

Matrix: `v1/admet120-unit-normalized.npy`

SHA256:`62cddb9cfc892655c54f2e930b16f720d8725e05d3a70165f366739e08a2e856`

Manifest: `v1/manifest.json`

SHA256:`b7706a74d90ee311e492dc7e6f1023cd2788756db1f8ae19e2cb1b19acd1d6d6`

The manifest binds source code, original matrix/table/row/fold hashes and allversionedoutputs. Supporting files are all-row-formula-audit.csv, changed-values.csv, radii-policy.json, explicit-handling-cases.json and training-normalization-comparison.csv. `prepare_unit_repair.py` refuses to overwrite an existingversion and fails finalization if any source-radius/formula case needs review. Private local preparation only; this report does not authorize a model run or spending.
