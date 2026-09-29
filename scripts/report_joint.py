"""Joint LaTeX PDF and standalone HTML, using frozen evidence from both branches."""
import argparse,json,shutil,subprocess
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from reproduce import ROOT,DERIVED,OUT,read,check_inputs
from muones.io import sha256
from report_html import document

PDF=ROOT/'output/pdf/proyecto_muones.pdf';HTML=ROOT/'output/informe.html'
TEXDIR=ROOT/'output/latex';TEX=TEXDIR/'proyecto_muones.tex'
FIG=OUT/'figures';CCD=ROOT/'data/reference/ccd'
AUTHORS='Theo Del Compare y Santiago Romero'
PUBLIC_FIGURES=('signals.png','signals_pdf.png','lifetime.png','ccd_detections.png','ccd_composition.png')
BLUE,ORANGE='#285b78','#b95330'

def ccd_evidence():
    c=json.loads((DERIVED/'ccd_summary.json').read_text(encoding='utf-8'))
    for name,digest in c['source_sha256'].items():assert sha256(CCD/name)==digest,name
    assert sum(c['composition']['counts'].values())==c['composition']['traces']==6251
    assert c['raw_data_available'] is False
    return c

def figures(payload,ccd):
    FIG.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,
                         'axes.labelcolor':'#243746','text.color':'#243746','axes.edgecolor':'#667785'})
    samples=read(DERIVED/'example_waveforms.csv')
    events={r['event_id']:r for r in read(DERIVED/'txt_automatic_events.csv')}
    decisions={r['event_id']:r for r in read(DERIVED/'txt_event_decisions.csv')}
    categories=[('10','Secundario claro'),('8','Grupo mixto aprobado'),('142','Saturación conservada'),('373','Cola incompleta al final')]
    fig,axes=plt.subplots(2,2,figsize=(10,4.5))
    for ax,(key,title) in zip(axes.flat,categories):
        rows=[r for r in samples if r['event_id']==key]
        t=np.array([float(r['time_ns']) for r in rows])-float(events[key]['t0_ns'])
        delay=float(decisions[key]['delay_ns']);end=t[-1]
        for field,name,color in [('ch1_mV','CH1','#929aa2'),('ch2_mV','CH2',BLUE),('ch3_mV','CH3',ORANGE)]:
            ax.plot(t,[float(r[field]) for r in rows],lw=1.,color=color,label=name)
        ax.axvline(delay,color='#2b343b',lw=.9,ls='--')
        if key=='373':ax.axvspan(end-10,end,color='#f0c374',alpha=.4)
        ax.set(xlim=(max(0,delay-75),min(end,delay+95)),title=title,xlabel='Retardo desde CH1 [ns]',ylabel='Voltaje [mV]')
        ax.tick_params(labelsize=9);ax.title.set_fontsize(11)
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper center',ncol=3,frameon=False,bbox_to_anchor=(.5,1.))
    fig.tight_layout(rect=(0,0,1,.91),h_pad=1.3);fig.savefig(FIG/'signals.png',dpi=210);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,2.4))
    for ax,(key,title) in zip(axes,categories[:2]):
        rows=[r for r in samples if r['event_id']==key]
        t=np.array([float(r['time_ns']) for r in rows])-float(events[key]['t0_ns'])
        delay=float(decisions[key]['delay_ns'])
        for field,name,color in [('ch1_mV','CH1','#929aa2'),('ch2_mV','CH2',BLUE),('ch3_mV','CH3',ORANGE)]:
            ax.plot(t,[float(r[field]) for r in rows],lw=1.,color=color,label=name)
        ax.axvline(delay,color='#2b343b',lw=.9,ls='--')
        ax.set(xlim=(delay-75,delay+95),title=title,xlabel='Retardo desde CH1 [ns]',ylabel='Voltaje [mV]')
        ax.tick_params(labelsize=9);ax.title.set_fontsize(11)
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper center',ncol=3,frameon=False,bbox_to_anchor=(.5,1.04))
    fig.tight_layout(rect=(0,0,1,.88));fig.savefig(FIG/'signals_pdf.png',dpi=220);plt.close(fig)
    rows=read(OUT/'fit_events.csv');t=np.array([float(r['delay_ns'])/1000 for r in rows])
    u=np.array([float(r['upper_ns'])/1000 for r in rows]);beta=payload['fit']['beta_per_us'];lo=.12
    edges=lo+np.arange(19)*.08;observed,_=np.histogram(t,bins=edges);expected=[]
    for left,right in zip(edges[:-1],edges[1:]):
        lower=max(lo,left);upper=np.minimum(u,right)
        mass=np.where(upper>lower,(np.exp(-beta*lower)-np.exp(-beta*upper))/(np.exp(-beta*lo)-np.exp(-beta*u)),0.)
        expected.append(float(mass.sum()))
    assert observed.sum()==len(rows)==525 and abs(sum(expected)-525)<1e-8
    fig,ax=plt.subplots(figsize=(9,3.65))
    ax.bar(edges[:-1],observed,width=np.diff(edges),align='edge',color='#729cb5',edgecolor='white',linewidth=.8,label='525 retardos observados')
    label=f'Exponencial truncada: τ = {payload["fit"]["tau_us"]:.3f} µs'.replace('.',',')
    ax.stairs(expected,edges,lw=2.2,color=ORANGE,label=label)
    ax.set(xlim=(.12,1.56),ylim=(0,max(max(expected),max(observed))*1.12),xlabel='Retardo desde el pulso inicial [µs]',ylabel='Eventos por intervalo de 80 ns')
    legend=ax.legend(loc='lower center',bbox_to_anchor=(.5,1.035),ncol=2,frameon=False,fontsize=10)
    fig.tight_layout();fig.canvas.draw();renderer=fig.canvas.get_renderer()
    assert legend.get_window_extent(renderer).y0>ax.get_window_extent(renderer).y1
    fig.savefig(FIG/'lifetime.png',dpi=220);plt.close(fig)
    (OUT/'report_plot_data.json').write_text(json.dumps({'bin_edges_us':edges.tolist(),'observed_counts':observed.tolist(),
        'expected_counts':expected,'observed_total':int(observed.sum()),'expected_total':sum(expected),
        'fit_events':525,'normalization':'individual record windows','lifetime_legend_outside_axes':True},indent=2),encoding='utf-8')
    shutil.copy2(CCD/'detections_source.png',FIG/'ccd_detections.png')
    counts=ccd['composition']['counts'];pairs=[('electron','Electrón'),('puntual','Puntual'),('muon','Muón'),('artefacto','Artefacto')]
    values=[counts[k] for k,_ in pairs];fig,ax=plt.subplots(figsize=(9,3.35))
    bars=ax.barh([name for _,name in pairs],values,color=['#64a986','#719dbf','#bf694e','#9c85b2'],height=.6)
    ax.invert_yaxis();ax.set(xlabel='Trazas clasificadas en 30 imágenes',xlim=(0,max(values)*1.25))
    ax.spines[['left','top','right']].set_visible(False);ax.tick_params(axis='y',length=0)
    for bar,value in zip(bars,values):
        label=f'{value:,}'.replace(',',' ')+f'  ({100*value/6251:.1f} %)'.replace('.',',')
        ax.text(value+45,bar.get_y()+bar.get_height()/2,label,va='center',fontsize=11)
    fig.tight_layout();fig.savefig(FIG/'ccd_composition.png',dpi=210);plt.close(fig)

