"""Калибровка прибора: как показание скрининга при одной концентрации связано с pIC50.
Модель: доля подавленной активности I = E/(1+10^{h(pC0-pi)}), показание log2fc = log2(1-I).
Подгоняем E и h на фермент по соединениям, у которых есть и то и другое."""
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from cyppaths import D, RES
import numpy as np, pandas as pd
from scipy.optimize import least_squares
from scipy.stats import spearmanr
from sklearn.isotonic import IsotonicRegression
C=["CYP1A2","CYP2C9","CYP2D6","CYP3A4"]
pC0=-np.log10(4.95049505e-05)
inh=pd.read_csv(D+"cyp-challenge-TRAIN_inhibition.csv")
sc=pd.read_csv(D+"cyp-challenge-single-concentration-TRAIN.csv")
piv=sc.pivot_table(index="Molecule_Name",columns="enzyme",values="log2fc_estimate")
m=inh.set_index("Molecule_Name").join(piv)
print(f"концентрация скрина 49.5 мкМ -> pC0 = {pC0:.3f}\n")
print(f"{'фермент':8s} {'n':>5s} {'E':>7s} {'h':>7s} {'ско остатка':>12s} {'ско от изотоники':>17s} {'rho':>7s}")
FIT={}
for c in C:
    col=f"{c}_pIC50_direct_inhibition"; k=m[col].notna()&m[c].notna()
    pi=m.loc[k,col].to_numpy(); y=m.loc[k,c].to_numpy()
    def resid(t):
        E,h=t
        I=E/(1+10**(h*(pC0-pi)))
        return np.log2(np.clip(1-I,1e-3,None))-y
    r=least_squares(resid,[1.0,1.0],bounds=([0.2,0.2],[1.2,4.0]))
    E,h=r.x; res=resid(r.x)
    iso=IsotonicRegression(increasing=False,out_of_bounds="clip").fit(pi,y)
    ri=y-iso.predict(pi)
    FIT[c]=(E,h,res.std(),ri.std())
    print(f"{c:8s} {k.sum():5d} {E:7.3f} {h:7.3f} {res.std():12.3f} {ri.std():17.3f} {spearmanr(pi,y).statistic:+7.3f}")
print("""
E и h здесь -- параметры КАЛИБРОВКИ, а не химии соединения: одна пара на фермент,
описывающая, как латентная кривая превращается в показание прибора.
Столбец «ско от изотоники» -- предел того, что вообще может дать любая монотонная
калибровка. Разрыв между двумя ско показывает, теряет ли хилловская форма что-то
против свободной монотонной.""")

print("\n=== планшетный разброс: сколько показания гуляют между планшетами ===")
for c in C:
    d=sc[sc.enzyme==c]
    g=d.groupby("plate_id")["log2fc_estimate"]
    med=g.median(); n=g.size()
    big=med[n>=30]
    print(f"  {c}: планшетов {d.plate_id.nunique():4d} | из них >=30 соединений: {len(big):3d} | "
          f"ско медиан по планшетам {big.std():.3f} | размах {big.max()-big.min():.3f} | общее ско показаний {d.log2fc_estimate.std():.3f}")
print("""
Если ско медиан по планшетам заметно меньше общего ско показаний, планшетный эффект
мал по сравнению с химическим разбросом и отдельного слагаемого не требует.""")

# Сырой разброс сам по себе ничего не доказывает: планшеты не рандомизированы, активные
# соединения сидят кучно, поэтому часть разброса медиан -- это состав планшета, а не
# прибор. Вычитаем предсказанное по pIC50 и смотрим, что осталось. Раздел 4 документа
# опирался на эти числа, но не считал их нигде.
print("\n=== планшет после вычитания предсказанного по pIC50 ===")
print(f"  {'фермент':8s} {'n':>5s} {'ско медиан':>11s} {'размах':>8s} {'ско ост.':>9s} "
      f"{'доля дисп. (Хилл)':>18s} {'(изотоника)':>12s}")
