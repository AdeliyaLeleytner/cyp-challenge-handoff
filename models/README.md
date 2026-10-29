# Модели рабочего комплекта

Выбран владельцем рабочий комплект: код, данные и результаты всех направлений; бинарные веса промежуточных и отклонённых моделей исключены. [Полный перечень сохранённых моделей](../manifest/retained-models.json), [перечень исключённых checkpoint](../manifest/omitted-models.json).

- **Direct incumbent:** 20 checkpoint в [incumbent-artifact-copy](../archive/artifacts/cyp-private-v2-20261026/model-audit/incumbent-artifact-copy/): union18, mtaux8, 2d6isoform6, 2d6single × 5 folds. [Provenance](../archive/artifacts/cyp-private-v2-20261026/model-audit/incumbent_preservation.json). Это точная сохранённая основа submission 0,4424575.
- **H6:** четыре `head.joblib`, переносимые `booster.txt`, imputer/feature-order и query predictions в [final-models](../archive/artifacts/goal-20261026/final-locked-h6-output/final-models/). Они сохранены для анализа/воспроизведения уже рассчитанных результатов. Для полного H6 на новых молекулах нужны также corrected-native модели; их отдельные refit checkpoint не включены в сокращённый набор. Для исходных 750 молекул сохранены точные native vectors и raw/served CSV.
- **TDI Jeremy:** full-training seed42 LightGBM и fitted transforms в [baseline/results/full/seed42](../archive/artifacts/tdi-20261024/remote/baseline/results/full/seed42/), плюс сохранённый TabICL classifier checkpoint.
- **TDI Hauser:** `remote/baseline/hauser_native/full/final_tdi.joblib` содержит финальный сериализованный baseline-ансамбль.
- **Зависимости:** замороженный ADME encoder `chemprop_medium.pt`, TabICL classifier и CheMeleon foundation. Исходные лицензии/источники сохраняются. Другие предобученные веса можно получить по сохранённым upstream pins при необходимости.

Дубликаты одного hash могут быть перечислены по нескольким историческим путям, но скачиваются один раз. Все веса требуют предварительного `python3 tools/restore_assets.py --download`. Не загружайте pickle/joblib/checkpoint из неизвестного источника; здесь проверка SHA256 связывает их с сохранённым архивом.
