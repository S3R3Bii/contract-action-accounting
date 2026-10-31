"""Keep minimal exact factual transaction fields; preserve eligibility failures."""
from pathlib import Path
from datetime import date
from decimal import Decimal
from collections import Counter
import argparse,csv,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def valid_date(value):
    if not isinstance(value,str):return False
    try:return date.fromisoformat(value).isoformat()==value
    except ValueError:return False
def money(value):
    if type(value) not in [int,Decimal]:return '', 'MISSING' if value is None else 'NONNUMERIC'
    result=Decimal(value)
    if not result.is_finite():return '', 'NONFINITE'
    return str(result),'FINITE'
def run(source):
    manifest=json.loads((ROOT/'data/capture_manifest.json').read_bytes());assert manifest['status']=='PASS_CAPTURE_CONTROLS'
    for request in manifest['requests']:
        raw=(source/request['file']).read_bytes()
        assert len(raw)==request['bytes'] and hashlib.sha256(raw).hexdigest()==request['sha256']
    projected=[];cases=[]
    for case in manifest['cases']:
        rows=json.loads((source/(case['case']+'-transactions.json')).read_bytes(),parse_float=Decimal,parse_constant=Decimal)['results']
        counts=Counter(r.get('id') for r in rows if isinstance(r.get('id'),str) and r.get('id'))
        for index,row in enumerate(rows):
            key=row.get('id')
            identity='SINGLETON' if isinstance(key,str) and key and counts[key]==1 else 'DUPLICATE' if isinstance(key,str) and key else 'MISSING'
            token,state=money(row.get('federal_action_obligation'))
            action=row.get('action_date')
            projected.append(dict(case=case['case'],source_row=index+1,transaction_id=key if isinstance(key,str) else '',identity_state=identity,
                                  action_date=action if isinstance(action,str) else '',date_state='VALID' if valid_date(action) else 'INVALID_OR_MISSING',
                                  type_code=row.get('type',''),modification_token=row.get('modification_number') or '',money_token=token,money_state=state))
        cases.append({k:case[k] for k in ['case','generated_award_id','award_id','base_date','contract_type','captured_records']})
    (ROOT/'data/cases.json').write_bytes((json.dumps(cases,indent=2)+'\n').encode())
    path=ROOT/'data/transactions.csv'
    with path.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(projected[0]),lineterminator='\n');writer.writeheader();writer.writerows(projected)
    receipt=dict(status='PROJECTION_PRODUCED_NOT_YET_INDEPENDENTLY_VERIFIED',cases=len(cases),records=len(projected),hashes={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['data/cases.json','data/transactions.csv','data/capture_manifest.json']},
                 qualification='Minimal current contract transaction facts; no original publication snapshot or verified staff-task identity.')
    (ROOT/'data/projection_receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
    print(json.dumps(receipt))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-dir',type=Path,required=True);run(p.parse_args().source_dir)
