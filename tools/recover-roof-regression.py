#!/usr/bin/env python3
"""Recover immutable first-run report from the unpublished draft before replacement."""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess

EXPECTED={'223184536','1460484457','223204089','224014876','223180379','223180362','223351055','223203879','223354712','223351080','223180321','223351067','223354671','223586396','223586347','223203956','223180360','223586446'}
ARCHIVE='regression-46070425792-buildings.json'

def diagnose(prev):
    fails=[]
    for row in prev['rows']:
        reason=[]
        vals=[row.get(k) for k in ('foundation_min_m','terrain_max_m','habitable_base_m','roof_top_m')]
        if any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in vals):reason.append('nonfinite_foundation_or_roof')
        else:
            if vals[1]<vals[0]:reason.append('terrain_max_below_min')
            if vals[3]<vals[2]:reason.append('roof_below_base')
        if reason:fails.append({**row,'failed_predicates':reason})
    return {'source_run':46070425792,'prior_measured':prev.get('measured'),
            'prior_foundation_failures':fails,
            'prior_rejected_roofer':[row for row in prev['rows'] if str(row['osm_id']) in EXPECTED and row['policy']!='roofer_lod22'],
            'missing_expected_ids':sorted(EXPECTED-{str(r['osm_id']) for r in prev['rows']})}

def main():
    root=Path('/tmp/roof-results')
    prior=Path('/tmp/previous-roofs');prior.mkdir(exist_ok=True)
    tag='geodata-dgt-roofs-agent-building-roofs-facades'
    repo=os.environ['GITHUB_REPOSITORY']
    def gh(*args):
        return subprocess.run(['gh','release',*args,'--repo',repo],check=True,capture_output=True,text=True).stdout
    metadata=json.loads(gh('view',tag,'--json','isDraft,assets'))
    if not metadata['isDraft']:raise ValueError('Expected unpublished draft')
    names={a['name'] for a in metadata['assets']}
    filename=ARCHIVE if ARCHIVE in names else 'building-detail-report.json'
    gh('download',tag,'--dir',str(prior),'--pattern',filename,'--pattern','SHA256SUMS.txt')
    hashes=dict((name,digest) for digest,name in (line.split(maxsplit=1) for line in (prior/'SHA256SUMS.txt').read_text().splitlines()))
    if hashlib.sha256((prior/filename).read_bytes()).hexdigest()!=hashes.get(filename):raise ValueError('Prior report hash mismatch')
    prev=json.loads((prior/filename).read_text())
    if prev.get('buildings')!=527 or prev.get('measured')!=9 or prev.get('valid_foundations') is not False:
        raise ValueError('Prior report is not the reviewed failed run')
    shutil.copy2(prior/filename,root/ARCHIVE)
    report=diagnose(prev)
    (root/'regression-46070425792-diagnostics.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PRIOR_FOUNDATION_FAILURES',json.dumps(report['prior_foundation_failures']))
    print('PRIOR_REJECTED_ROOFER',json.dumps(report['prior_rejected_roofer']))
    print('PRIOR_MISSING_ROOFER',json.dumps(report['missing_expected_ids']))

if __name__=='__main__':main()
