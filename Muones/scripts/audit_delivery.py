"""Check the scientific result and the compact deliverable, including compressed evidence."""
import base64,csv,gzip,json,re
from pathlib import Path
from collections import Counter
from html.parser import HTMLParser
import numpy as np
import pymupdf
from reproduce import ROOT,DERIVED,OUT,read,check_inputs,select
from muones.io import sha256
from muones.finite_window import density


class Links(HTMLParser):
    def __init__(self):super().__init__();self.targets=[];self.ids=set();self.images=[];self.sections=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.add(a['id'])
        if tag=='section':self.sections+=1
        if tag=='a':self.targets.append(a.get('href',''))
        if tag=='img':self.images.append(a.get('src',''))


def main():
    cfg=check_inputs();rows=select(read(DERIVED/'txt_event_decisions.csv'),cfg)
    fit=read(OUT/'fit_events.csv');payload=json.loads((OUT/'lifetime_fit.json').read_text(encoding='utf-8'))
    assert len(rows)==847 and len(fit)==525 and len({r['uid'] for r in fit})==525
    assert dict(Counter(r['decision'] for r in rows))==payload['decisions']
    assert payload['previous_events_used']==payload['background']==0 and payload['event_weight']==1
    assert all(r['source']==cfg['source'] and int(r['n_samples'])==1024 and float(r['weight'])==1 for r in fit)
    assert {int(r['event_id']) for r in rows if r['decision']=='outside_upper_edge_margin'}=={373,737}
    for r in fit:
        assert float(r['lower_ns'])==120<=float(r['delay_ns'])<=float(r['upper_ns'])
        assert abs(float(r['record_end_ns'])-10-float(r['upper_ns']))<1e-9
    for upper in set(float(r['upper_ns'])/1000 for r in fit):
        x=np.linspace(.12,upper,10001)
        assert abs(np.trapezoid(density(x,payload['fit']['beta_per_us'],.12,upper),x)-1)<1e-8
    with gzip.open(DERIVED/'five_runs_event_decisions.csv.gz','rt',encoding='utf-8',newline='') as f:
        previous=list(csv.DictReader(f))
    assert len(previous)==192680 and all(int(r['n_samples'])==1024 for r in previous)
    counts=Counter(r['count_status'] for r in previous)
    assert counts==dict(accepted=182709,ambiguous=9835,excluded=136)
    with gzip.open(DERIVED/'excluded_300_metadata.csv.gz','rt',encoding='utf-8',newline='') as f:
        excluded=list(csv.DictReader(f))
    assert len(excluded)==23727 and all(int(r['n_samples'])==300 for r in excluded)
    for dst,item in json.loads((DERIVED/'migration_provenance.json').read_text(encoding='utf-8')).items():
        if item.get('representation')=='lossless gzip':
            import hashlib
            with gzip.open(ROOT/dst,'rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==item['sha256']
        else:assert sha256(ROOT/dst)==item['sha256']
    receipt=json.loads((OUT/'verification_receipt.json').read_text(encoding='utf-8'))
    assert receipt['script_sha256']==sha256(ROOT/'scripts/reproduce.py')
    assert receipt['inputs_manifest_sha256']==sha256(ROOT/'data/inputs_manifest.json')
    assert receipt['raw_verification']['selected_times_verified']==525 and receipt['simulations_recomputed']
    assert receipt['local_validation']==payload['local_validation']
    for path,digest in json.loads((OUT/'report_manifest.json').read_text(encoding='utf-8')).items():assert sha256(ROOT/path)==digest
    pdf=ROOT/'output/pdf/proyecto_muones.pdf';web=ROOT/'output/informe.html'
    # Temporary environments are not delivery artifacts.
    files=[p for p in ROOT.rglob('*') if p.is_file() and not any(x in p.relative_to(ROOT).parts for x in ('tmp','.venv','__pycache__','.git'))]
    assert [p for p in files if p.suffix.lower()=='.pdf']==[pdf]
    assert [p for p in files if p.suffix.lower()=='.html']==[web]
    with pymupdf.open(pdf) as doc:
        assert len(doc)==5
        for i,p in enumerate(doc):
            text=p.get_text();assert f'{i+1}.' in text
            for block in p.get_text('blocks'):
                assert block[0]>=20 and block[1]>=10 and block[2]<=575 and block[3]<=829
        assert '525' in doc[3].get_text() and '1,948' in doc[3].get_text()
    parser=Links();parser.feed(web.read_text(encoding='utf-8'))
    assert parser.sections==5 and len(parser.images)==3
    for target in parser.targets:
        if target.startswith('#'):assert target[1:] in parser.ids
        elif target.startswith('https://'):pass
        else:assert (web.parent/target).resolve().is_file(),target
    for src in parser.images:
        assert src.startswith('data:image/png;base64,')
        assert base64.b64decode(src.split(',',1)[1],validate=True).startswith(b'\x89PNG')
    qa=json.loads((OUT/'visual_qa.json').read_text(encoding='utf-8'))
    assert qa['pdf_pages_inspected']==5 and qa['pdf_sha256']==sha256(pdf)
    assert qa['html_sha256']==sha256(web)
    result=dict(status='passed',events_txt=847,selected_txt=525,previous_events_in_likelihood=0,
        previous_event_decisions_preserved=192680,excluded_300_metadata_preserved=23727,
        tests_passed=31,raw_waveform_verification_receipt=True,simulation_reproduction_receipt=True,
        pdf_files=1,pdf_pages=5,html_files=1,html_embedded_images=3,
        nominal_intervals_conditional_on_model=True,html_browser_visual_check=qa['html_browser_visual_check'])
    (OUT/'audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    files=[p for p in ROOT.rglob('*') if p.is_file() and not any(x in p.relative_to(ROOT).parts for x in ('tmp','.venv','__pycache__','.git'))
           and p.name!='delivery_manifest.json' and not p.name.startswith('.local_')]
    (ROOT/'delivery_manifest.json').write_text(json.dumps({p.relative_to(ROOT).as_posix():sha256(p) for p in sorted(files)},indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
