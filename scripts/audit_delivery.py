"""Check the scientific result and the compact deliverable, including compressed evidence."""
import ast,base64,csv,gzip,json,re
from pathlib import Path
from collections import Counter
from html.parser import HTMLParser
import numpy as np
import pymupdf
from reproduce import ROOT,DERIVED,OUT,read,check_inputs,select
from muones.io import sha256
from muones.finite_window import density


class Links(HTMLParser):
    def __init__(self):
        super().__init__();self.targets=[];self.ids=set();self.images=[];self.sections=0
        self.body=False;self.skip=0;self.text=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='body':self.body=True
        if tag in ('script','style'):self.skip+=1
        if 'id' in a:self.ids.add(a['id'])
        if tag=='section':self.sections+=1
        if tag=='a':self.targets.append(a.get('href',''))
        if tag=='img':self.images.append(a.get('src',''))
    def handle_endtag(self,tag):
        if tag=='body':self.body=False
        if tag in ('script','style'):self.skip-=1
    def handle_data(self,data):
        if self.body and not self.skip:self.text.append(data)


def check_ccd():
    """Validate frozen documentary evidence; do not simulate missing CCD data."""
    manifest=json.loads((ROOT/'data/ccd_inputs_manifest.json').read_text(encoding='utf-8'))
    assert len(manifest)==11
    for path,digest in manifest.items():assert sha256(ROOT/path)==digest,path
    c=json.loads((DERIVED/'ccd_summary.json').read_text(encoding='utf-8'))
    assert c['raw_data_available'] is False and c['user_confirmed_unavailable'] is True
    assert c['status']=='documented_previous_analysis_not_reexecuted'
    assert c['commit']=='fd262213fcaab221b771617b49f47769f9e1c83c'
    source=ROOT/'data/reference/ccd'
    for name,digest in c['source_sha256'].items():assert sha256(source/name)==digest
    text=(source/'summary_source.txt').read_text(encoding='utf-8')
    counts=ast.literal_eval(re.search(r'por clase: (\{[^\n]+\})',text).group(1))
    assert counts==c['composition']['counts'] and sum(counts.values())==6251
    assert c['composition']['images']==int(re.search(r'imagenes: (\d+)',text).group(1))==30
    assert c['network_validation']['reference_traces']==15434
    assert c['hybrid_comparison']['reference_traces']==15554
    assert c['network_validation']['images']==300 and c['hybrid_comparison']['files']==75
    assert c['network_validation']['labels']=='automatic_morphological_rules'
    assert sha256(OUT/'figures/ccd_detections.png')==c['source_sha256']['detections_source.png']
    return c


def check_plot(fit,payload):
    """Independently integrate the density over the displayed histogram bins."""
    plot=json.loads((OUT/'report_plot_data.json').read_text(encoding='utf-8'))
    edges=np.asarray(plot['bin_edges_us'])
    t=np.array([float(r['delay_ns'])/1000 for r in fit])
    observed,_=np.histogram(t,bins=edges)
    assert np.allclose(np.diff(edges),.08) and observed.tolist()==plot['observed_counts']
    assert int(observed.sum())==plot['observed_total']==plot['fit_events']==525
    upper_counts=Counter(float(r['upper_ns'])/1000 for r in fit)
    beta=payload['fit']['beta_per_us'];expected=[]
    for a,b in zip(edges[:-1],edges[1:]):
        total=0.
        for upper,n in upper_counts.items():
            if upper<=a:continue
            x=np.linspace(a,min(b,upper),501)
            total+=n*np.trapezoid(density(x,beta,.12,upper),x)
        expected.append(total)
    assert np.allclose(expected,plot['expected_counts'],atol=1e-6,rtol=1e-8)
    assert abs(sum(expected)-525)<1e-6 and abs(plot['expected_total']-525)<1e-8
    assert plot['lifetime_legend_outside_axes'] is True


