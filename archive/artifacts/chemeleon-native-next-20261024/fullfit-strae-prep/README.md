# Готовый шаблон полного ST-refit — пока не выбран и не запущен

Этот каталог находится вне frozen source/worktree. Ни scratch, ни CheMeleon заранее не выбран. Шаблон нужен только если root установит, что конкретный ST-рецепт улучшил оба holdout и выполнено ранее заданное пользователем условие отправки. Это не новый эксперимент и не разрешение обойти это условие.

## Что подготовлено

- `fullfit_strae.py`: готовый модуль для `night/fullfit_strae.py` на новом child-узле **выбранного** рецепта.
- `briford_config.template.json`: initialization/selected_recipe_commit/selection_evidence остаются null, selection_confirmed_by_root=false. С таким файлом запуск намеренно отклоняется.
- `run.sh.template`: сохраняет проектную команду `bash run.sh`; внутри вызывает новый refit-модуль.
- `fullfit_input_manifest.json`: готовая замена `native_input_manifest.json` только на будущем child. Совместима с существующим `night/briford_setup.sh`.
- `stage/`: уже подготовленные файлы для загрузки в `/workspace/cyp-repro/assets/` без удаления существующих файлов.
- `approved-original-input-manifest.json`, `fullfit_input_audit.json`, `fullfit_routine_validation.json`: происхождение и результаты проверок.

## Данные и неизменяемые проверки

Исходные full-таблицы и folds взяты непосредственно из native-воспроизведения briford, которое дало 27-е место. Контрольный input-manifest прочитан из immutable Git commit `38fe110e5a8d17a7bfb48ac78fe12e425da8deeb`. Все 13 исходных файлов совпали по размеру и SHA256. Дополнительно заново сверены все шесть исходных raw-CSV по raw_sha256 из native manifest; они также входят в staged bundle. Проверен CheMeleon checkpoint SHA256.

Новые CSV строить не нужно: полные таблицы уже содержат обе границы CI для всех наблюдаемых primary-меток. Проверены исходные partitions, отсутствие дублированных ID, однократное OOF-покрытие и все 20 fit/validation ST-RAE знаменателей — они конечны и положительны.

| Компонент | Строк | Задач | Folds |
|---|---:|---:|---:|
| union18 | 31 670 | 18 | 5 |
| mtaux8 | 4 905 | 8 | 5 |
| 2d6isoform6 | 23 264 | 6 | 5 |
| 2d6single | 1 493 | 1 | 5 |

TEST — ровно750 уникальных `Molecule_Name` и `SMILES`, без столбцов целевых ответов. Его исходный SHA256 закреплён. Модуль не читает скрытые экспериментальные test-метки. Сохранены исходные публичные joins и документированное пересечение Veith с одной структурной группой TEST; это публичный исторический auxiliary-readout, не скрытый ответ челленджа.

## Как root может использовать пакет после выбора

1. Создать новый ORX child от действительно выбранного завершённого ST-узла. Не менять frozen winner.
2. Скопировать `fullfit_strae.py` в `night/fullfit_strae.py`, шаблон run.sh в run.sh, `fullfit_input_manifest.json` в `native_input_manifest.json`. Остальные core-модули берутся из выбранного parent: `briford_native`, `strae_trainer`, `strae_objective`, `gpu_slots`, `chemeleon_native` и frozen vendor.
3. Заполнить копию config: `initialization` равен только выбранному scratch или chemeleon; записать полный commit выбранного рецепта и ссылку/хеш проверенного отчёта о сравнении в `selection_evidence`; установить `selection_confirmed_by_root=true`. Это фиксация уже принятого решения root, не новая просьба разрешения к пользователю.
4. Загрузить **содержимое** `stage/` в `/workspace/cyp-repro/assets/` без `--delete`, сохранить distinct output_dir, затем commit и запуск только через ORX. GPU0–7 используют уже существующие shared flock leases, FD наследуются worker'ами. Lifecycle самой арендованной машины и денежные лимиты остаются ответственностью root.

Модуль готовит20 новых моделей на полных источниках. Сохраняются исходные full-pool scaffold-folds, seed42, full-source native nominal task weights и остальные native гиперпараметры. Не копируются веса задач из outer-holdout моделей: fit-specific D/sigma/n пересчитывает выбранный ST-trainer. Обучение BF16, validation FP32, тот же exact-ST loss/aux-budget/checkpoint monitor; vendor не меняется.

Этот шаблон предназначен именно для текущих C/D ST-рецептов 18/8/6/1 без дополнительных ADMETlab-признаков. Для другого состава входов его нельзя молча переиспользовать.

## Результат и границы

После20 моделей вызывается неизменённый native collect: усреднение folds/компонентов, OOF-корреляции, исходная published placement и официальный CSV-validator. Итог будет записан под output_dir/results/, а provenance — в fullfit_complete.json. CSV содержит750 строк. Модуль **ничего не загружает на лидерборд**, не выбирает рецепт и не изменяет submission ledger.

Полные checkpoint'ы ещё не обучены; scores/прогнозов нового refit пока нет. Подготовка и проверки были только чтением/копированием утверждённых данных и CPU-проверкой схем/численных знаменателей. В этой подзадаче не создавались ORX-узлы, не менялись исходные ветки, не запускались compute/rental.
