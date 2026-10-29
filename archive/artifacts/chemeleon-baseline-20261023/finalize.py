"""Export, independently verify and report the already-completed baseline."""
from pathlib import Path
import json,shutil,hashlib,sys,subprocess
import numpy as np,pandas as pd
import matplotlib.pyplot as plt
from orx_figstyle import use_style,save,PALETTE

P=Path(__file__).resolve().parent
receipt=json.loads((P/'execution.json').read_text())
run=Path(receipt['run_directory'])/'repo';src=Path(receipt['source_root'])
results=json.loads((run/'outputs/results.json').read_text())
durable=Path.home()/'.local/share/cyp-inhibition/runs'/receipt['run_id']
durable.mkdir(parents=True,exist_ok=True)
shutil.copytree(run/'outputs',durable/'outputs',dirs_exist_ok=True)
shutil.copytree(run/'data',durable/'data',dirs_exist_ok=True)
for f in ['run.py','modeling.py','config.json','requirements.lock.txt','official_scoring_functions.py','README.md']:
    shutil.copyfile(run/f,durable/f)
shutil.copyfile(Path(receipt['orx_data_dir'])/'run-logs'/f"{receipt['run_id']}.log",durable/'run.log')
previous=results['configuration'].get('previous_run_directory')
if previous:
    previous=Path(previous)
    shutil.copytree(previous/'outputs',durable/'previous_leg'/'outputs',dirs_exist_ok=True)
    oldlog=Path(receipt['orx_data_dir'])/'run-logs'/f"{receipt['initial_run_id']}.log"
    shutil.copyfile(oldlog,durable/'previous_leg'/'run.log')
for f in ['results.json','run-manifest.json','holdout_predictions.csv','bootstrap_scores.npz','history.jsonl']:
    shutil.copyfile(run/'outputs'/f,P/f)
shutil.copyfile(durable/'run.log',P/'training.log')
with (P/'source-snapshot.tar.gz').open('wb') as h:
    subprocess.run(['git','-C',str(src),'archive','--format=tar.gz',receipt['source_commit']],stdout=h,check=True)

truth=pd.read_csv(run/'data/holdout.csv');pred=pd.read_csv(P/'holdout_predictions.csv')
assert truth.Molecule_Name.equals(pred.Molecule_Name)
assert len(truth)==750
checks={};CYP=['CYP1A2','CYP2C9','CYP2D6','CYP3A4']
for c in CYP:
    k=c+'_pIC50_direct_inhibition';mask=truth[k].notna();y=truth.loc[mask,k].to_numpy();p=pred.loc[mask,k].to_numpy()
    lo=truth.loc[mask,k+'_conf_low'].to_numpy();hi=truth.loc[mask,k+'_conf_high'].to_numpy()
    # Independent distance implementation by projecting each prediction onto its interval.
    numerator=np.abs(p-np.clip(p,lo,hi)).sum()
    denominator=np.abs(y.mean()-np.clip(np.full_like(y,y.mean()),lo,hi)).sum()
    direct=float(numerator/denominator);assert abs(direct-results['endpoints'][c]['ST_RAE'])<1e-7
    checks[c]={'independent_ST_RAE':direct,'n':len(y)}
assert hashlib.sha256((P/'holdout_predictions.csv').read_bytes()).hexdigest()==results['prediction_sha256']
best_source=Path(results['selected_checkpoint'])
best=durable/'outputs/checkpoints'/best_source.name
if not best.exists() and previous:best=durable/'previous_leg/outputs/checkpoints'/best_source.name
assert best.exists()
sha=hashlib.sha256(best.read_bytes()).hexdigest()
assert sha==hashlib.sha256(best_source.read_bytes()).hexdigest()
receipt.update({'status':'complete','durable_run_directory':str(durable),'selected_checkpoint':str(best),'checkpoint_sha256':sha})
(P/'execution.json').write_text(json.dumps(receipt,indent=2)+'\n')
(P/'result-verification.json').write_text(json.dumps({'passed':True,'independent_metrics':checks,'checkpoint_sha256':sha},indent=2)+'\n')

