"""Data-driven local planar candidates. No prescribed hip/gable model.
Preserve V1 interpolation within and near upper tower region, and reject unsupported extrapolation.
"""
import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse.csgraph import connected_components
import shapely as sh
from shapely.ops import transform
from roof_plane_fit import axis_frame,partition_tower

def fit_regions(p,samples,baseline):
    xy=samples[:,[0,2]];y=samples[:,1];basis=axis_frame(p)
    def local(x,z,h=None):return (np.asarray(x)*basis[0,0]+np.asarray(z)*basis[1,0],np.asarray(x)*basis[0,1]+np.asarray(z)*basis[1,1])
    q=np.column_stack((xy@basis,y));region=transform(local,p);tower=partition_tower(region,q)
    if tower is None:raise ValueError("Cannot isolate upper tower: preserve V1")
    protected=tower.buffer(1.5)
    # Also protect any upper returns missed by the bounding polygon.
    upper=y>max(float(np.median(y)+3.5),float(np.quantile(y,.8)+1))
    upper_tree=cKDTree(xy[upper])
    def locked(x,z):
        u,v=local(x,z)
        return bool(sh.intersects_xy(protected,u,v) or upper_tree.query([x,z])[0]<=1.5)
    free=np.array([not locked(x,z) for x,z in xy])
    remaining=np.flatnonzero(free);rng=np.random.default_rng(149406360);planes=[];infos=[]
    for _ in range(12):
        if len(remaining)<35:break
        a=np.column_stack((xy[remaining],np.ones(len(remaining))));b=y[remaining];best=None
        for _ in range(240):
            ids=rng.choice(len(a),3,replace=False);m=a[ids]
            if abs(np.linalg.det(m))<.08:continue
            coef=np.linalg.solve(m,b[ids])
            if np.linalg.norm(coef[:2])>1.5:continue
            residual=np.abs(a@coef-b);inliers=np.flatnonzero(residual<=.16)
            if len(inliers)<35:continue
            score=(len(inliers),-float(np.median(residual[inliers])))
            if best is None or score>best[0]:best=(score,inliers)
        if best is None:break
        ids=remaining[best[1]]
        graph=cKDTree(xy[ids]).sparse_distance_matrix(cKDTree(xy[ids]),1.05,output_type="coo_matrix")
        _,labels=connected_components(graph.tocsr(),directed=False)
        ids=ids[labels==np.argmax(np.bincount(labels))]
        if len(ids)<35:break
        A=np.column_stack((xy[ids],np.ones(len(ids))));coef=np.linalg.lstsq(A,y[ids],rcond=None)[0]
        residual=np.abs(A@coef-y[ids]);ids=ids[residual<=.20]
        if len(ids)<35:break
        A=np.column_stack((xy[ids],np.ones(len(ids))));coef=np.linalg.lstsq(A,y[ids],rcond=None)[0]
        if np.linalg.norm(coef[:2])>1.5:break
        planes.append((coef,cKDTree(xy[ids])))
        infos.append({"plane_x_z_y_intercept":coef.tolist(),"support_cells":len(ids),"fit_rmse_m":float(np.sqrt(np.mean((A@coef-y[ids])**2)))})
        remaining=remaining[~np.isin(remaining,ids)]
    def sample(x,z):
        h,d=baseline(x,z)
        if locked(x,z) or not planes:return h,d
        # Only use supported local plane. Blend smoothly near region boundaries.
        opts=[]
        for coef,tree in planes:
            distance=float(tree.query([x,z])[0]);value=float(coef@[x,z,1])
            if distance<=.85 and abs(value-h)<=.45:opts.append((distance,abs(value-h),value))
        if not opts:return h,d
        dist,_,value=min(opts);w=float(np.clip((.85-dist)/.45,0,1))
        # Suppress smoothing close to preserved tower.
        u,v=local(x,z);tower_distance=float(protected.distance(sh.Point(float(u),float(v))))
        w*=min(1.,tower_distance/.8)*min(1.,max(0.,(float(upper_tree.query([x,z])[0])-1.5)/.8))
        return h+w*(value-h),d
    return sample,locked,[{"name":"tower","kind":"unchanged V1 upper volume","area_m2":float(tower.area),"protected_margin_m":1.5},{"name":"nave","kind":"connected RANSAC local planes","planes":infos,"unassigned_cells":len(remaining)}]
