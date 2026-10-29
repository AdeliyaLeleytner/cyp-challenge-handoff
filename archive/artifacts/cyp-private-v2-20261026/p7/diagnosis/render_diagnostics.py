"""Rendering-only derivative of the frozen P7 cached diagnostic outputs."""
from pathlib import Path
import sys,json,hashlib
import pandas as pd,numpy as np
p=Path(__file__).parent;sys.path.insert(0,str(p/'worktree/night'))
from orx_figstyle import use_style,save,PALETTE
import matplotlib.pyplot as plt
out=p/'figures';out.mkdir(exist_ok=True);r=pd.read_csv(p/'results/measured-row-diagnostics.csv');use_style()
for kind in ['observed-predicted','paired-error','support-error']:
 fig,axs=plt.subplots(2,2,figsize=(6.75,5.4));axs=axs.ravel()
 for j,(ep,g) in enumerate(r.groupby('endpoint',sort=True)):
  ax=axs[j];ax.text(.03,.97,chr(65+j)+'  '+ep,transform=ax.transAxes,ha='left',va='top',fontsize=9)
  if kind=='observed-predicted':
   for c,label,color in [('zero','Zero descriptors',PALETTE['blue']),('fusion','ADMET fusion',PALETTE['orange'])]:ax.scatter(g.truth,g[c],s=5,alpha=.3,color=color,label=label,rasterized=True)
   lim=[min(g.truth.min(),g.zero.min(),g.fusion.min())-.1,max(g.truth.max(),g.zero.max(),g.fusion.max())+.1];ax.plot(lim,lim,color='.55',lw=.7);ax.set_xlabel('Measured pIC50');ax.set_ylabel('OOF predicted pIC50');ax.set_xlim(lim);ax.set_ylim(lim)
   if j==0:ax.legend(loc='lower right',fontsize=7)
  elif kind=='paired-error':
   ax.scatter(g.zero_abs_error,g.fusion_abs_error,s=6,alpha=.35,color=PALETTE['blue'],rasterized=True);v=max(g.zero_abs_error.max(),g.fusion_abs_error.max());ax.plot([0,v],[0,v],color='.55',lw=.7);ax.set_xlabel('Zero absolute error (pIC50)');ax.set_ylabel('Fusion absolute error (pIC50)')
  else:
   ax.scatter(g.nearest_labeled_train_similarity,g.delta_abs_error,s=6,alpha=.35,color=PALETTE['blue'],rasterized=True);ax.axhline(0,color='.55',lw=.7);ax.set_xlabel('Nearest labeled train Tanimoto');ax.set_ylabel('Fusion − zero absolute error')
 fig.tight_layout();save(fig,out/kind);fig.savefig(out/(kind+'.png'),dpi=180);plt.close(fig)
manifest={'render_only':True,'scientific_input_sha256':hashlib.sha256((p/'results/measured-row-diagnostics.csv').read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'files':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(out.iterdir()) if x.is_file()}};(out/'render-receipt.json').write_text(json.dumps(manifest,indent=2)+'\n')
