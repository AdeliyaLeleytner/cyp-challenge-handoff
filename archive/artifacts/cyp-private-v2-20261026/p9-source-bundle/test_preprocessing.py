from pathlib import Path
import sys,json,hashlib
import numpy as np
from sklearn.decomposition import PCA
p=Path(__file__).parent;sys.path.insert(0,str(p/'profile-worktree/night'));from source_preprocessing import endpoint_pca
rng=np.random.default_rng(42);X=(rng.normal(size=(800,256))*np.linspace(.01,4,256)).astype(np.float32);y=rng.normal(size=800);train=np.arange(800)<600;query=~train;y[np.arange(0,600,5)]=np.nan;a,b,yy,mask,pc=endpoint_pca(X,train,query,y);assert mask.sum()==480 and not (mask&query).any();ref=PCA(n_components=128,random_state=42);ra=ref.fit_transform(X[mask].astype(np.float32));assert np.array_equal(a,ra.astype(np.float32)) and np.array_equal(pc.components_,ref.components_)
changed=X.copy();changed[query]*=10000;changed[train&~mask]+=1000;y2=y.copy();y2[query]=np.nan;c,d,yy2,mask2,pc2=endpoint_pca(changed,train,query,y2);assert np.array_equal(mask,mask2) and np.array_equal(a,c) and np.array_equal(pc.components_,pc2.components_) and np.array_equal(yy,yy2);assert not np.array_equal(b,d)
result={'status':'pass','synthetic_only_no_TabICL_calls':True,'direct_unscaled_source_PCA_parity':True,'query_features_and_query_labels_do_not_change_fitted_PCA':True,'unlabeled_training_rows_do_not_change_fitted_PCA':True,'context_rows':480,'components':128,'no_external_StandardScaler':True,'source_sha256':hashlib.sha256((p/'profile-worktree/night/source_preprocessing.py').read_bytes()).hexdigest()};(p/'PREPROCESSING_TESTS.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
