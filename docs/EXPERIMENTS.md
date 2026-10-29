# Эксперименты: что повторять, что считать отрицательным результатом

Все приведённые значения относятся к сохранённым результатам конкретных запусков, а не к свежему повторному обучению при передаче. ST-RAE меньше — лучше; TDI MCC больше — лучше.

| Направление | Проверенный результат / решение | Доказательства в `archive/artifacts/` |
|---|---|---|
| Native reproduction | Лучший сохранённый submission 0,4424575; 20 моделей, четыре task-набора × пять folds | `briford-native-reproduction-20261024/REPORT_RU.md`, `p11/evidence/native-csv.csv` в private-v2 |
| CheMeleon, ранние ансамбли, reciprocal | Предыстория и baseline comparison; не подменять последним native | `chemeleon-baseline-20261023/`, `reciprocal-comparison-20261023/`, `overnight-autoresearch-20261023/` |
| H6 | own750 raw ST 0,615706 vs corrected-native 0,620777; briford529 0,579888 vs 0,642309. Leaderboard ухудшился до 0,4616 | `goal-20261026/submission-preparation/MODEL_REPORT_FINAL_LOCAL.md`, `submission-publication/README.md` |
| H7 | Не продвинут; сохраняется как проверенная альтернативная simplex-ветка | `goal-20261026/h7-simplex/` |
| P1/P2 | Serving-map replay не даёт устойчивого rescue; локальные cohorts отличаются от dense blind geometry | `cyp-private-v2-20261026/p1/`, `p2/` |
| P3 | MAE/uniform 0,656206; interval/uniform 0,661896; MAE/CI 0,700939; interval/CI 0,701533 | `cyp-private-v2-20261026/p3/RESULTS.md` |
| P4/P6 | Assay-context/censor и direct/active audits; ограниченная сопоставимость, описательные выводы | `cyp-private-v2-20261026/p4-data/REPORT.md`, `p6/RESULTS.md` |
| P5/P5b | Разделение native base × feature эффекта; anchored candidate всё равно ухудшил blind score до 0,4679 | `cyp-private-v2-20261026/p5b/candidate/READOUT.md`, dispatch receipt |
| P7 | Прямое ADMET120 fusion: OOF ST 0,674456 → 0,702571; все пять macro метрик хуже | `cyp-private-v2-20261026/p7/RESULTS.md` |
| P7D | Inference-only checkpoint diagnosis; dependence under input shift, не доказанная причинность | `cyp-private-v2-20261026/p7/diagnosis/DIAGNOSIS_SYNTHESIS.md` |
| P7R | Fresh control 0,672018; original fusion 0,715618; masked 0,712342; repaired 0,707574. Repair не закрывает разрыв | `cyp-private-v2-20261026/p7r/RESULTS.md` |
| P8a/P8b/P8c | Training-only observation maps подготовлены; graph condition-routing P8c был отложен в пользу P7R | `cyp-private-v2-20261026/p8a/`, `p8b/`, `p8c/` |
| P9 | Atom-JEPA/ADME banks, standalone и nested ensemble; небольшие разнонаправленные эффекты, без продвижения | `cyp-private-v2-20261026/p9-tabicl/READOUT.md`, `p9-source-bundle/READOUT.md`, `p9-nested/READOUT.md` |
| P10 | Continuation/all18 vs primary4: zero controls ~0,6586/0,6577; repaired fusion ~0,7074/0,7092. Нет свидетельства rescue через этот контраст | `cyp-private-v2-20261026/p10/readout/READOUT.json` |
| P11 | Аудит validation/calibration, предварительный proxy own750 raw MAE; базовые модели не обучались | `cyp-private-v2-20261026/p11/VALIDATION_PROTOCOL.json`, report.html |
| TDI | Jeremy native MCC 0,300550 / 0,262583 на двух cohorts; ни один вариант не лучше обоих, отправки нет | `tdi-20261024/REPORT.md`, `validation-final.json` |

Разные P7/P7R/P10 control scores относятся к разным зафиксированным запускам; нельзя объединять их в одну парную оценку. Интервалы scaffold bootstrap условны на сохранённых предсказаниях и не учитывают весь model selection / training-seed uncertainty.

P9 post-final-normalization/PCA96 branch не эквивалентна опубликованной pre-normalization/PCA128 ветке: отдельно сохранена source-fidelity проверка. Отрицательный результат одной ветки не доказывает бесполезность представления вообще.
