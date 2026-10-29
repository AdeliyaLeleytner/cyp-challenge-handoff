# Карта архива

Каталоги сохраняют исторические имена и взаимное расположение. Для больших файлов сначала восстановите release.

| Каталог | Назначение |
|---|---|
| [cyp-private-v2-20261026](../archive/artifacts/cyp-private-v2-20261026/) | Последняя приватная кампания P1–P11, restore, chemistry и validation audits |
| [goal-20261026](../archive/artifacts/goal-20261026/) | Полный ADMETlab audit, corrected-native, H6/H7, финальные головы и submission evidence |
| [tdi-20261024](../archive/artifacts/tdi-20261024/) | Отдельная TDI-классификация, baseline/candidate/GNN/assay-stack |
| [briford-native-reproduction-20261024](../archive/artifacts/briford-native-reproduction-20261024/) | Исторический native, fullfit и отправка 0,4425 |
| [briford-native-holdouts-20261024](../archive/artifacts/briford-native-holdouts-20261024/) | Парная проверка native на own750 и reconstructed529 |
| [chemeleon-native-next-20261024](../archive/artifacts/chemeleon-native-next-20261024/) | Loss/precision/features и подготовка ADMETlab |
| [overnight-autoresearch-20261023](../archive/artifacts/overnight-autoresearch-20261023/) | Ранний широкий поиск, reference, calibration, исходные assets/weights |
| [admetlab-auto](../archive/artifacts/admetlab-auto/) | Код коллектора; не запускать сеть без нового решения |
| [admet500-pilot-20261025](../archive/artifacts/admet500-pilot-20261025/) | Первый пилот ADMETlab на 500 молекулах |
| [admetlab-labeling-skill-check](../archive/artifacts/admetlab-labeling-skill-check/) | Проверка батчей и merged outputs |
| [smiles-500](../archive/artifacts/smiles-500/) | Подготовленные запросы по 500 структур |
| [strategy-20261024](../archive/artifacts/strategy-20261024/) | Сохранённые частные кандидаты и стратегия |
| [chemical-space-audit-20261023](../archive/artifacts/chemical-space-audit-20261023/) | Геометрия химического пространства и серии аналогов |
| [data-comparison-20261024](../archive/artifacts/data-comparison-20261024/) | Сравнение источников/таблицы/HTML/workbook |
| [cyp-review](../archive/artifacts/cyp-review/) | Научный разбор endpoint/данных/ESM |
| [leaderboard-review-20261023](../archive/artifacts/leaderboard-review-20261023/) | Исторический обзор публичных решений |
| [reciprocal-comparison-20261023](../archive/artifacts/reciprocal-comparison-20261023/) | Взаимные сравнения на согласованных cohorts |
| [ensemble-add-chemeleon-20261023](../archive/artifacts/ensemble-add-chemeleon-20261023/) | Вклад CheMeleon в ансамбль |
| [chemeleon-baseline-20261023](../archive/artifacts/chemeleon-baseline-20261023/) | Первый standalone CheMeleon baseline |

[Полный сырой сбор ADMETlab](../archive/admetlab-collection/) добавлен отдельно из рабочего каталога Downloads. Аутентификационные материалы исключены.

Список файлов и контрольные суммы: [manifest/files.jsonl](../manifest/files.jsonl). Исходные machine paths сопоставлены в [path-map.json](../manifest/path-map.json). Имеются повторные snapshots одного кода: выбирайте snapshot по source/run manifest конкретного результата.

Дополнительно сохранены [точные Git-снимки исходников](../archive/git-snapshots/) и [локальные ORX-запуски](../archive/local-orx-runs/), включая исходные CheMeleon checkpoint. Связь версий с рабочими деревьями: [git-snapshots.json](../manifest/git-snapshots.json).
