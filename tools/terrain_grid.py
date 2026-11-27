"""MapSlop local metric frame and triangle interpolation (stdlib only)."""
import math

BBOX = (41.4105, -8.395, 41.4195, -8.383)  # S,W,N,E
ORIGIN = (41.41501, -8.38809)  # lat,lon; identical to the pinned Nairobi adapter
A, E2 = 6378137.0, 6.69437999014e-3
phi = math.radians(ORIGIN[0])
N = A / math.sqrt(1 - E2 * math.sin(phi)**2)
M = A * (1 - E2) / (1 - E2 * math.sin(phi)**2)**1.5
KX, KY = math.pi / 180 * N * math.cos(phi), math.pi / 180 * M

def to_world(lon, lat):
    return (lon - ORIGIN[1]) * KX, -(lat - ORIGIN[0]) * KY

def extent(bbox=BBOX):
    s,w,n,e = bbox
    x0,z1 = to_world(w,s)
    x1,z0 = to_world(e,n)
    return x0,z0,x1,z1

def grid_shape(cell, bounds=None):
    x0,z0,x1,z1 = extent() if bounds is None else bounds
    x0,z0 = math.floor(x0/cell)*cell, math.floor(z0/cell)*cell
    return x0,z0,math.ceil((x1-x0)/cell)+1,math.ceil((z1-z0)/cell)+1

def height_at(t,x,z):
    fx = min(t["nx"]-1,max(0,(x-t["x0"])/t["cell"]))
    fz = min(t["nz"]-1,max(0,(z-t["z0"])/t["cell"]))
    i,j = min(t["nx"]-2,math.floor(fx)),min(t["nz"]-2,math.floor(fz))
    u,v = fx-i,fz-j
    h = t["heights"]
    a,b,c,d = h[j*t["nx"]+i],h[j*t["nx"]+i+1],h[(j+1)*t["nx"]+i],h[(j+1)*t["nx"]+i+1]
    if u+v<=1:
        return a+(b-a)*u+(c-a)*v
    return d+(c-d)*(1-u)+(b-d)*(1-v)

def validate(t, bounds=None):
    """Require coverage and the exact frame; do not clamp missing source coverage."""
    if t.get("kind") == "tin":
        from terrain_tin import validate_tin
        return validate_tin(t,bounds)
    if t.get("origin_lat_lon") != list(ORIGIN):
        raise ValueError("Terrain origin mismatch")
    if t.get("source") not in {"DGT MDT 0.5 m","SYNTHETIC TEST TERRAIN"}:
        raise ValueError("Unexpected terrain source")
    if t.get("cell") not in (1,2,5,10):
        raise ValueError("Unsupported terrain cell")
    for k in ("base","x0","z0"):
        if not isinstance(t.get(k),(float,int)) or not math.isfinite(t[k]):
            raise ValueError("Invalid terrain coordinate: "+k)
    x0,z0,nx,nz=grid_shape(t["cell"],bounds)
    if (t["x0"],t["z0"],t.get("nx"),t.get("nz"))!=(x0,z0,nx,nz):
        raise ValueError("Terrain grid does not match required extent")
    if nx*nz>1_500_000 or len(t.get("heights",[]))!=nx*nz:
        raise ValueError("Invalid terrain dimensions")
    if any(not isinstance(v,(float,int)) or not math.isfinite(v) or abs(v)>9000 for v in t["heights"]):
        raise ValueError("Invalid terrain heights")
    if x0<=0<=x0+(nx-1)*t["cell"] and z0<=0<=z0+(nz-1)*t["cell"] and abs(height_at(t,0,0))>0.02:
        raise ValueError("Terrain base must be at origin")
    return t

def synthetic_grid(cell=5):
    x0,z0,nx,nz=grid_shape(cell)
    return validate(dict(source="SYNTHETIC TEST TERRAIN",origin_lat_lon=list(ORIGIN),
        base=100.0,x0=x0,z0=z0,cell=cell,nx=nx,nz=nz,
        heights=[round(0.012*(x0+i*cell)+0.008*(z0+j*cell),3) for j in range(nz) for i in range(nx)]))
