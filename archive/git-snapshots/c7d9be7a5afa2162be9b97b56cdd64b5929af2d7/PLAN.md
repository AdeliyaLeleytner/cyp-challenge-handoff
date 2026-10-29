# Corrected native reference: strict tautomer exclusions

Parent1346e303-7733-44ce-b2d8-ffe26eab8a61 established the native four-component ensemble on two frozen outer holdouts. This child corrects a newly audited source of training/validation structural overlap:12 specific external component rows are strict stereo-preserving tautomer counterparts of outer-held-out official molecules. Four broader stereo-related analog rows are not part of this correction.

The controlled change is training membership only. Keep all outer IDs/truth, retained data values/order, model hyperparameters, native vendor code, primary task weights, and surviving inner-fold validation assignments. Delete/reindex the12 outer rows; additionally remove train-side strict-equivalence counterparts of each inner validation set. No scaffold re-splitting. Emit exact per-fold exclusions and preserved-member certificates.

Retrain union18 and2d6isoform6 only (20fold fits total). Reuse mtaux8 and2d6single only if every data/spec/fold/outer-exclusion/checkpoint/prediction hash and native training source check passes, and their inner train memberships remain unchanged. Preserve historical native scores; measure the corrected reference separately, raw and with unchanged native placement.

Preparation only is authorized for this helper. No fits or paid compute will be launched. The parent selects compute and launch within its remaining cap. Every actual run must use ORX and the inherited `bash run.sh` command; settings are committed, not injected through launch environment variables.
