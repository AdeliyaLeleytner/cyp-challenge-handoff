from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from orx_figstyle import use_style, save, WIDE
P=Path(__file__).resolve().parents[1]; T=P/'tables'; F=P/'figures'
use_style()
LABELS={'User_ChEMBL37':'User ChEMBL37','Official_TRAIN':'Official TRAIN','Official_TEST':'Official TEST','Official_single':'Official single dose','Official_TDI':'Official TDI','Official_Emax':'Official Emax','Briford_ChEMBL_raw':'briford ChEMBL raw','Briford_Veith_raw':'briford Veith raw','Ours_ChEMBL_used':'Our ChEMBL used','Ours_Veith_used':'Our Veith used','Ours_Tox21_used':'Our Tox21 used','Ours_BindingDB_articles':'BindingDB articles','Ours_BindingDB_patents':'BindingDB patents','Earlier_Jeremy_ChEMBL':'Earlier ChEMBL','Earlier_Jeremy_PubChem':'Earlier PubChem','Existing_all_labelled':'Previously used source pool','User_novel_excluding_TEST':'Only novel user parents','Existing_plus_user_novel':'Used pool + novel user'}
SHORT={'User_ChEMBL37':'User37','Official_TRAIN':'TRAIN','Official_TEST':'TEST','Official_single':'Single','Official_TDI':'TDI','Official_Emax':'Emax','Briford_ChEMBL_raw':'ChEMBL raw','Briford_Veith_raw':'Veith raw','Ours_ChEMBL_used':'ChEMBL used','Ours_Veith_used':'Veith used','Ours_Tox21_used':'Tox21','Ours_BindingDB_articles':'BDB articles','Ours_BindingDB_patents':'BDB patents','Earlier_Jeremy_ChEMBL':'Earlier ChEMBL','Earlier_Jeremy_PubChem':'Earlier PubChem'}
COLORS=['#0072B2','#D55E00','#009E73','#CC79A7','#E69F00','#444444','#56B4E9']
captions={}
def finish(fig,name,caption):
    save(fig,str(F/name),close=False);fig.savefig(F/(name+'.png'),dpi=180,bbox_inches='tight');plt.close(fig);captions[name]=caption
def ecdf(ax,x,label,color,ls='-'):
    a=np.sort(np.asarray(pd.Series(x).dropna(),float));ax.plot(a,np.arange(1,len(a)+1)/len(a),label=f'{label} (n={len(a):,})',color=color,ls=ls,lw=1.15)
def panel(ax,text):ax.text(-.13,1.03,text,transform=ax.transAxes,fontweight='bold',fontsize=9)
summary=pd.read_csv(T/'dataset_comparison.csv');ov=pd.read_csv(T/'pairwise_overlap.csv');u=pd.read_csv(T/'user_rows_annotated.csv.gz');long=pd.read_csv(T/'all_sources_long.csv.gz');desc=pd.read_csv(T/'structure_descriptors.csv.gz')
fig,ax=plt.subplots(figsize=(WIDE,5.2));z=summary.iloc[::-1];ax.barh([LABELS[x] for x in z.dataset],z.parents,color=['#D55E00' if x=='User_ChEMBL37' else '#0072B2' for x in z.dataset]);ax.set_xlabel('Unique normalized parents (count)');ax.set_xlim(0,z.parents.max()*1.20)
for i,v in enumerate(z.parents):ax.text(v+250,i,f'{v:,}',va='center',fontsize=7)
fig.tight_layout();finish(fig,'01_dataset_sizes','Counts use the same salt/charge/stereochemistry normalization for every source. Raw and used versions are overlapping views, not independent datasets. Source rows and measurement counts are separate columns in the workbook. Descriptive census; no sampling uncertainty.')
names=summary.dataset.tolist();mat=ov.pivot(index='dataset_a',columns='dataset_b',values='fraction_a').loc[names,names].to_numpy()*100
fig,ax=plt.subplots(figsize=(WIDE,6.3));im=ax.imshow(mat,cmap='viridis',vmin=0,vmax=100,interpolation='nearest');ax.set_xticks(range(len(names)),[SHORT[x] for x in names],rotation=90,ha='center');ax.set_yticks(range(len(names)),[SHORT[x] for x in names]);ax.tick_params(labelsize=6);ax.grid(False)
for i in range(len(names)):
 for j in range(len(names)):ax.text(j,i,f'{mat[i,j]:.0f}',ha='center',va='center',fontsize=5.4,color='black' if mat[i,j]>55 else 'white')
