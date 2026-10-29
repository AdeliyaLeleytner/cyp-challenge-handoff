# Отправки и защищённый incumbent

| Вариант | Наблюдённый MA-ST-RAE | Точный CSV в P11 evidence |
|---|---:|---|
| Ранний ensemble + OOF calibration | 0,7521205 | `adapted-csv.csv` |
| Исходный Briford-native | **0,4424575** | `native-csv.csv` |
| Corrected/refit native + H6 | 0,4616 | `H6-csv.csv` |
| Исходный native + H6 | 0,4679 | `anchored-csv.csv` |
| Восстановление исходного native 27 октября | 0,4425 | тот же `native-csv.csv` |

[Все четыре файла и исходные квитанции](../archive/artifacts/cyp-private-v2-20261026/p11/evidence/). [Таблица локальных и blind результатов](../archive/artifacts/cyp-private-v2-20261026/p11/submission-local-comparison.csv). [Последнее восстановление](../archive/artifacts/cyp-private-v2-20261026/restore-20261027/processed-result.json).

Hashes:

- Native: `349165ecf50906e43a27f12dee97891a92cda59e798db614ef27a7c920c38a37`.
- H6: `91fa8bf0870f68071b04183166b1507c20001d04f3ae3fb5f4d055618fff98c7`.
- Anchored: `6807263f0ccadcb31aa28a5c54653608e12271939a2490a2404d4353aeb0e16d`.

Leaderboard показывает часть скрытого теста. Таблица не является full-test оценкой. Его публичная строка не содержит hash загруженного файла: связь устанавливается локальной immutable intent/receipt вместе с alias и временем отправки. Ранги исторические и меняются.

Удалённый публичный gist не восстанавливается этим репозиторием. Старые отчёты с требованием публичной ссылки — история старого transport contract; новый участник перед любой будущей отправкой должен заново проверить правила и обсудить возможное требование раскрытия метода с владельцем. Создание этого приватного handoff не разрешает новые leaderboard submissions или публичные публикации.
