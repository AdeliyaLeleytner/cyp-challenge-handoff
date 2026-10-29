"""Assemble completed recipes only; never infer a score from partial folds."""
from pathlib import Path
import csv
import datetime
import hashlib
import json

ROOT = Path(__file__).resolve().parent
recipes = [
    ('Native Chemprop + MAE', ROOT.parent / 'cyp-briford-holdouts-20261024/remote/holdouts/scores.json', None),
    ('CheMeleon + MAE', ROOT / 'remote/results/chemeleon_mae/scores.json', None),
    ('Native Chemprop + ST-RAE recipe', ROOT / 'remote/results/scratch_strae_bf16_fp32val_repair1/scores.json', 'scratch'),
    ('CheMeleon + ST-RAE recipe', ROOT / 'remote/results/chemeleon_strae_bf16/scores.json', 'chemeleon'),
]
rows, sources, missing = [], [], []
for name, path, key in recipes:
    if not path.exists():
        missing.append(name)
        continue
    obj = json.loads(path.read_text())
    scores = obj[key] if key else obj
    sources.append({'recipe': name, 'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    for cohort in ('own750', 'briford529'):
        for lane in ('raw', 'native_published_placement'):
            result = scores[cohort][lane]
            if not result['defined']:
                raise ValueError(f'Undefined score: {name}/{cohort}/{lane}')
            row = {'recipe': name, 'cohort': cohort, 'lane': lane, 'macro_ST_RAE': result['macro_ST_RAE']}
            row.update({target: values['ST_RAE'] for target, values in result['endpoints'].items()})
            rows.append(row)
with (ROOT / 'comparison.csv').open('w') as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
manifest = {'updated_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'source_files': sources,
            'incomplete_recipes': missing, 'rows': rows}
(ROOT / 'comparison.json').write_text(json.dumps(manifest, indent=2) + '\n')
lines = ['# Сравнение CheMeleon и нового ST-RAE-лосса', '',
         'Ниже только завершённые ансамбли. ST-RAE: меньше — лучше; 1 соответствует постоянному прогнозу среднего экспериментального значения.', '',
         '| Вариант | Наш holdout (750) | Holdout briford (529) |',
         '|---|---:|---:|']
for name, _, _ in recipes:
    found = [r for r in rows if r['recipe'] == name and r['lane'] == 'raw']
    if len(found) == 2:
        values = {r['cohort']: r['macro_ST_RAE'] for r in found}
        lines.append(f"| {name} | {values['own750']:.6f} | {values['briford529']:.6f} |")
if missing:
    lines.extend(['', 'Ещё нет полного результата: ' + '; '.join(missing) + '.'])
else:
    control = {(r['cohort'], r['lane']): r['macro_ST_RAE'] for r in rows if r['recipe'] == recipes[0][0]}
    if all(r['macro_ST_RAE'] >= control[(r['cohort'], r['lane'])] for r in rows):
        lines.extend(['', '**Исходный native Chemprop + MAE остаётся лучшим из этих четырёх рецептов на обоих holdout, до и после авторской калибровки. Нового полного переобучения и сабмита по этим вариантам не запускали.**'])
lines.extend(['', 'В основной таблице — предсказания до авторского сдвига/масштабирования под тестовый набор. Оба варианта и оценки каждого CYP сохранены в [comparison.csv](comparison.csv).', '',
              'Данные: те же четыре пула официальных и публичных ChEMBL/Veith задач, те же внутренние фолды, отдельное переобучение после исключения каждого внешнего holdout. По 40 моделей на вариант. Внешние holdout пересекаются на 143 молекулах и уже многократно использовались для сравнения.', '',
              'CheMeleon заменяет архитектуру и инициализацию энкодера; прежние настройки оптимизатора сохранены. Новый ST-RAE-рецепт дополнительно меняет нормировку вспомогательных задач, выбор чекпойнта и, после численной ошибки FP16, использует BF16-обучение с FP32-валидацией. Поэтому различия нельзя приписать только предобучению или только формуле лосса.', '',
              'ADMETlab: проверен официальный веб-режим с 120 доступными показателями на трёх молекулах, подготовлены очередь из 32 421 молекулы и полноценный запуск обучения с признаками. Однако первый пакет из 100 молекул получил HTTP 429 без Retry-After. Полной матрицы нет, feature-модель не обучалась и её балл неизвестен. Это блокировка получения данных, а не отрицательный результат метода. Псевдолейблы не считаются экспериментальными измерениями. [Состояние](STATUS.json), [доказательства ответа сервиса](admetlab-access/ACQUISITION_FINAL_STATUS.json), [готовые входные пакеты](admetlab-ready-batches.zip).', '',
              'Все машины, арендованные для этой серии, удалены. Перед удалением основной машины проверены SHA256 всех 2350 сохранённых файлов (11,66 ГБ); расхождений нет. [Проверка восстановления](recovery-certificate.json).', '',
              'Подробный [протокол](COMPARISON_PROTOCOL.md), [происхождение результатов](comparison.json) и сохранённые исходные предсказания доступны рядом. Текущий сабмит на лидерборде этими экспериментами не заменялся.', ''])
(ROOT / 'RESULTS.md').write_text('\n'.join(lines))
print(json.dumps({'completed_recipes': len(sources), 'incomplete': missing, 'report': str(ROOT / 'RESULTS.md')}))