def latex(payload,ccd):
    template=(ROOT/'scripts/templates/report.tex').read_text(encoding='utf-8')
    fit=payload['fit'];ci=fit['intervals_us'];fmt=lambda x:f'{x:.3f}'.replace('.',r'{,}')
    nn=ccd['network_validation'];stats=ccd['composition']
    names=[('artefacto','Artefacto'),('muon','Muón'),('electron','Electrón'),('puntual','Puntual')]
    nnfmt=lambda x:f'{x:.2f}'.replace('.',r'{,}')
    nn_rows='\n'.join(f'{name} & {nnfmt(nn[k]["map50"])} & {nnfmt(nn[k]["precision"])} & {nnfmt(nn[k]["recall"])} '+r'\\' for k,name in names)
    amp_rows='\n'.join(f'{i+1} & {g} $\\pm$ {sg} & {fmt(n)} $\\pm$ {fmt(sn)} '+r'\\'
        for i,(g,sg,n,sn) in enumerate(zip(stats['gain_adu_per_e'],stats['gain_std'],stats['noise_e'],stats['noise_std'])))
    repl={'TAU':fmt(fit['tau_us']),'LOW68':fmt(ci['68'][0]),'HIGH68':fmt(ci['68'][1]),
          'LOW95':fmt(ci['95'][0]),'HIGH95':fmt(ci['95'][1]),'AMP_ROWS':amp_rows,'NN_ROWS':nn_rows}
    for key,value in repl.items():template=template.replace('@@'+key+'@@',value)
    assert '@@' not in template
    (TEXDIR/'figures').mkdir(parents=True,exist_ok=True)
    for name in PUBLIC_FIGURES:shutil.copy2(FIG/name,TEXDIR/'figures'/name)
    TEX.write_text(template,encoding='utf-8')

