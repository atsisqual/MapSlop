"""MSLTERR1: magic, little-endian uint32 JSON length, padded JSON, f32/u32 payload.
Use stdlib only so the existing adapter can decode without GIS dependencies.
"""
import array
import gzip
import hashlib
import json
from pathlib import Path
import struct
import sys

MAGIC=b"MSLTERR1"
MAX_BYTES=32_000_000

def packed(values,code):
    a=array.array(code,values)
    if a.itemsize!=4:
        raise ValueError("Expected 32-bit array")
    if sys.byteorder!="little":a.byteswap()
    return a.tobytes()

def unpack(data,code):
    a=array.array(code)
    a.frombytes(data)
    if sys.byteorder!="little":a.byteswap()
    return a.tolist()

def f32(value):
    return struct.unpack("<f",struct.pack("<f",value))[0]


def float_bits(value):
    return struct.unpack("<I",struct.pack("<f",value))[0]


def morton(x,z):
    def spread(v):
        v=(v|(v<<16))&0x0000ffff0000ffff
        v=(v|(v<<8))&0x00ff00ff00ff00ff
        v=(v|(v<<4))&0x0f0f0f0f0f0f0f0f
        v=(v|(v<<2))&0x3333333333333333
        return (v|(v<<1))&0x5555555555555555
    return spread(x)|(spread(z)<<1)


def varint(out,value):
    if not 0<=value<2**33:
        raise ValueError("Compact terrain integer range")
    while value>=128:
        out.append((value&127)|128)
        value>>=7
    out.append(value)


def delta_stream(values):
    out=bytearray()
    prev=0
    for value in values:
        d=value-prev
        varint(out,2*d if d>=0 else -2*d-1)
        prev=value
    return out


def compact_payload(t):
    """Reorder only: centimetre x/z are checked losslessly, y keeps all Float32 bits.
    Sort faces by smallest index after cyclic rotation (winding unchanged).
    Six independent streams improve gzip locality; no runtime dependency.
    """
    v=unpack(packed(t["vertices"],"f"),"f")
    f=t["triangles"]
    nv=len(v)//3
    coords=[(round(v[i]*100),float_bits(v[i+1]),round(v[i+2]*100))
            for i in range(0,len(v),3)]
    if any(f32(x/100)!=v[3*i] or f32(z/100)!=v[3*i+2]
           for i,(x,y,z) in enumerate(coords)):
        raise ValueError("Compact terrain requires exact centimetre horizontal coordinates")
    minx=min(p[0] for p in coords)
    minz=min(p[2] for p in coords)
    order=sorted(range(nv),key=lambda i:morton(coords[i][0]-minx,coords[i][2]-minz))
    inverse=[0]*nv
    for new,old in enumerate(order):
        inverse[old]=new
    xs,ys,zs=zip(*(coords[i] for i in order))
    faces=[]
    for i in range(0,len(f),3):
        a,b,c=(inverse[f[i+j]] for j in range(3))
        if b<a and b<c:a,b,c=b,c,a
        elif c<a and c<b:a,b,c=c,a,b
        faces.append((a,b,c))
    faces.sort()
    streams=[delta_stream(s) for s in (xs,ys,zs,[a for a,b,c in faces])]
    for k in (1,2):
        out=bytearray()
        for face in faces:
            varint(out,face[k]-face[0])
        streams.append(out)
    return b"".join(streams),[len(s) for s in streams]


def decode_compact(payload,nv,nt,lengths):
    if not isinstance(lengths,list) or len(lengths)!=6 or any(type(n)!=int or n<1 for n in lengths) or sum(lengths)!=len(payload):
        raise ValueError("Compact terrain stream lengths")
    streams=[]
    pos=0
    for i,length in enumerate(lengths):
        end=pos+length
        count=nv if i<3 else nt
        values=[]
        prev=0
        for _ in range(count):
            value=0
            for shift in range(0,35,7):
                if pos>=end:raise ValueError("Truncated compact terrain stream")
                b=payload[pos];pos+=1
                value|=(b&127)<<shift
                if not b&128:break
            else:raise ValueError("Compact terrain varint too long")
            if value>=2**33:raise ValueError("Compact terrain integer range")
            if i<4:
                prev+=value//2 if value%2==0 else -(value//2)-1
                values.append(prev)
            else:
                values.append(value)
        if pos!=end:raise ValueError("Trailing compact terrain stream bytes")
        streams.append(values)
    xs,ys,zs,aa,bb,cc=streams
    if any(not 0<=v<2**32 for v in ys):raise ValueError("Compact terrain height bits")
    vertices=[]
    for x,y,z in zip(xs,ys,zs):
        if abs(x)>100000000 or abs(z)>100000000:raise ValueError("Compact terrain coordinate range")
        vertices.extend((f32(x/100),struct.unpack("<f",struct.pack("<I",y))[0],f32(z/100)))
    faces=[]
    for a,b,c in zip(aa,bb,cc):
        if not (0<=a<a+b<nv and 0<=a<a+c<nv and b!=c):
            raise ValueError("Compact terrain index")
        faces.extend((a,a+b,a+c))
    return vertices,faces


