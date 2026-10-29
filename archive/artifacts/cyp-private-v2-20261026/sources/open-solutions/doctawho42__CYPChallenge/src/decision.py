"""Байесовски-оптимальная точечная оценка под ST-RAE.

ell(yhat) = (yhat - H)_+ + (L - yhat)_+ , где (L,H) -- случайный credible interval
будущего измерения. R выпукла, R'(y) = F_L(y) + F_H(y) - 1, значит оптимум --
медиана равновесной смеси распределений L и H: пулим сэмплы lo и hi, берём медиану.

Проверяем на настоящих данных: тот же предиктор, разные решающие слои.
"""
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from cyppaths import D, RES, tutorial
tutorial()
import numpy as np, pandas as pd, json, sys
from evaluation.custom_scoring_functions import rae_soft_threshold_absolute_error as strae
from sklearn.ensemble import HistGradientBoostingRegressor
CYPS=["CYP1A2","CYP2C9","CYP2D6","CYP3A4"]
z=np.load(D+"feats.npz"); X=np.hstack([z["FP"],z["DESC"],z["MECH"]])
rows=pd.read_csv(D+"rows.csv")
tr=pd.read_csv(D+"cyp-challenge-TRAIN_inhibition.csv").set_index("Molecule_Name").loc[rows.Molecule_Name].reset_index()
oof=json.load(open(RES+"preds/oof.json"))

# те же фолды, что в абляции
from cypsplit import butina_folds
fold,_=butina_folds(list(rows.SMILES))

rng=np.random.default_rng(0); S=400
res=[]
for c in CYPS:
    col=f"{c}_pIC50_direct_inhibition"
    m=tr[col].notna().to_numpy()
    y=tr.loc[m,col].to_numpy(); lo=tr.loc[m,col+"_conf_low"].to_numpy(); hi=tr.loc[m,col+"_conf_high"].to_numpy()
    yhat=np.array(oof[f"FP+DESC+MECH|{c}"])                 # тот же предиктор во всех вариантах
    fi=fold[m]
    a_hat=np.zeros(len(y)); b_hat=np.zeros(len(y)); sig=np.zeros(len(y))
    Xi=X[m]
    for f in range(5):
        trn,te=fi!=f,fi==f
        if te.sum()==0: continue
        # полуширины полосы как функция признаков, обучены только на train-фолдах
        a_hat[te]=HistGradientBoostingRegressor(max_iter=200,learning_rate=0.06,random_state=0).fit(Xi[trn],(y-lo)[trn]).predict(Xi[te])
        b_hat[te]=HistGradientBoostingRegressor(max_iter=200,learning_rate=0.06,random_state=0).fit(Xi[trn],(hi-y)[trn]).predict(Xi[te])
        sig[te]=np.std(y[trn]-yhat[trn])                    # гомоскедастичная предиктивная сигма
    a_hat=np.clip(a_hat,0.02,None); b_hat=np.clip(b_hat,0.02,None)

    # решающий слой: пулим сэмплы lo и hi, берём медиану
    eps=rng.standard_normal((S,len(y)))
    ys=yhat[None,:]+sig[None,:]*eps
    los=ys-a_hat[None,:]; his=ys+b_hat[None,:]
    pooled=np.concatenate([los,his],axis=0)
    y_bayes=np.median(pooled,axis=0)
    # для сравнения: сдвиг на половину асимметрии без сэмплирования (аналитический предел sigma->0)
    y_shift=yhat+(b_hat-a_hat)/2

    f_=lambda p: round(strae(y,p,y_true_upper=hi,y_true_lower=lo),4)
    res.append(dict(cyp=c, raw=f_(yhat), bayes=f_(y_bayes), shift=f_(y_shift),
                    mean_move=round(float(np.mean(y_bayes-yhat)),3),
                    move_inactive=round(float(np.mean((y_bayes-yhat)[yhat<4])),3),
                    move_active=round(float(np.mean((y_bayes-yhat)[yhat>=5])),3),
                    n_inactive=int((yhat<4).sum())))
r=pd.DataFrame(res)
r.loc[len(r)]=dict(cyp="MACRO",**{k:round(r[k].mean(),4) for k in r.columns if k!="cyp"})
print(r.to_string(index=False))
print("\nraw = сырое предсказание модели; bayes = медиана пула {lo_s, hi_s}; shift = аналитический предел")
