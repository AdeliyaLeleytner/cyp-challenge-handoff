"""Read-only scoring of saved predictions; no model fitting or prediction changes."""
from pathlib import Path
import hashlib, importlib.util, json
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, kendalltau, pearsonr

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
SCORER = BASE / 'remote-orx/runs/3568687e-a9d3-4f04-a047-43b8c6e9af0b/repo/official_scoring_functions.py'
spec = importlib.util.spec_from_file_location('official', SCORER)
official = importlib.util.module_from_spec(spec); spec.loader.exec_module(official)
TARGETS = [f'{x}_pIC50_direct_inhibition' for x in ['CYP1A2','CYP2C9','CYP2D6','CYP3A4']]
RECIPES = {
    'Chemprop MAE': BASE.parent/'cyp-briford-holdouts-20261024/remote/holdouts',
    'CheMeleon MAE': BASE/'remote/results/chemeleon_mae',
    'Chemprop ST': BASE/'remote/results/scratch_strae_bf16_fp32val_repair1/scratch_exact_strae',
    'CheMeleon ST': BASE/'remote/results/chemeleon_strae_bf16/chemeleon_exact_strae',
}
LANES = {'raw':'cyp-ensemble_activity_submission_native_raw.csv',
         'placed':'cyp-ensemble_activity_submission_native_raw_native_strae.csv'}
MAIN = ['ST_RAE','MAE','R2','Spearman','Kendall']
EXTRA = ['RMSE','Pearson','RAE','ICW_RAE','W_RAE_threshold4_weight025','CI_hit_fraction','bias']
def metrics(y, p, lo, hi, extras=False):
    var = np.sum((y-y.mean())**2)
    result = dict(ST_RAE=float(official.rae_soft_threshold_absolute_error(y,p,y_true_lower=lo,y_true_upper=hi)),
                  MAE=float(np.abs(p-y).mean()), R2=float(1-np.sum((p-y)**2)/var),
                  Spearman=float(spearmanr(y,p).statistic), Kendall=float(kendalltau(y,p).statistic))
    if extras:
        result.update(RMSE=float(np.sqrt(np.mean((p-y)**2))), Pearson=float(pearsonr(y,p).statistic),
                      RAE=float(official.rae(y,p)),
                      ICW_RAE=float(official.rae_inverse_confidence_weighting(y,p,y_true_lower=lo,y_true_upper=hi)),
                      W_RAE_threshold4_weight025=float(official.rae_weight_below_threshold(y,p)),
                      CI_hit_fraction=float(((p>=lo)&(p<=hi)).mean()), bias=float((p-y).mean()))
    return result