use_style();figdir=P/'figures';figdir.mkdir(exist_ok=True)
metrics=pd.read_csv(run/'outputs/training/version_0/metrics.csv')
if previous:
    old_metrics=pd.read_csv(previous/'outputs/training/version_0/metrics.csv')
    old_metrics=old_metrics[old_metrics.epoch<=6]
    metrics=pd.concat([old_metrics,metrics],ignore_index=True)
fig,ax=plt.subplots(figsize=(6.75,2.8),layout='constrained')
for col,label,color in [('train_loss_epoch','Training',PALETTE['blue']),('val_loss','Epoch-selection validation',PALETTE['orange'])]:
    if col in metrics:
        r=metrics.loc[metrics[col].notna(),['epoch',col]].groupby('epoch')[col].last()
        ax.plot(r.index+1,r.to_numpy(),label=label,color=color)
ax.axvline(results['selected_epoch']+1,color='gray',ls='--',lw=.8,label='Selected epoch')
ax.set_xlabel('Epoch');ax.set_ylabel('Masked MSE (standardized targets)');ax.legend()
save(fig,str(figdir/'learning_curve'));fig.savefig(figdir/'learning_curve.png',dpi=180);plt.close(fig)

fig,axes=plt.subplots(2,2,figsize=(6.75,5.8),layout='constrained')
for ax,c in zip(axes.flat,CYP):
    k=c+'_pIC50_direct_inhibition';mask=truth[k].notna();y=truth.loc[mask,k].to_numpy();p=pred.loc[mask,k].to_numpy()
    lo=min(y.min(),p.min());hi=max(y.max(),p.max());pad=.1*(hi-lo)
    ax.scatter(y,p,s=8,alpha=.55,color=PALETTE['blue'],edgecolors='none')
    ax.plot([lo-pad,hi+pad],[lo-pad,hi+pad],color='gray',ls='--',lw=.7)
    ax.set_xlim(lo-pad,hi+pad);ax.set_ylim(lo-pad,hi+pad)
    ax.set_xlabel('Experimental pIC50');ax.set_ylabel('Predicted pIC50')
    ax.text(.03,.96,f'{c}, n={len(y)}',transform=ax.transAxes,ha='left',va='top',fontsize=8)
save(fig,str(figdir/'holdout_predictions'));fig.savefig(figdir/'holdout_predictions.png',dpi=180);plt.close(fig)

split=json.loads((P/'split/manifest.json').read_text());macro=results['macro']
lines=['# CheMeleon: первый baseline CYP Direct Inhibition','',
       'Один локальный запуск на Apple M3/MPS. Официальные direct-inhibition метки; без вспомогательных задач, внешних activity-данных, подбора гиперпараметров и отправки на leaderboard.','',
       '## Результат','',
       f"**MA-ST-RAE: {macro['bootstrap_mean_ST_RAE']:.4f}**, 95%-й bootstrap-интервал [{macro['bootstrap_95CI_ST_RAE'][0]:.4f}; {macro['bootstrap_95CI_ST_RAE'][1]:.4f}]. Меньше — лучше.",
       f"Постоянный прогноз среднего обучающей части: **{macro['train_mean_bootstrap_mean_ST_RAE']:.4f}** при том же расчёте. Обычная macro-MAE модели: **{macro['MAE']:.4f} pIC50**.",'',
       '| CYP | n holdout | ST-RAE, bootstrap mean | MAE, pIC50 | R² | Spearman |','|---|---:|---:|---:|---:|---:|']
