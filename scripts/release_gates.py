"""Validate explicit release gates; missing or pending evidence never means ready."""
import argparse
import json
from pathlib import Path

STATUSES={'PASS','FAIL','BLOCKED','PENDING','NOT_APPLICABLE'}
REQUIRED={'GIT_HISTORY','SOURCE_INTEGRITY','UNIT_TESTS','STANDARD_WINDOWS_TESTS',
          'PORTABLE_BUILD','PORTABLE_LAUNCH','CLEAN_MACHINE_TEST','HUMAN_GUI_ACCEPTANCE',
          'EVIDENCE_PRESERVATION','DEPENDENCY_REVIEW','LICENSE_REVIEW','ARTIFACT_CHECKSUMS',
          'PUBLICATION_AUDIT','RELEASE_AUTHORIZATION'}
REQUIRED_V2={'GIT_HISTORY','SOURCE_INTEGRITY','STANDARD_TESTS','OWNER_WINDOWS_TESTS',
             'GITHUB_WINDOWS_CI','PORTABLE_BUILD','PORTABLE_LAUNCH','EVIDENCE_PRESERVATION',
             'DEPENDENCY_REVIEW','LICENSE_REVIEW','HUMAN_VISUAL_ACCEPTANCE',
             'CLEAN_MACHINE_ACCEPTANCE','PUBLICATION_AUDIT','RELEASE_AUTHORIZATION',
             'ARTIFACT_CHECKSUMS'}


def validate(report):
    if set(report)!={'schema_version','version','gates'} or report['schema_version'] not in (1,2):raise ValueError('Release gate schema')
    required = REQUIRED if report['schema_version']==1 else REQUIRED_V2
    if not isinstance(report['gates'],list) or len(report['gates'])!=len(required):raise ValueError('Release gate inventory')
    ids=set()
    for gate in report['gates']:
        if set(gate)!={'id','description','evidence','status','actor','follow_up'}:raise ValueError('Release gate fields')
        if gate['id'] in ids or gate['id'] not in required:raise ValueError('Duplicate/unknown gate')
        ids.add(gate['id'])
        if gate['status'] not in STATUSES:raise ValueError('Release gate status')
        if any(not isinstance(gate[k],str) or not gate[k].strip() or len(gate[k])>4096 for k in ('description','actor','follow_up')):raise ValueError('Release gate explanation')
        if not isinstance(gate['evidence'],list) or len(gate['evidence'])>20:raise ValueError('Evidence list')
        if any(not isinstance(e,str) or not e.strip() or len(e)>4096 for e in gate['evidence']):raise ValueError('Evidence reference')
        if gate['status']=='PASS' and not gate['evidence']:raise ValueError('Passing gate requires evidence')
    return dict(valid=True,release_ready=all(g['status']=='PASS' for g in report['gates']),
                unresolved=[g['id'] for g in report['gates'] if g['status']!='PASS'],
                limitation='Validation checks declarations, not the truth or authenticity of linked evidence.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('report',type=Path);a=p.parse_args()
    if a.report.stat().st_size>256*1024:raise ValueError('Gate report too large')
    print(json.dumps(validate(json.loads(a.report.read_text(encoding='utf-8'))),indent=2))
