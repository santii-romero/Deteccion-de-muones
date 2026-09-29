"""Reproduce the adopted result from frozen evidence; optionally verify original TXT.

No historical reports or excluded first-acquisition events enter the likelihood.
"""
from pathlib import Path
import argparse,csv,hashlib,json,sys
from collections import Counter
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from muones.finite_window import fit,validate_local
from muones.io import sha256,Event
from muones.filters import classify
from muones.upload import blocks
from muones.scope import in_scope
from selection_helpers import regroup

ROOT=Path(__file__).resolve().parents[1]
DERIVED=ROOT/'data/derived'
OUT=ROOT/'results'


def read(path):
    with Path(path).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))


def write(path,rows):
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def check_inputs():
    manifest=json.loads((ROOT/'data/inputs_manifest.json').read_text(encoding='utf-8'))
    for path,digest in manifest.items():
        if sha256(ROOT/path)!=digest:raise ValueError('Frozen input changed: '+path)
    cfg=json.loads((ROOT/'config/lifetime_active.json').read_text(encoding='utf-8'))
    assert (ROOT/'config/lifetime_active.json').read_bytes()==(ROOT/'config/lifetime_txt_margin10_v3.json').read_bytes()
    assert cfg['n_samples']==1024 and cfg['background']=='fixed_zero' and cfg['event_weight']==1
    assert cfg['lower_ns']==120 and cfg['edge_margin_ns']==10
    assert cfg['exclude_prompt3_detected'] and cfg['ignore_late_ch1_veto']
    return cfg


def select(rows,cfg):
    result=[]
    for original in rows:
        r=dict(original)
        assert in_scope(r['source'],r['n_samples']) and r['source']==cfg['source']
        assert abs(float(r['fit_upper_ns'])-(float(r['record_end_ns'])-cfg['edge_margin_ns']))<1e-9
        if r['prompt3_status']=='detected':decision='veto_prompt3_detected'
        elif r['prompt3_status']=='ambiguous':decision='pending_prompt3_uncertain'
        elif r['count_status']!='accepted':decision='pending_initial_quality'
        elif r['user_quality_decision']=='exclude':decision='excluded_by_user'
        elif r['user_quality_decision']=='accept_quality' and not r['delay_ns']:decision='accepted_quality_time_unresolved'
        elif r['base_decision'] in ('selected','outside_fit_window') or r['user_quality_decision']=='accept_quality':
            t=float(r['delay_ns']);u=float(r['record_end_ns'])-cfg['edge_margin_ns']
            decision='outside_fit_window' if t<cfg['lower_ns'] else 'outside_upper_edge_margin' if t>u else 'selected'
        else:raise ValueError('Unresolved policy state: '+r['uid'])
        assert decision==r['decision'],r['uid']
        result.append(r)
    return result