for c,r in results['endpoints'].items():lines.append(f"| {c} | {r['n']} | {r['bootstrap_mean_ST_RAE']:.4f} | {r['MAE']:.4f} | {r['R2']:.4f} | {r['Spearman']:.4f} |")
lines += ['',f"Всего выполнено {results['epochs_completed']} эпох; выбран чекпойнт эпохи **{results['selected_epoch']+1}** по внутренней validation. Время обучения: {results['training_seconds']/60:.1f} мин. Число эпох чекпойнта в JSON хранится с нуля.",'',
          '![Кривая обучения](figures/learning_curve.png)','',
          'Кривые показывают обучение и отдельную validation для выбора эпохи; финальный holdout здесь не участвует. Один seed, без интервалов между независимыми обучениями.','',
          '![Предсказания на holdout](figures/holdout_predictions.png)','',
          'Показаны точечные экспериментальные pIC50 и прогнозы на отложенных молекулах. Интервалы измерений учитываются в ST-RAE, но не изображены на этих scatter-графиках.','',
          '## Разбиение и границы интерпретации','',
          f"Fit: {split['n_train']}; validation для выбора эпохи: {split['n_validation']}; итоговый holdout: {split['n_holdout']} молекул. Stereo-stripped parent группы не пересекаются. Holdout выбран по структурам и наличию меток, без численных activity-значений; итоговый прогноз выполнен после выбора чекпойнта.",
          '','| CYP | Медиана ближайшего сходства holdout к fit | Test к полному официальному train |','|---|---:|---:|']
for c in CYP:
    r=split['actual_fit_pool_geometry']['holdout_'+c];lines.append(f"| {c} | {r['median']:.3f} | {r['test_reference_median']:.3f} |")
lines += ['', 'Это приближённое воспроизведение структурного покрытия теста, а не точное совпадение экспериментального распределения. Macro вычисляется по разным наблюдаемым подмножествам четырёх CYP. Bootstrap отражает повторную выборку из данного holdout; он не включает неопределённость выбора split, seed обучения или скрытого leaderboard. Не следует переносить полученный балл напрямую на соревнование.', '',
          '## Исполнение и проверка','',
          f"Источник кода: commit `{receipt['source_commit']}`; orx run `{receipt['run_id']}`. Encoder CheMeleon загружен строго из авторского checkpoint, SHA-256 зафиксирован. Размеры признаков совпали. Скалер обучен только на fit; пропуски замаскированы; encoder действительно изменился при обучении.",
          'Первая техническая попытка прервалась при записи checkpoint из-за заполнения диска. Удалены неиспользуемая среда этой задачи, избыточная вычисленная матрица кэша и недостижимые объекты uv cache; научные данные и checkpoints сохранены. Продолжение восстановило модель, optimizer и scheduler с завершённой 7-й эпохи. Порядок batch после восстановления начинается от настроенного seed; побитное совпадение с непрерывным запуском не заявляется. Выбран лучший validation-checkpoint с учётом обеих частей; holdout оценён только после завершения.',
          'Официальная функция двухсторонней интервальной ST-RAE использована без изменения. После завершения результат независимо пересчитан через проекцию прогноза на экспериментальный интервал; совпадение <1e-7. Скопированный выбранный checkpoint проверен по SHA-256.', '',
          '[Численные результаты](results.json) · [Прогнозы](holdout_predictions.csv) · [Проверка результатов](result-verification.json) · [Журнал обучения](training.log) · [Манифест split](split/manifest.json) · [Исходный commit, архив](source-snapshot.tar.gz)', '',
          f"[Выбранный checkpoint](<{best}>) · [Полный долговременный каталог запуска](<{durable}>)", '',
          '## Независимый совет','',
          'Claude Opus (`claude-opus-5`, автоматический fallback), консультация `20261023T161951Z-59921d7c`: разделить выбор эпохи и итоговый holdout, проверить загрузку весов, scaler и masking, сравнить с train-mean. Codex выполнил эти проверки; вместо предложенного обычного random holdout использован заранее подобранный структурный holdout с опубликованными ограничениями. Совет не является доказательством качества модели.']
(P/'report.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'status':'verified','macro':macro,'durable_checkpoint':str(best),'report':str(P/'report.md')},indent=2))