def public_text_check(text):
    assert not re.search(r'laboratorio\s*5\b',text,re.I),'Removed course label in public report'
    assert not re.search(r'#\s*\d+\b',text),'Individual event IDs in public narrative'
    assert not re.search(r'PAblo|decaimientos\.txt|Med_con_Decaimientos|run_\d+',text,re.I)
    assert 'plomo' in text and 'Skipper' in text


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
    presentation=json.loads((ROOT/'data/report_changes_manifest.json').read_text(encoding='utf-8'))
    assert set(presentation)=={'results/figures/lifetime.png'}
    for dst,item in json.loads((DERIVED/'migration_provenance.json').read_text(encoding='utf-8')).items():
        if item.get('representation')=='lossless gzip':
            import hashlib
            with gzip.open(ROOT/dst,'rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==item['sha256']
        elif dst in presentation:
            change=presentation[dst]
            assert change['previous_sha256']==item['sha256']
            assert sha256(ROOT/change['previous_preserved_path'])==item['sha256']
            assert sha256(ROOT/dst)==change['current_sha256']
        else:assert sha256(ROOT/dst)==item['sha256']
    receipt=json.loads((OUT/'verification_receipt.json').read_text(encoding='utf-8'))
    assert receipt['script_sha256']==sha256(ROOT/'scripts/reproduce.py')
    assert receipt['inputs_manifest_sha256']==sha256(ROOT/'data/inputs_manifest.json')
    assert receipt['raw_verification']['selected_times_verified']==525 and receipt['simulations_recomputed']
    assert receipt['local_validation']==payload['local_validation']
    ccd=check_ccd();check_plot(fit,payload)
    for path,digest in json.loads((OUT/'report_manifest.json').read_text(encoding='utf-8')).items():assert sha256(ROOT/path)==digest
    pdf=ROOT/'output/pdf/proyecto_muones.pdf';web=ROOT/'output/informe.html'
    expected_mails={'mailto:Theo.Del.Compare@gmail.com','mailto:romerosantiago545@gmail.com'}
    tex=(ROOT/'output/latex/proyecto_muones.tex').read_text(encoding='utf-8')
    headings=re.findall(r'^\\section\{([^}]+)\}',tex,re.M)
    assert headings==['Objetivo del proyecto','Desarrollo y análisis con centelladores',
        'Desarrollo y análisis del detector con datos del Laboratorio Lambda','Discusión conjunta y comparativa']
    # Temporary environments are not delivery artifacts.
    files=[p for p in ROOT.rglob('*') if p.is_file() and not any(x in p.relative_to(ROOT).parts for x in ('tmp','.venv','__pycache__','.git'))]
    assert [p for p in files if p.suffix.lower()=='.pdf']==[pdf]
    assert [p for p in files if p.suffix.lower()=='.html']==[web]
    with pymupdf.open(pdf) as doc:
        assert len(doc)==5
        assert 'pdfTeX' in doc.metadata['producer']
        assert doc.metadata['author']=='Theo Del Compare y Santiago Romero'
        pdf_text='\n'.join(p.get_text() for p in doc)
        public_text_check(pdf_text)
        assert all(word in pdf_text for word in ('Claude','Anthropic','Codex','OpenAI','Laboratorio Lambda'))
        assert '28 de septiembre de 2026' not in pdf_text
        pdf_links={link.get('uri','') for p in doc for link in p.get_links()}
        assert not any(uri.startswith('mailto:') for uri in pdf_links)
        assert 'Theo.Del.Compare@gmail.com' not in pdf_text
        first=doc[0]
        name_rects=[first.search_for(name) for name in ('Theo Del Compare','Santiago Romero')]
        email_rects=[first.search_for(email) for email in ('theo.del.compare@gmail.com','romerosantiago545@gmail.com')]
        assert all(len(rects)==1 for rects in name_rects+email_rects)
        assert min(rects[0].y0 for rects in email_rects)>max(rects[0].y1 for rects in name_rects)
        assert 0<name_rects[1][0].x0-name_rects[0][0].x1<18
        title_spans=[span for block in first.get_text('dict')['blocks'] if 'lines' in block
                     for line in block['lines'] for span in line['spans']
                     if span['bbox'][1]<80 and span['size']>15]
        assert title_spans and all(abs(span['size']-16)<.1 for span in title_spans)
        for link in first.get_links():
            assert all(not link['from'].intersects(rects[0]) for rects in name_rects+email_rects)
        for i,p in enumerate(doc):
            assert p.get_text().strip().endswith(str(i+1))
            for block in p.get_text('blocks'):
                assert block[0]>=20 and block[1]>=10 and block[2]<=575 and block[3]<=829
        assert '525' in doc[1].get_text() and '1,948' in doc[1].get_text()
        assert 'Skipper' in doc[2].get_text() and '6251' in doc[3].get_text()
        assert '15' in doc[3].get_text() and 'Discusión' in doc[4].get_text()
    parser=Links();parser.feed(web.read_text(encoding='utf-8'))
    assert parser.sections==7 and len(parser.images)==4
    html_text=re.sub(r'\s+',' ',' '.join(parser.text))
    public_text_check(html_text)
    assert 'Theo Del Compare y Santiago Romero' in html_text
    assert all(word in html_text for word in ('Claude','Anthropic','Codex','OpenAI','Laboratorio Lambda'))
    assert '28 SEPTIEMBRE 2026' not in html_text
    assert expected_mails<=set(parser.targets)
    for target in parser.targets:
        if target.startswith('#'):assert target[1:] in parser.ids
        elif target.startswith('https://') or target in expected_mails:pass
        else:assert (web.parent/target).resolve().is_file(),target
    for src in parser.images:
        assert src.startswith('data:image/png;base64,')
        assert base64.b64decode(src.split(',',1)[1],validate=True).startswith(b'\x89PNG')
    qa=json.loads((OUT/'visual_qa.json').read_text(encoding='utf-8'))
    assert qa['pdf_pages_inspected']==5 and qa['pdf_sha256']==sha256(pdf)
    assert qa['html_sha256']==sha256(web)
    for mode in ('desktop','mobile'):
        browser=qa['browser_checks'][mode]
        assert browser['no_horizontal_overflow'] and not browser['public_text_has_event_id']
        assert browser['sections']==7 and len(browser['cases'])==7
        assert all(i['loaded'] for i in browser['images']) and len(browser['images'])==4
        assert '525 eventos' in browser['default_result']
    result=dict(status='passed',events_txt=847,selected_txt=525,previous_events_in_likelihood=0,
        previous_event_decisions_preserved=192680,excluded_300_metadata_preserved=23727,
        tests_passed=31,raw_waveform_verification_receipt=True,simulation_reproduction_receipt=True,
        pdf_files=1,pdf_pages=5,pdf_created_with_latex=True,html_files=1,html_embedded_images=4,
        scope='joint_temporal_and_spatial_report',ccd_documentary_sources_verified=11,
        ccd_raw_data_available=False,ccd_analysis_reexecuted=False,
        ccd_composition_traces=ccd['composition']['traces'],
        ccd_network_reference_traces=ccd['network_validation']['reference_traces'],
        ccd_hybrid_reference_traces=ccd['hybrid_comparison']['reference_traces'],
        histogram_normalization_verified=True,lifetime_legend_outside_axes=True,
        pdf_main_sections=4,publication_date_removed=True,html_author_mail_links_verified=True,
        course_label_removed=True,pdf_names_unlinked=True,pdf_emails_unlinked=True,
        pdf_emails_below_names=True,pdf_names_compact_spacing=True,pdf_title_size_tex_pt=16,
        ai_assistance_acknowledged=True,lambda_role='data_provider_confirmed_by_user',
        nominal_intervals_conditional_on_model=True,html_browser_visual_check=qa['html_browser_visual_check'])
    (OUT/'audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    files=[p for p in ROOT.rglob('*') if p.is_file() and not any(x in p.relative_to(ROOT).parts for x in ('tmp','.venv','__pycache__','.git'))
           and p.name!='delivery_manifest.json' and not p.name.startswith('.local_')]
    (ROOT/'delivery_manifest.json').write_text(json.dumps({p.relative_to(ROOT).as_posix():sha256(p) for p in sorted(files)},indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