records=[]; macros=[]; provenance=[]; bootstrap=[]
for cohort in ['own750','briford529']:
    truth = pd.read_csv(RECIPES['Chemprop MAE']/cohort/'truth.csv').set_index('Molecule_Name')
    assert truth.index.is_unique
    rng=np.random.default_rng(20261025)
    draws=rng.integers(0,len(truth),size=(1000,len(truth)))
    for recipe,root in RECIPES.items():
        other=pd.read_csv(root/cohort/'truth.csv').set_index('Molecule_Name').loc[truth.index]
        pd.testing.assert_frame_equal(other,truth)
        for lane,filename in LANES.items():
            path=root/cohort/'results'/filename
            pred=pd.read_csv(path).set_index('Molecule_Name')
            assert pred.index.is_unique and set(pred.index)==set(truth.index)
            pred=pred.loc[truth.index]
            assert np.isfinite(pred[TARGETS].to_numpy()).all()
            provenance.append({'recipe':recipe,'cohort':cohort,'lane':lane,'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
            bytarget=[]; arrays=[]
            for target in TARGETS:
                y=truth[target].to_numpy();p=pred[target].to_numpy();lo=truth[target+'_conf_low'].to_numpy();hi=truth[target+'_conf_high'].to_numpy()
                mask=np.isfinite(y);assert np.isfinite(lo[mask]).all() and np.isfinite(hi[mask]).all() and (lo[mask]<=hi[mask]).all()
                values=metrics(y[mask],p[mask],lo[mask],hi[mask],True)
                records.append(dict(recipe=recipe,cohort=cohort,lane=lane,target=target,n=int(mask.sum()),**values))
                bytarget.append(values);arrays.append((y,p,lo,hi))
            macro={key:float(np.mean([x[key] for x in bytarget])) for key in MAIN+EXTRA}
            macros.append(dict(recipe=recipe,cohort=cohort,lane=lane,**macro))
            # Preserve shared molecule resampling across targets, models and output lanes.
            samples=[]
            for ix in draws:
                per=[]
                for y,p,lo,hi in arrays:
                    yy,pp,ll,hh=y[ix],p[ix],lo[ix],hi[ix];m=np.isfinite(yy)
                    per.append(metrics(yy[m],pp[m],ll[m],hh[m]))
                samples.append([np.mean([v[k] for v in per]) for k in MAIN])
            samples=np.asarray(samples);assert np.isfinite(samples).all()
            for j,key in enumerate(MAIN):
                bootstrap.append(dict(recipe=recipe,cohort=cohort,lane=lane,metric=key,estimate=macro[key],
                    lower95=float(np.quantile(samples[:,j],.025)),upper95=float(np.quantile(samples[:,j],.975)),
                    bootstrap_mean=float(samples[:,j].mean()),bootstrap_sd=float(samples[:,j].std(ddof=1))))
            print(json.dumps({'recipe':recipe,'cohort':cohort,'lane':lane,**{k:round(macro[k],5) for k in MAIN}}),flush=True)
pd.DataFrame(records).to_csv(HERE/'per-cyp.csv',index=False)
pd.DataFrame(macros).to_csv(HERE/'macro.csv',index=False)
pd.DataFrame(bootstrap).to_csv(HERE/'bootstrap-95.csv',index=False)
(HERE/'provenance.json').write_text(json.dumps({'inputs':provenance,'scorer_sha256':hashlib.sha256(SCORER.read_bytes()).hexdigest(),
    'bootstrap':'1000 molecule-level paired resamples within each cohort, seed20261025; all denominators recomputed; percentile95 intervals. Local uncertainty, not exact leaderboard bootstrap replay.',
    'aggregation':'Unweighted mean of four target-level metrics; supplementary RMSE is mean target RMSE, not pooled RMSE.',
    'no_refit':True},indent=2)+'\n')
lines=['# Все метрики сохранённых ансамблей','',
       'Точечные оценки на тех же двух holdout. ST-RAE и MAE: меньше лучше; R², Spearman и Kendall: больше лучше. Каждый CYP имеет одинаковый вес.',
       'Ничего не переобучалось и не калибровалось заново. Эти holdout уже использовались при разработке и пересекаются на 143 молекулах.','']
for cohort in ['own750','briford529']:
    for lane in LANES:
        lines += [f'## {cohort} — {lane}','','| Модель | ST-RAE ↓ | MAE ↓ | R² ↑ | Spearman ↑ | Kendall ↑ |','|---|---:|---:|---:|---:|---:|']
        for row in macros:
            if row['cohort']==cohort and row['lane']==lane:lines.append('| '+row['recipe']+' | '+' | '.join(f'{row[k]:.4f}' for k in MAIN)+' |')
        lines.append('')
lines += ['[Все CYP и дополнительные метрики](per-cyp.csv) · [Макросредние](macro.csv) · [95% bootstrap-интервалы](bootstrap-95.csv) · [Происхождение и методика](provenance.json)','',
    'Дополнительные диагностические метрики: RMSE, Pearson, обычная RAE, inverse-confidence RAE, RAE с весом0,25 ниже pIC50=4, доля попаданий в экспериментальный интервал и среднее смещение. Это не дополнительные критерии конкурсного рейтинга. Доля попаданий в экспериментальный CI не является калибровкой неопределённости модели.','',
    'Официальные пять метрик и роль ST-RAE проверены по [конфигурации конкурса](https://huggingface.co/spaces/openadmet/cyp-challenge/blob/main/config.py).']
(HERE/'RESULTS.md').write_text('\n'.join(lines)+'\n')