fig.colorbar(im,ax=ax,fraction=.04,pad=.03,label='Row dataset also present in column dataset (%)');fig.tight_layout();finish(fig,'02_parent_overlap','Directional overlap: each cell is the percentage of row-source normalized parents present in the column source. The matrix is not symmetric because denominators differ. Empty Murcko scaffolds are not used as evidence of scaffold overlap.')
targets=['CYP1A2','CYP2C9','CYP2D6','CYP3A4'];groups=[('hts','point'),('ic50','point'),('ic50','upper_bound')]
fig,ax=plt.subplots(figsize=(WIDE,3.2));bottom=np.zeros(4)
for k,(task,rel) in enumerate(groups):
 counts=u[(u.endpoint==task)&(u.relation==rel)].gene.value_counts().reindex(targets,fill_value=0).to_numpy();ax.bar(targets,counts,bottom=bottom,label=f'{task} / {rel}',color=COLORS[k]);bottom+=counts
ax.set_ylabel('User aggregated rows (count)');ax.legend(frameon=False,loc='upper left');ax.set_ylim(0,bottom.max()*1.16)
for i,v in enumerate(bottom):ax.text(i,v+250,f'{v:,.0f}',ha='center',fontsize=7)
fig.tight_layout();finish(fig,'03_user_label_types','The supplied table contains different task and censoring labels. Upper bounds are displayed separately and never treated as point measurements. Task names and y units are not documented by the supplied file; source labels are retained literally.')
sources=[('Official_TRAIN',None,'Official pIC50'),('Ours_ChEMBL_used',None,'Our ChEMBL potency'),('User_ChEMBL37','hts','User hts y'),('User_ChEMBL37','ic50','User ic50 y')]
fig,axes=plt.subplots(2,2,figsize=(WIDE,5.2),sharex=True,sharey=True)
for k,(ax,g) in enumerate(zip(axes.flat,targets)):
 for i,(ds,task,label) in enumerate(sources):
  v=long[(long.dataset==ds)&(long.gene==g)&(long.relation=='point')]
  if task:v=v[v.endpoint==task]
  ecdf(ax,v.value,label,COLORS[i],'--' if ds.startswith('User') else '-')
 ax.set_xlabel('Reported numeric value');ax.set_ylabel('Cumulative fraction');panel(ax,f'({chr(97+k)}) {g}');ax.grid(alpha=.15);ax.legend(fontsize=5.7,frameon=False,loc='lower right')
fig.tight_layout();finish(fig,'04_activity_distributions','Only point-labelled rows are plotted, separately by CYP. Solid lines are known reference potency scales; dashed lines are the supplied y values whose units are unverified. The numerical overlay is descriptive and does not establish assay equivalence. Rows are aggregated labels, not independent experimental replicates.')
chem_sources=['User_ChEMBL37','Official_TRAIN','Official_TEST','Ours_ChEMBL_used','Ours_Veith_used','Ours_Tox21_used']
parent_members={n:set(long.loc[long.dataset==n,'parent'].dropna()) for n in chem_sources if n!='Official_TEST'}
# Structures without labels must stay in structural-distribution denominators.
membership=pd.read_csv(T/'user_structure_membership.csv')
cache=desc.set_index('smiles');A=Path('/Users/adeliyaleleytner/autoresearch-runs/cyp-direct-overnight-20261023/remote/assets')
for ds,file in [('Official_TRAIN','official-train.csv'),('Official_TEST','official-test.csv')]:parent_members[ds]=set(cache.loc[pd.read_csv(A/file).SMILES,'parent'].dropna())
parent_members['User_ChEMBL37']=set(membership.parent.dropna());parents=desc[desc.valid].drop_duplicates('parent').set_index('parent')
fig,axes=plt.subplots(2,2,figsize=(WIDE,5.1))
for k,(ax,prop,label) in enumerate(zip(axes.flat,['MW','cLogP','TPSA','RotB'],['Molecular weight (Da)','Calculated logP','TPSA (angstrom squared)','Rotatable bonds (count)'])):
 for i,ds in enumerate(chem_sources):
  ecdf(ax,parents.loc[sorted(parent_members[ds]),prop],SHORT[ds],COLORS[i])
 ax.set_xlabel(label);ax.set_ylabel('Cumulative fraction');panel(ax,f'({chr(97+k)})');ax.grid(alpha=.15)
handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',ncol=3,frameon=False,fontsize=6);fig.tight_layout(rect=(0,.12,1,1));
for ax,limits in zip(axes.flat,[(0,800),(-4,9),(0,200),(0,20)]): ax.set_xlim(*limits)
finish(fig,'05_chemical_properties','RDKit descriptors are calculated once per standardized parent, not once per measurement. They describe chemical space rather than measured bioavailability, clinical inhibition or pH-specific charge. Axes zoom to the main chemical range; observations are not removed and n gives full unique-parent counts. Quantiles and descriptor maxima are retained in the downloadable data.')
nn=pd.read_csv(T/'test_nearest_neighbors.csv');refs=['Official_TRAIN','Ours_ChEMBL_used','User_ChEMBL37','Existing_all_labelled','User_novel_excluding_TEST','Existing_plus_user_novel']
fig,ax=plt.subplots(figsize=(WIDE,3.7))
for i,ds in enumerate(refs):ecdf(ax,nn.loc[nn.reference==ds,'max_tanimoto'],LABELS[ds],COLORS[i])
ax.set_xlabel('Maximum Morgan Tanimoto to reference pool');ax.set_ylabel('Fraction of TEST queries');ax.legend(frameon=False,fontsize=6.2,loc='upper center',bbox_to_anchor=(.5,-.22),ncol=2);ax.grid(alpha=.15);fig.tight_layout();finish(fig,'06_test_neighborhood','All 750 TEST structures are queried against each complete reference pool using Morgan radius2,2048-bit fingerprints without chirality. Novel user parents exclude every existing labelled parent and TEST identities. Larger pools can increase nearest-neighbour similarity; this figure does not measure prediction improvement.')
pairs=pd.read_csv(T/'paired_activity_values.csv');pairs=pairs[(pairs.identity=='iso')&(pairs.comparator=='Ours_ChEMBL_used')]
fig,axes=plt.subplots(1,2,figsize=(WIDE,3.3))
for k,(ax,task) in enumerate(zip(axes,['hts','ic50'])):
 z=pairs[pairs.user_task==task];im=ax.hexbin(z.other_value,z.user_y,gridsize=50,mincnt=1,norm=LogNorm(),cmap='viridis');lo=min(z.user_y.min(),z.other_value.min());hi=max(z.user_y.max(),z.other_value.max());ax.plot([lo,hi],[lo,hi],color='#D55E00',lw=.8,ls='--');ax.set_xlabel('Our ChEMBL aggregate value');ax.set_ylabel('User y');ax.text(.04,.96,f'n={len(z):,}\nmedian |delta|={z.delta.abs().median():.4f}',transform=ax.transAxes,va='top',fontsize=7);panel(ax,f'({chr(97+k)}) {task}');fig.colorbar(im,ax=ax,label='Matched pairs per bin',fraction=.05)
fig.tight_layout();finish(fig,'07_shared_values','Exact normalized stereochemical identity and CYP are matched. Within-source duplicate values are reduced by the median for this diagnostic only; task types remain separate. Near-equality supports shared numerical information, but without assay IDs it does not prove the same raw experiments or establish user y units.')
ua=pd.read_csv(T/'user_rows_all_archive_membership.csv.gz');fig,ax=plt.subplots(figsize=(WIDE,3.1));names2=['hts / point','ic50 / point','ic50 / upper_bound'];known=[];new=[];testonly=[]
for task,rel in groups:
 z=ua[(ua.endpoint==task)&(ua.relation==rel)];new.append(int(z.new_parent_vs_all_raw_excluding_TEST.sum()));testonly.append(int(z.parent.isin(parent_members['Official_TEST']).sum()));known.append(len(z)-new[-1]-testonly[-1])
ax.barh(names2,known,color=COLORS[0],label='Parent already in existing source archive');ax.barh(names2,new,left=known,color=COLORS[1],label='Novel parent, excluding TEST');ax.barh(names2,testonly,left=np.array(known)+new,color=COLORS[2],label='TEST identity overlap');ax.set_xlabel('User source rows (count)');ax.legend(frameon=False,fontsize=6.3,loc='upper center',bbox_to_anchor=(.5,-.23),ncol=1);fig.tight_layout();finish(fig,'08_new_information','Novelty here is counted against all available source archives, including downloaded but untrained columns and records; TEST identities are excluded from novel parents. Bars count user rows, not independent molecules. A bound or a new target on a known molecule may add information even when its structure is not novel.')
corr=pd.read_csv(T/'user_cross_target_correlations.csv');fig,axes=plt.subplots(1,2,figsize=(WIDE,3.5))
for k,(ax,task) in enumerate(zip(axes,['hts','ic50'])):
 z=corr[corr.task==task];r=z.pivot(index='target_a',columns='target_b',values='spearman').loc[targets,targets].to_numpy();n=z.pivot(index='target_a',columns='target_b',values='n_shared').loc[targets,targets].to_numpy();im=ax.imshow(r,vmin=-1,vmax=1,cmap='RdBu_r',interpolation='nearest');ax.set_xticks(range(4),targets,rotation=45,ha='right');ax.set_yticks(range(4),targets);ax.tick_params(labelsize=7);ax.grid(False);panel(ax,f'({chr(97+k)}) {task}')
 for i in range(4):
  for j in range(4):ax.text(j,i,f'{r[i,j]:.2f}\nn={n[i,j]:,}',ha='center',va='center',fontsize=5.8,color='white' if abs(r[i,j])>.6 else 'black')
fig.colorbar(im,ax=axes,label='Spearman correlation',fraction=.025,pad=.03);fig.subplots_adjust(left=.1,right=.86,bottom=.2,top=.90,wspace=.5);finish(fig,'09_cross_target_profiles','Pairwise complete observations on the same normalized stereochemical structure, separated by user task. Each cell reports its own sample size. Correlated profiles are descriptive; pooled measurements with unknown assay conditions cannot establish mechanistic or clinical selectivity.')
(F/'captions.json').write_text(json.dumps(captions,indent=2))
print('FIGURES',len(captions))
