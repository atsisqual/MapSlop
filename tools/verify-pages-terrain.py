"""Fail closed if the private validation draft differs from the reviewed product."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

RAW_SHA="de37795151e47e5892b4ed8c701968f0bfe60f64f35d9142fc7b89c71ac633d0"
GZIP_SHA="9009db14b6808e36f3457db525eef2589328ac2769fe1899a8d53598efc0758d"

def verify(root):
    report=json.loads((root/"validation.json").read_text())
    if (report.get("run_id")!="46063386111" or report.get("tested_commit")!="5e1e3bb5062e636b5847c566b909c20aa5ecd02e"
        or report.get("pass") is not True or report.get("recommended_default_file")!="terrain-tin.bin"):
        raise ValueError("Unexpected validation run or selection")
    row=next(r for r in report["results"] if r["kind"]=="tin")
    if (row.get("pass") is not True or row.get("exact_float32_geometry") is not True
        or row.get("compression_pass") is not True or row.get("precision_pass") is not True
        or row.get("sha256")!=RAW_SHA or row.get("gzip_sha256")!=GZIP_SHA
        or row.get("raw_bytes")!=1288689 or row.get("gzip_bytes")!=787914):
        raise ValueError("Validation evidence differs from reviewed TIN")
    raw=(root/"terrain-tin.bin").read_bytes()
    if len(raw)!=1288689 or hashlib.sha256(raw).hexdigest()!=RAW_SHA:
        raise ValueError("Unapproved terrain bytes")
    compressed=gzip.compress(raw,compresslevel=9,mtime=0)
    if len(compressed)!=787914 or hashlib.sha256(compressed).hexdigest()!=GZIP_SHA:
        raise ValueError("Unapproved compressed terrain bytes")
    (root/"terrain-tin.bin.gz").write_bytes(compressed)

if __name__=="__main__":
    verify(Path(sys.argv[1]))