def compile_pdf():
    executable=shutil.which('pdflatex')
    if executable is None:raise RuntimeError('Install a LaTeX distribution with pdflatex (MiKTeX or TeX Live).')
    build=ROOT/'tmp/latex';build.mkdir(parents=True,exist_ok=True)
    command=[executable,'--interaction=nonstopmode','--halt-on-error','--file-line-error','--output-directory='+str(build),'proyecto_muones.tex']
    for _ in range(2):
        r=subprocess.run(command,cwd=TEXDIR,capture_output=True,text=True,encoding='utf-8',errors='replace')
        (build/'compiler_stdout.txt').write_text(r.stdout+r.stderr,encoding='utf-8')
        if r.returncode:raise RuntimeError('LaTeX compilation failed; see tmp/latex/compiler_stdout.txt')
    PDF.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(build/'proyecto_muones.pdf',PDF)

def finalize():
    import pymupdf
    with pymupdf.open(PDF) as p:
        assert len(p)<=5 and 'pdfTeX' in p.metadata.get('producer','')
        assert AUTHORS==p.metadata['author']
    paths=[Path(__file__),ROOT/'scripts/build_report.py',ROOT/'scripts/report_html.py',ROOT/'scripts/templates/report.tex',
        OUT/'lifetime_fit.json',DERIVED/'ccd_summary.json',ROOT/'data/ccd_inputs_manifest.json',
        ROOT/'data/report_changes_manifest.json',ROOT/'data/reference/temporal/lifetime_previous.png',OUT/'report_plot_data.json',HTML,PDF,TEX]
    paths += [FIG/name for name in PUBLIC_FIGURES]+[TEXDIR/'figures'/name for name in PUBLIC_FIGURES]
    (OUT/'report_manifest.json').write_text(json.dumps({p.relative_to(ROOT).as_posix():sha256(p) for p in paths},indent=2),encoding='utf-8')
    print(PDF);print(HTML)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only',action='store_true',help='Generate figures, HTML and LaTeX; compile separately')
    parser.add_argument('--finalize-only',action='store_true',help='Record hashes after external compilation')
    args=parser.parse_args()
    if args.finalize_only:finalize();return
    check_inputs();p=json.loads((OUT/'lifetime_fit.json').read_text(encoding='utf-8'));c=ccd_evidence()
    figures(p,c);latex(p,c);HTML.write_text(document(p,c,FIG),encoding='utf-8')
    if not args.prepare_only:compile_pdf();finalize()

if __name__=='__main__':main()
