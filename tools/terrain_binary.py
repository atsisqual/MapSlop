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

def encode(t):
    meta={k:v for k,v in t.items() if k not in ("heights","vertices","triangles")}
    if t.get("kind")=="tin":
        meta["encoding"]="xyz-f32le-index-u32le"
        meta["vertex_count"]=len(t["vertices"])//3
        meta["triangle_count"]=len(t["triangles"])//3
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
    elif enc=="height-f32le-implicit-grid" and t.get("kind","grid")=="grid":
        count=t.pop("height_count")
        if type(count)!=int or count!=t["nx"]*t["nz"] or not 4<=count<=1500000 or len(data)!=offset+count*4:
            raise ValueError("Invalid grid payload length")
        t["heights"]=unpack(data[offset:],"f")
    else:
        raise ValueError("Unknown terrain encoding")
    return t

def save(path,t):
    data=encode(t)
    decoded=decode(data)
    path.write_bytes(data)
    compressed=gzip.compress(data,compresslevel=9,mtime=0)
    old=json.dumps(t,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode()+b"\n"
    return decoded,{"file":path.name,"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data),
        "gzip_bytes":len(compressed),"gzip_sha256":hashlib.sha256(compressed).hexdigest(),
        "json_bytes":len(old),"json_gzip_bytes":len(gzip.compress(old,compresslevel=9,mtime=0)),
        "encoding":"MSLTERR1"}
