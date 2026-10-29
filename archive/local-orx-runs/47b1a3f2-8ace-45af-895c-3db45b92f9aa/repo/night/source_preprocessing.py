"""Inspected source PCA convention, with explicit endpoint training membership."""
import numpy as np
from sklearn.decomposition import PCA

def endpoint_pca(X, train, query, y, max_features=128, seed=42):
 train=np.asarray(train,bool);query=np.asarray(query,bool);assert not (train&query).any();context=train&np.isfinite(y);assert context.sum()>=max_features and np.isfinite(X).all()
 raw=X[context].astype(np.float32);test=X[query].astype(np.float32);pca=PCA(n_components=min(max_features,len(raw),raw.shape[1]),random_state=seed)
 fitted=pca.fit_transform(raw).astype(np.float32);transformed=pca.transform(test).astype(np.float32)
 assert np.isfinite(fitted).all() and np.isfinite(transformed).all()
 return fitted,transformed,np.asarray(y[context],np.float32),context,pca
