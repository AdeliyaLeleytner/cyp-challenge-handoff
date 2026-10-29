СРАВНЕНИЕ CYP-ДАННЫХ — 24 октября 2026

Начать с comparison.html: большой отчёт с таблицами и 10 встроенными векторными графиками.
Excel: outputs/01a16d31-5fea-7710-b157-221709646aea/CYP_dataset_comparison.xlsx — 12 листов.
Все PNG — просмотровые версии; PDF и SVG в figures сохраняют векторную геометрию.

Это аналитическое сравнение, не новый обучающий датасет.
15 основных представлений данных дополняются 5 сырыми архивами. Сырые и использованные версии пересекаются и не суммируются.

Новизна зависит от базы сравнения:
- официальные источники + использованные внешние поднаборы: 4491 новых parent-SMILES или3826 InChIKey14 безTEST;
- весь доступный архив, включая скачанные, но не использованные записи/столбцы: 3927 новых parent-SMILES или3323 InChIKey14 безTEST.

Для полного архива используйте user_rows_all_archive_membership.csv.gz и novelty_vs_all_raw_archives.csv.
Для основных15представлений — all_sources_long.csv.gz и user_rows_annotated.csv.gz.
user_novel_structures.csv относится к первому, более узкому сравнению. Он не является готовым списком для обучения.

Единицы y, правила task/y_type/spread/any_preinc и происхождение каждого агрегата нового CSV не документированы.
Границы не заменены точками; TDI не выводится из одного флага; совпадения структур не объявлены утечкой скрытых измерений.
Статистики описательные. Качество новой модели не измерялось.

Источники:
https://supercowpowers.github.io/workbench/blogs/cyp_challenge/
https://github.com/lachrymator/openadmet-cyp-challenge-public/tree/6afb664e6fb22c516952e020273ba91442f426db
https://chembl.gitbook.io/chembl-interface-documentation/frequently-asked-questions/chembl-data-questions
https://pubmed.ncbi.nlm.nih.gov/27063220/
Полные сторонние веб-страницы в архив не включены; ссылки и результаты проверок сохранены.

Повторение расчётов в исходном рабочем окружении:
analyse.py -> extend_analysis.py -> identity_followup.py -> diagnostics.py -> raw_inventory.py -> all_raw_geometry.py
Затем figures/plot_comparison.py, figures/plot_density.py, build_payload.py, build_workbook.mjs, build_report.py, verify_deliverables.py.
Пути к исходным локальным файлам и SHA256 находятся в source_manifest.json. Исходники не изменялись.
Для повторного построения графиков достаточно таблиц в tables. Использованы RDKit, numpy, pandas, matplotlib; Excel создан Artifact Tool.

В qa/final_validation.json: проверка сохранённого XLSX, отсутствие error-cells, формулы, хеши входов, ссылки и уникальность HTML-id.
Визуально проверены листы Excel и графики. Браузерный UI недоступен для автоматической проверки; работа сортировки в конкретном браузере не заявлена как протестированная.
