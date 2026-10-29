# Данные для продолжения

Начните с [описания данных](../docs/DATA.md). Основные точки входа:

- [Официальный Direct train](../archive/artifacts/cyp-private-v2-20261026/p11/evidence/official_train.csv) и [blind query](../archive/artifacts/cyp-private-v2-20261026/p11/evidence/official_blind.csv).
- [ADMETlab: проверенная таблица всех 32 421 исходов](../archive/artifacts/goal-20261026/audited-dataset/admetlab-32421-audited-features.csv), [manifest](../archive/artifacts/goal-20261026/audited-dataset/manifest.json), [пояснения](../archive/artifacts/goal-20261026/audited-dataset/README.txt).
- [Prepared native datasets](../archive/artifacts/cyp-private-v2-20261026/model-audit/incumbent-artifact-copy/prepared/): точные наборы для четырёх native-компонентов.
- [TDI baseline prepared data](../archive/artifacts/tdi-20261024/remote/baseline/prepared/); provenance и число известных меток — в [TDI report](../archive/artifacts/tdi-20261024/REPORT.md).
- [Сырые ADMETlab ответы и объединённые результаты](../archive/admetlab-collection/results/). Учёт missing/rejected/ineligible сохраняется; predicted properties не становятся экспериментальными метками.

Крупные CSV/массивы восстанавливаются из закрытого release. Размер official Direct train не равен размеру TDI train или полного external pool. Не переносите splits между ними без identity audit.
