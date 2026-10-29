# Восстановление на новой машине

## Уровень 1: читать и проверять сохранённые результаты

Python 3.10+ достаточен для `tools/verify_handoff.py` и `tools/restore_assets.py`. GitHub CLI нужен только для скачивания private release, с аккаунтом, которому выдан доступ. Проверка не обращается к leaderboard, не обучает модели и не тратит GPU-бюджет.

```bash
python3 tools/verify_handoff.py
python3 tools/restore_assets.py --list
python3 tools/restore_assets.py --download
python3 tools/verify_handoff.py --all
```

Восстановление проверяет хеш каждого release pack и каждого объекта. Возобновление пропускает уже проверенные файлы. `--prefix archive/artifacts/tdi-20261024/` или другой префикс ограничивает нужное направление. Загрузка проходит по pack целиком; затем cache pack удаляется. Размеры указаны в manifest/summary.json. Для полного независимого копирования без hardlink нужна логическая ёмкость всех путей; hardlink сокращает её до уникальных байтов.

## Уровень 2: перенос конкретного экспериментального дерева

Каждый `worktree/`, `remote-orx/...` и source snapshot относится к своей версии. Не пытайтесь собрать все requirements в одно окружение. H6 CPU, ADME encoder GPU, P7/P7R/P10 Chemprop и TDI имеют разные пины. Их `requirements*.txt`, source hashes, run configs и logs сохранены рядом. Старые абсолютные `/Users/...` и `/workspace/...` пути не будут работать автоматически.

```bash
python3 tools/prepare_runtime.py --source archive/artifacts/cyp-private-v2-20261026/p11 --output .runtime/p11
```

Команда создаёт отдельную runtime-копию, заменяет известные локальные source prefixes в UTF-8 конфигурациях/скриптах и сохраняет список изменений. Зафиксированные архивные файлы не меняются. Пути удалённых GPU (`/workspace/...`) зависят от конкретного запуска: их надо сопоставить с его recovered/stage/output каталогом вручную и проверить asset hashes. Автоматически обходить manifest hash gate нельзя. Для старых git hashes имеются исходные snapshots, но `.git` worktree pointers и полная git-история хоста не перенесены.

## Уровень 3: новые кандидаты

Прежде чем запускать `bash run.sh`, прочитайте локальный config и план: старые entry points могут обучать модели, создавать аренду или отправлять CSV. Для нового эксперимента сделайте отдельную ветку/каталог, укажите dataset/folds/source hashes, точный baseline, budget и список outputs. Не заменяйте старую ветку новым результатом.

Для P11 предварительной оценки сохранён `evaluate_future.py`; необходимы NumPy, pandas и SciPy из совместимого окружения. Пример после подготовки runtime, с собственными genuine outer predictions:

```bash
python3 .runtime/p11/evaluate_future.py   --own own750_predictions.csv --briford briford529_predictions.csv   --blind blind750_predictions.csv --provenance candidate_provenance.json   --output .runtime/candidate_sealed.json
```

Нельзя подавать full-training predictions вместо genuine outer predictions. Скрипт проверяет identity, но не способен доказать по CSV исключение query из обучения; provenance проверяется отдельно. Выход не прогнозирует leaderboard и ничего не отправляет.

Для exact incumbent быстрее и надёжнее использовать сохранённый CSV с фиксированным hash. Повторное обучение даже того же рецепта не гарантирует побитовую идентичность. При передаче выполнена проверка сохранённых файлов и offline-инструментов, а не повторное обучение всей кампании.
