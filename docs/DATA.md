# Данные и единицы анализа

| Набор | Размер/смысл | Где искать |
|---|---|---|
| Direct official train | 4 905 молекул; пропуски по четырём CYP | `archive/artifacts/cyp-private-v2-20261026/p11/evidence/official_train.csv` |
| Blind query | 750 молекул; без скрытых меток | `archive/artifacts/cyp-private-v2-20261026/p11/evidence/official_blind.csv` |
| Полный prepared pool | 32 421 уникальная структура, включая official и external | `archive/artifacts/goal-20261026/audited-dataset/` |
| ADMETlab eligible | 32 418 строк, 120 предсказанных свойств | `admetlab-32421-audited-features.csv` в audited-dataset |
| Source-supervision eligible | 32 392 после отдельной политики источников | `source-supervision-policy.json` и quarantine |
| P7/P7R рабочая матрица | 31 641 строка конкретного staged эксперимента | `archive/artifacts/cyp-private-v2-20261026/p7*/stage/` и manifests |
| TDI official train | 6 145 молекул, 2 частично наблюдаемых бинарных endpoint | `archive/artifacts/tdi-20261024/remote/` и DATA.md |

Разные размеры относятся к разным сущностям и политикам; 32 421 — не число экспериментальных pIC50-меток и не размер каждого training run. У четырёх добавленных H6 readout наблюдалось 1 412/1 285/1 493/2 335 официальных меток (1A2/2C9/2D6/3A4).

Два сервисных запроса, Cl и N, были явно отклонены. Для одной внешней Sb-структуры численные значения существуют, но returned graph не подтверждён: она не допущена как feature row. Отдельное точное внутреннее proton-transfer преобразование разрешено как представление признаков после проверки; это не установление assay microstate и не разрешение слить экспериментальные идентичности. Все 5 655 official rows полностью покрыты и прошли проверку.

Сохраняются request/service SMILES, исходные aliases, outcome ledger, provenance, flags и missingness. Не заменять отсутствующие метки нулями. Сырые ADMETlab ответы лежат в `archive/admetlab-collection/`; проверенные экспортные таблицы — в `goal-20261026/audited-dataset`. Для анализа обычно достаточно последних, сырые ответы нужны для аудита.

P7R unit repair применяется к производной feature matrix, не переписывает сырой cache. Полные точные правила и row/cell hashes находятся в `cyp-private-v2-20261026/p7r/` и связанной chemical review; не вводить произвольную нормализацию вместо сохранённого исправления.

Own750 и reconstructed-briford529 — development cohorts с пересечением 143. Второй является нашей реконструкцией, не восстановленным авторским split. Исходный native и corrected-native различаются: сохраняйте названия и provenance. Часть исторических native components использует свои fold assignments и legacy supervision; чистый downstream nesting не исправляет задним числом upstream limitations.

Основные отчёты: [BIOCHEM_DATA_AUDIT](../archive/artifacts/cyp-private-v2-20261026/BIOCHEM_DATA_AUDIT.md), [external measurement availability](../archive/artifacts/cyp-private-v2-20261026/EXTERNAL_MEASUREMENT_AVAILABILITY.md), [data policy](../archive/artifacts/goal-20261026/audited-dataset/README.txt), [TDI report](../archive/artifacts/tdi-20261024/REPORT.md).