def assert_same_geometry(original,decoded):
    """Compare canonical float32 vertex triples and oriented faces, including multiplicity.
    Exact equality proves that the already measured raster-node surface is unchanged.
    """
    def canonical(t):
        v=unpack(packed(t["vertices"],"f"),"f")
        points=[tuple(v[i:i+3]) for i in range(0,len(v),3)]
        order=sorted(range(len(points)),key=points.__getitem__)
        if len(set(points))!=len(points):raise ValueError("Duplicate TIN vertices")
        rank=[0]*len(points)
        for i,old in enumerate(order):rank[old]=i
        faces=[]
        f=t["triangles"]
        for i in range(0,len(f),3):
            a,b,c=(rank[f[i+j]] for j in range(3))
            if b<a and b<c:a,b,c=b,c,a
            elif c<a and c<b:a,b,c=c,a,b
            faces.append((a,b,c))
        return [points[i] for i in order],sorted(faces)
    if canonical(original)!=canonical(decoded):
        raise ValueError("Compact terrain changed Float32 geometry or face winding")


def encode(t,compact=False):
    meta={k:v for k,v in t.items() if k not in ("heights","vertices","triangles")}
    if t.get("kind")=="tin":
        meta["encoding"]="xyz-f32le-index-u32le"
        meta["vertex_count"]=len(t["vertices"])//3
        meta["triangle_count"]=len(t["triangles"])//3
        if compact:
            meta["encoding"]="tin-morton-cm-f32bits-varint"
            payload,meta["stream_lengths"]=compact_payload(t)
        else:
            payload=packed(t["vertices"],"f")+packed(t["triangles"],"I")
    else:
        meta["encoding"]="height-f32le-implicit-grid"
        meta["height_count"]=len(t["heights"])
        payload=packed(t["heights"],"f")
    header=json.dumps(meta,ensure_ascii=True,separators=(",",":"),allow_nan=False).encode()
    pad=(-len(header))%4
    return MAGIC+struct.pack("<I",len(header))+header+b"\0"*pad+payload

def decode(data):
    if len(data)<12 or len(data)>MAX_BYTES or data[:8]!=MAGIC:
        raise ValueError("Invalid terrain binary magic/size")
    n=struct.unpack_from("<I",data,8)[0]
    offset=12+(n+3)//4*4
    if n<2 or n>65536 or offset>len(data):
        raise ValueError("Invalid terrain header")
    t=json.loads(data[12:12+n])
    enc=t.pop("encoding")
    if enc=="xyz-f32le-index-u32le" and t.get("kind")=="tin":
        nv,nt=t.pop("vertex_count"),t.pop("triangle_count")
        if type(nv)!=int or type(nt)!=int or not 4<=nv<150000 or not 2<=nt<=2*nv:
            raise ValueError("Invalid TIN counts")
        split=offset+nv*12
        if len(data)!=split+nt*12:
            raise ValueError("Invalid TIN payload length")
        t["vertices"]=unpack(data[offset:split],"f")
        t["triangles"]=unpack(data[split:],"I")
    elif enc=="tin-morton-cm-f32bits-varint" and t.get("kind")=="tin":
        nv,nt=t.pop("vertex_count"),t.pop("triangle_count")
        if type(nv)!=int or type(nt)!=int or not 4<=nv<150000 or not 2<=nt<=2*nv:
            raise ValueError("Invalid compact TIN counts")
        t["vertices"],t["triangles"]=decode_compact(data[offset:],nv,nt,t.pop("stream_lengths"))
    elif enc=="height-f32le-implicit-grid" and t.get("kind","grid")=="grid":
        count=t.pop("height_count")
        if type(count)!=int or count!=t["nx"]*t["nz"] or not 4<=count<=1500000 or len(data)!=offset+count*4:
            raise ValueError("Invalid grid payload length")
        t["heights"]=unpack(data[offset:],"f")
    else:
        raise ValueError("Unknown terrain encoding")
    return t

def save(path,t,compact=False):
    data=encode(t,compact=compact)
    decoded=decode(data)
    if compact:
        assert_same_geometry(t,decoded)
    path.write_bytes(data)
    compressed=gzip.compress(data,compresslevel=9,mtime=0)
    old=json.dumps(t,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode()+b"\n"
    return decoded,{"file":path.name,"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data),
        "gzip_bytes":len(compressed),"gzip_sha256":hashlib.sha256(compressed).hexdigest(),
        "json_bytes":len(old),"json_gzip_bytes":len(gzip.compress(old,compresslevel=9,mtime=0)),
        "encoding":"MSLTERR1/compact" if compact else "MSLTERR1",
        "exact_float32_geometry":True if compact else None,
        "legacy_binary_bytes":len(encode(t)) if compact else len(data),
        "legacy_binary_gzip_bytes":len(gzip.compress(encode(t),compresslevel=9,mtime=0)) if compact else len(compressed)}
