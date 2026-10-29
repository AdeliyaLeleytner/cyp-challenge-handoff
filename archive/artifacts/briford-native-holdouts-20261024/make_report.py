from pathlib import Path
import json,datetime,hashlib
import numpy as np
import pandas as pd
p=Path(__file__).resolve().parent;r=p/'remote/holdouts';scores=json.loads((r/'scores.json').read_text());frozen=json.loads((p/'stage/cohorts.json').read_text())['cohorts']
verified={};details=[];count=0
for name in ['own750','briford529']:
 truth=pd.read_csv(r/name/'truth.csv');assert truth.Molecule_Name.tolist()==frozen[name]['test_ids']
 audit=json.loads((r/name/'exclusion-audit.json').read_text());assert all(x['remaining_held_id_parent_or_connectivity_overlap']==0 for x in audit.values())
 for variant,file in [('raw','cyp-ensemble_activity_submission_native_raw.csv'),('native_published_placement','cyp-ensemble_activity_submission_native_raw_native_strae.csv')]:
  pred=pd.read_csv(r/name/'results'/file).set_index('Molecule_Name').loc[truth.Molecule_Name]
  vals=[]
  for col,endpoint in scores[name][variant]['endpoints'].items():
   m=truth[col].notna().to_numpy();y=truth.loc[m,col].to_numpy();lo=truth.loc[m,col+'_conf_low'].to_numpy();hi=truth.loc[m,col+'_conf_high'].to_numpy();q=pred[col].to_numpy()[m]
   dist=lambda x:np.maximum(lo-x,0)+np.maximum(x-hi,0)
   ratio=dist(q).sum()/dist(y.mean()).sum();assert np.isclose(ratio,endpoint['ST_RAE'],rtol=0,atol=1e-12)
   vals.append(ratio)
  assert np.isclose(np.mean(vals),scores[name][variant]['macro_ST_RAE'],rtol=0,atol=1e-12)
 for member in ['union18','mtaux8','2d6isoform6','2d6single']:
  prep=r/name/'prepared';spec=json.loads((prep/f'{member}.json').read_text());frame=pd.read_csv(prep/f'{member}.csv');assert len(frame)==spec['rows'];assert not(set(frame.molecule_name)&set(frozen[name]['test_ids']))
  for fold in range(5):
   d=r/name/'results'/member/f'fold{fold}';c=json.loads((d/'complete.json').read_text());assert c['status']=='complete'
   for rel,h in c['files'].items():assert hashlib.sha256((d/rel).read_bytes()).hexdigest()==h
   meta=json.loads((d/'metadata.json').read_text());assert meta['training_rows']+meta['validation_rows']==len(frame)
   count+=1;details.append({'cohort':name,**meta})
 verified[name]={'molecules':len(truth),'raw_ST_RAE':scores[name]['raw']['macro_ST_RAE'],'native_placed_ST_RAE':scores[name]['native_published_placement']['macro_ST_RAE'],'independent_numpy_scorer_agrees':True,'exclusion_audit':audit}
assert count==40
(p/'verified-results.json').write_text(json.dumps({'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'model_count':count,'cohorts':verified},indent=2)+'\n')
(p/'model-details.json').write_text(json.dumps(details,indent=2)+'\n')
lines=['# briford: проверка на двух отложенных выборках','','ST-RAE: меньше — лучше. Все40 моделей переобучены; молекулы соответствующего holdout и все их вспомогательные метки исключены из каждого обучающего пула.','','| Вариант | Наш holdout, 750 | Holdout briford, 529 |','|---|---:|---:|']
for v,label in [('raw','Авторский ансамбль до калибровки'),('native_published_placement','С авторской калибровкой под тест конкурса')]:lines.append(f"| {label} | {scores['own750'][v]['macro_ST_RAE']:.6f} | {scores['briford529'][v]['macro_ST_RAE']:.6f} |")
lines+=['','Второй вариант соответствует последнему воспроизведению с опубликованными константами BLIND_MOMENTS, OOF_TO_BLIND и STRAE_MOMENTS. Эти константы рассчитаны автором под публичную часть теста конкурса. На holdout они применены без подгонки по его ответам. Первый вариант показывает те же обученные модели до этого преобразования.','','## По ферментам','','| Выборка | Вариант | CYP1A2 | CYP2C9 | CYP2D6 | CYP3A4 |','|---|---|---:|---:|---:|---:|']
for name in scores:
 for v in scores[name]:
  vals=[scores[name][v]['endpoints'][f'{iso}_pIC50_direct_inhibition']['ST_RAE'] for iso in ['CYP1A2','CYP2C9','CYP2D6','CYP3A4']]
  lines.append('| '+name+' | '+v+' | '+' | '.join(f'{x:.6f}' for x in vals)+' |')
lines+=['','## Проверки и границы вывода','','- Ровно40 чекпойнтов:4 компонента ×5 внутренних разбиений ×2 внешних разбиения; исходные функции обучения и seed 42 сохранены.','- Составы holdout взяты из ранее зафиксированных файлов. Для briford сохранено дополнительное исключение OCNT-1911794.','- Исключены совпадения по ID, нормализованной структуре и InChIKey connectivity; удалены строки целиком со всеми метками.','- Внутренние scaffold-разбиения и веса задач пересчитаны после исключения holdout.','- Официальная ST-RAE независимо перепроверена прямой формулой расстояния до интервалов; совпадение до 1e-12.','- Сохранены предсказания, интервалы, журналы, конфигурации и контрольные суммы всех моделей.','- Две выборки пересекаются по 143 молекулам, поэтому это не две независимые репликации. Это один seed авторского рецепта.','- Предыдущие 0,60238/0,62678 относились к иной адаптации с двумя seeds и обучаемой калибровкой; не выдаются за оценки этого воспроизведения.','- Эти модели и предсказания не отправлялись на лидерборд. Исходный полный сабмишен и его отдельная очередь не изменялись.','','## Происхождение','','ORX run: bad1ee83-ca85-4459-890f-c8b720d88ab6; commit 28933f8. Протокол обсудил Claude Fable 5, консультация 20261024T105326Z-53f5236d: отдельное переобучение, исключение вспомогательных меток, раздельная оценка исходного ансамбля и калибровки. Эти проверки выполнены по файлам и численным расчётам.']
(p/'REPORT_RU.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({n:{v:scores[n][v]['macro_ST_RAE'] for v in scores[n]} for n in scores},indent=2))