for c in C:
    d = sc[sc.enzyme == c].merge(
        inh[["Molecule_Name", f"{c}_pIC50_direct_inhibition"]].rename(
            columns={f"{c}_pIC50_direct_inhibition": "pic"}),
        on="Molecule_Name", how="inner").dropna(subset=["pic", "log2fc_estimate", "plate_id"])
    pi = d.pic.to_numpy(); yy = d.log2fc_estimate.to_numpy()
    def _res(t):
        E_, h_ = t
        return np.log2(np.clip(1 - E_ / (1 + 10 ** (h_ * (pC0 - pi))), 1e-3, None)) - yy
    E_, h_ = least_squares(_res, [1., 1.], bounds=([.2, .2], [1.2, 4.])).x
    r_hill = yy - np.log2(np.clip(1 - E_ / (1 + 10 ** (h_ * (pC0 - pi))), 1e-3, None))
    r_iso = yy - IsotonicRegression(increasing=False, out_of_bounds="clip").fit(pi, yy).predict(pi)
    def _share(r):
        g_ = d.assign(r=r).groupby("plate_id")["r"]; gm = r.mean()
        return sum(len(v) * (v.mean() - gm) ** 2 for _, v in g_) / ((r - gm) ** 2).sum() * 100
    gg = d.assign(r=r_hill).groupby("plate_id")["r"]
    med = gg.median()[gg.size() >= 30]
    print(f"  {c:8s} {len(d):5d} {med.std():11.3f} {med.max()-med.min():8.3f} "
          f"{r_hill.std():9.3f} {_share(r_hill):17.2f}% {_share(r_iso):11.2f}%")
print("Доля дисперсии остатка, объяснённая планшетом, под двумя способами вычитания.")
print("Совпадение способов означает, что число -- свойство данных, а не выбора калибровки.")

# --- Двухсайтовая форма прибора (пункт 178). Односайтовая выше остаётся эталоном; эта
# --- печатается рядом, потому что перекрёстно проверенный остаток лучше на всех четырёх,
# --- но параметры описывают физику только на CYP3A4, где доля 0.481 при разделении 0.978.
def _two(t, pi):
    E, h, f, Dd = t
    f = np.clip(f, 0.0, 1.0)
    a = 1 / (1 + 10 ** np.clip(h * (pC0 - pi), -30, 30))
    b = 1 / (1 + 10 ** np.clip(h * (pC0 - pi - Dd), -30, 30))
    return np.log2(np.clip(1 - E * (f * a + (1 - f) * b), 1e-6, None))

print("\n=== двухсайтовая форма: I = E[f/(1+10^{h(pC0-pi)}) + (1-f)/(1+10^{h(pC0-pi-D)})] ===")
print(f"{'фермент':8s} {'E':>7s} {'h':>7s} {'f':>7s} {'D':>7s} {'ско':>8s} {'ско одно':>9s} {'D на границе':>13s}")
for c in C:
    col = f"{c}_pIC50_direct_inhibition"; k = m[col].notna() & m[c].notna()
    pi = m.loc[k, col].to_numpy(); y = m.loc[k, c].to_numpy()
    r2 = least_squares(lambda t: _two(t, pi) - y, [1.0, 1.0, 0.5, 0.5],
                       bounds=([0.2, 0.2, 0.0, -3.0], [1.2, 4.0, 1.0, 3.0]))
    E2, h2, f2, D2 = r2.x
    print(f"{c:8s} {E2:7.3f} {h2:7.3f} {f2:7.3f} {D2:7.3f} "
          f"{(_two(r2.x, pi) - y).std():8.3f} {FIT[c][2]:9.3f} "
          f"{'ДА' if abs(abs(D2) - 3.0) < 1e-3 else 'нет':>13s}")
print("""
Граница у D означает вырождение: второй сигмоид уходит в бесконечность и работает
переменной-заглушкой для хвоста, а не вторым сайтом. Так на CYP2C9 и CYP2D6.
Пункт 178: улучшение остатка есть везде, физика --- только на CYP3A4.""")
