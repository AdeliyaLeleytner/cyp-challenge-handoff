# Shared findings
Baselineaudit complete. Best-open source found; benchmarkreconstruction pending. ExistingCYP-adaptedTFMfeatures strongestcurrentcomponents. AddingdirectCheMeleon yieldssmallunstablegain mostlyoldweightreshuffle. No newcampaignmodelsrunyet.

## Next levers
TabICLv2;Monroe;multifamilyfingerprints;Tox21CYP;BindingDBnative;lossalignment;neighborresidualcorrection.

Claude consultation 20261023T205706Z-653191c2 exited0; actual primary claude-opus-5, automatic fallback=True (not Opus5.5). Advice: preserve reference placement, seed-pair comparisons, audit pretraining overlap, try interval-width modeling. Codex accepts train-only calibration and seed replication; rejects asserting historical approximate counts or ensemble dominance must reproduce exactly on new holdouts. Outcome is empirical.

Source correction to advisor: oof_pearson itself scales by OOF_TO_BLIND and then BLIND_MOMENTS; it is not fully board-free. Those constants are excluded. Report raw and train-OOF affine ST-RAE calibration for reconstructed reference. This is source-verified, not rejection of calibration.

Peer audits: outer train/validation/test ID,parent,scaffold separation andreference2/4member averagingverified. InnerOOF neuralpredictions use validation labels forbestepochselection; crossfitcalibrationisnotfullynested, and OOFsinglefold vsouter5bag spread differs. Thus development calibration scorecanbeoptimistic; outerlabelsremainexcluded. Metadata query_labels_usedFalse refers onlypredictioninputarrays anddoesnotdescribeepochselection foroverlappinginnervalidation. Readouts explicitly qualifythis; noouterleakfound.


Final campaign update,2026-10-24T00:13Z:57namedmethods/122evaluations, paired gatePASS,40finalneuralmodels, one server-accepted submission at00:10:09UTC asAdeliyaLL-CYP; officialscorepending. BothVastinstances destroyedafterSHA256exportverification; noactivecampaignprocesses. See REPORT_RU.md andFINAL_STATUS.json for final evidence andqualifications.