def verify_original(path,cfg,ledger):
    assert sha256(path)==cfg['source_sha256'],'Original TXT hash mismatch'
    events={r['uid']:r for r in read(DERIVED/'txt_automatic_events.csv')}
    stored_pulses=read(DERIVED/'txt_automatic_pulses.csv')
    pp={}
    for p in stored_pulses:pp.setdefault(p['uid'],[]).append(p)
    rows={int(r['event_id']):r for r in ledger}
    late_evidence={}
    for p in read(DERIVED/'late_timing_evidence.csv'):
        late_evidence.setdefault(p['uid'],[]).append(p['pulse_id'])
    filters=json.loads((ROOT/'config/filters_v1_1024.json').read_text(encoding='utf-8'))
    checked=0;time_checked=0
    for key,start,end,a in blocks(path):
        assert key==checked+1 and a.shape==(1024,4) and np.all(np.diff(a[:,0])>0)
        r=rows[key];uid=r['uid'];e=events[uid]
        assert hashlib.sha256(a.astype('<f8').tobytes()).hexdigest()==e['upload_wave_sha256']
        new,pulses,groups=classify(Event(cfg['source'],'upload_decaimientos_sin_fecha',-1,key,key,'',start,a),filters)
        for field in ('t0_ns','count_status','prompt3_status','decay_status'):
            assert str(new[field])==e[field],(key,field)
        old=pp.get(uid,[]);assert len(old)==len(pulses)
        for p,q in zip(old,pulses):
            assert p['status']==q['status'] and p['reasons']==q['reasons']
            assert int(p['sample'])==q['sample'] and int(p['channel'])==q['channel']
            assert abs(float(p['time_ns'])-q['time_ns'])<1e-9
        assert abs(a[-1,0]-float(e['t0_ns'])-float(r['record_end_ns']))<1e-9
        if r['decision']=='selected':
            # Timing proposals were chosen before the final window; human review is frozen.
            catalog=[{**p,'time_ns':float(p['time_ns']),'channel':int(p['channel']),
                      'amplitude_mV':float(p['amplitude_mV'])} for p in old]
            groups={str(g['group_id']):g for g in regroup(catalog,float(e['t0_ns'])) if g['side']==1}
            group=groups[r['group_id']]
            target=[p for p in old if p['pulse_id'] in group['pulse_ids'].split(';') and int(p['channel']) in (2,3)]
            chosen=[p for p in target if p['status']=='accepted'] or [max(target,key=lambda p:float(p['amplitude_mV']))]
            if uid in late_evidence:
                # The reviewed late proposals explicitly record their timing seeds.
                # In particular #68 retains the exported mean of both CH2 seeds.
                chosen=[p for p in old if p['pulse_id'] in late_evidence[uid]]
            if r['timing_pulse_ids']:assert r['timing_pulse_ids'].split(';')==[p['pulse_id'] for p in chosen]
            assert chosen and all(int(p['channel']) in (2,3) for p in chosen)
            expected=np.mean([float(p['time_ns']) for p in chosen])-float(e['t0_ns'])
            assert abs(expected-float(r['delay_ns']))<1e-9,(key,expected,r['delay_ns'])
            time_checked+=1
        checked+=1
    assert checked==847 and time_checked==525
    assert sha256(path)==cfg['source_sha256']
    return dict(source_events=checked,selected_times_verified=time_checked,all_automatic_pulse_labels_reproduced=True,
                source_sha256=cfg['source_sha256'],source_path_recorded=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--txt',type=Path,help='Optional external original TXT; verify all 847 waveforms and selected times')
    parser.add_argument('--simulate',action='store_true',help='Repeat the 3000 conditional simulations with the recorded seed')
    args=parser.parse_args();cfg=check_inputs()
    ledger=select(read(DERIVED/'txt_event_decisions.csv'),cfg)
    selected=[r for r in ledger if r['decision']=='selected']
    assert len(ledger)==len({r['uid'] for r in ledger})==847
    reference=read(DERIVED/'txt_fit_events_reference.csv')
    assert len(selected)==525 and {r['uid'] for r in selected}=={r['uid'] for r in reference}
    for r,old in zip(selected,reference):
        assert r['uid']==old['uid'] and r['delay_ns']==old['delay_ns'] and r['fit_upper_ns']==old['upper_ns']
    t=np.array([float(r['delay_ns'])/1000 for r in selected])
    upper=np.array([float(r['fit_upper_ns'])/1000 for r in selected])
    result=fit(t,upper,lo=cfg['lower_ns']/1000)
    old=json.loads((DERIVED/'txt_fit_reference.json').read_text(encoding='utf-8'))
    assert abs(result['tau_us']-old['fit']['tau_us'])<1e-10
    for level in ('68','95'):np.testing.assert_allclose(result['intervals_us'][level],old['fit']['intervals_us'][level],rtol=1e-10)
    validation=validate_local(t,upper,result,2026092811) if args.simulate else old['local_validation']
    if args.simulate:
        for field in ('nominal_68_coverage','nominal_95_coverage','refitted_pit_ks_p'):
            assert abs(validation[field]-old['local_validation'][field])<1e-12
    raw=verify_original(args.txt,cfg,ledger) if args.txt else None
    payload=dict(fit_events=525,source_events=847,previous_events_used=0,background=0,event_weight=1,
        source=cfg['source'],source_sha256=cfg['source_sha256'],fit=result,decisions=dict(Counter(r['decision'] for r in ledger)),
        local_validation=validation,simulation_recomputed=args.simulate,raw_verification=raw)
    OUT.mkdir(parents=True,exist_ok=True)
    write(OUT/'fit_events.csv',reference);write(OUT/'event_decisions.csv',ledger)
    (OUT/'lifetime_fit.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    if args.txt or args.simulate:
        receipt=dict(script_sha256=sha256(Path(__file__)),inputs_manifest_sha256=sha256(ROOT/'data/inputs_manifest.json'),
                     raw_verification=raw,simulations_recomputed=args.simulate,local_validation=validation,fit_events=525)
        (OUT/'verification_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(dict(events=525,tau_us=result['tau_us'],intervals_us=result['intervals_us'],raw_verification=raw),indent=2))


if __name__=='__main__':main()
