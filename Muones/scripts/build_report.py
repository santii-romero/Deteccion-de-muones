"""Generate the only delivery HTML and five-page PDF from the same content."""
from pathlib import Path
import argparse,base64,html,json,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak,KeepTogether
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reproduce import ROOT,DERIVED,OUT,read,check_inputs
from muones.io import sha256

PDF=ROOT/'output/pdf/proyecto_muones.pdf'
HTML=ROOT/'output/informe.html'
BLUE='#203e54';ORANGE='#b9792f'
AUTHORS='Theo Del Compare y Santiago Romero'


def figures():
    (OUT/'figures').mkdir(parents=True,exist_ok=True)
    fig,ax=plt.subplots(figsize=(10,2.4),layout='constrained');ax.set(xlim=(0,10),ylim=(0,4));ax.axis('off')
    for y,label,sub in [(3.15,'CH1 - superior','Disparo'),(1.95,'CH2 - central','Respuesta exigida'),(.45,'CH3 - inferior','Respuesta no exigida')]:
        ax.add_patch(Rectangle((1,y),4,.42,color='#7699ad'));ax.text(5.3,y+.21,label+' / '+sub,va='center',fontsize=11,color=BLUE)
    ax.add_patch(Rectangle((1,1.22),4,.24,color='#bd9360'));ax.text(5.3,1.34,'Barra de metal pesado (material sin confirmar)',va='center',fontsize=10,color=ORANGE)
    ax.annotate('',xy=(.58,.42),xytext=(.58,3.8),arrowprops=dict(arrowstyle='->',lw=1.8,color=BLUE))
    ax.text(.26,2.05,'Trayectoria ilustrativa',rotation=90,ha='center',va='center',fontsize=9)
    fig.savefig(OUT/'figures/setup.png',dpi=170);plt.close(fig)
    examples=read(DERIVED/'example_waveforms.csv');events={r['event_id']:r for r in read(DERIVED/'txt_automatic_events.csv')}
    decisions={r['event_id']:r for r in read(DERIVED/'txt_event_decisions.csv')}
    titles={'10':'Secundario limpio; seleccionado','8':'Grupo mixto; calidad aprobada','142':'Saturación conservada; aprobado','373':'Cola incompleta; fuera por margen'}
    fig,axes=plt.subplots(2,2,figsize=(10,4.8),layout='constrained')
    for ax,key in zip(axes.flat,['10','8','142','373']):
        a=[r for r in examples if r['event_id']==key];t=np.array([float(r['time_ns']) for r in a])-float(events[key]['t0_ns'])
        delay=float(decisions[key]['delay_ns']);end=t[-1]
        for field,label,color in [('ch1_mV','CH1','#8d9399'),('ch2_mV','CH2','#497c9c'),('ch3_mV','CH3','#bd7e35')]:
            ax.plot(t,[float(r[field]) for r in a],lw=.8,color=color,label=label)
        ax.axvline(delay,color='#203e54',lw=.8,ls='--')
        if key=='373':ax.axvspan(end-10,end,color='#e3b65f',alpha=.3)
        ax.set(xlim=(max(0,delay-75),min(end,delay+95)),title=f'#{key}: {titles[key]}',xlabel='Retardo desde CH1 [ns]',ylabel='Voltaje [mV]')
        ax.tick_params(labelsize=8);ax.title.set_fontsize(9);ax.spines[['top','right']].set_visible(False)
    axes[0,0].legend(frameon=False,fontsize=8,ncol=3,loc='lower right')
    fig.savefig(OUT/'figures/signals.png',dpi=175);plt.close(fig)


def content(payload):
    tau=payload['fit']['tau_us'];ci=payload['fit']['intervals_us'];fmt=lambda x:f'{x:.3f}'.replace('.',',')
    txt=lambda s:('text',s)
    table=lambda h,r:('table',(h,r))
    image=lambda name,height,caption:('image',(name,height,caption))
    sections=[('1. Objetivo, montaje y datos',[
        txt('Este proyecto analiza señales de centelladores para seleccionar coincidencias y candidatos compatibles con detención y decaimiento de muones, preservar casos ambiguos y estimar una vida media en una ventana temporal finita. La etapa Skipper-CCD prevista no se desarrolló aquí.'),
        txt('Los muones producen pulsos en el montaje; un pulso inicial seguido por uno secundario apartado motiva la búsqueda de decaimientos. Esa morfología también puede aparecer por respuestas instrumentales o coincidencias accidentales. La referencia docente [1] orienta el análisis; las aclaraciones de adquisición del usuario prevalecen.'),
        image('setup.png',125,'Montaje esquemático, sin escala. CH1 dispara; CH2 se exige para guardar; CH3 no. La barra está entre CH2 y CH3, sin material ni dimensiones confirmados.'),
        table(['Adquisición','Archivos','Eventos'],[['03/09 - 15:21','53','5019'],['03/09 - 18:40','2','156'],['04/09 - 13:43','459','64038'],['07/09 - 14:04','575','85843'],['09/09 - 14:26','284','37624'],['Subtotal cinco corridas','1373','192680'],['TXT independiente, sin fecha','1','847']]),
        txt('Solo 1024 muestras por evento: tiempo en ns, tres voltajes en mV, extremos 0 y 1698,340 ns y paso aproximado 1,660 ns. Los 23727 registros de 300 puntos se excluyeron de todo análisis. El TXT tiene cinco columnas y fue guardado por presentar pico secundario separado; su lógica exacta y fecha no se conservan.'),
        txt('Se verificaron bloques, unidades, ejes, duplicados e integridad. En PAblo faltan el inicio y dos índices internos. El eje exportado compartido no garantiza alineación entre canales; ts no se usa como retardo ni como tiempo vivo. No se conoce el código real del rechazo de positivos durante adquisición [3].')
    ]),('2. Filtros y revisión de señales',[
        txt('El filtro opera sobre muestras originales, sin suavizado. Base y ruido se estiman por mediana y 1,4826 MAD fuera de 160-300 ns, con un recorte robusto solo para estimar la base. Todas las semillas detectadas conservan métricas, estado y motivos; la escala MAD no es una significancia gaussiana.'),
        table(['Operación','Regla congelada v1'],[['Semilla negativa','Altura max(45 mV,3σ); prominencia max(30 mV,2,5σ)'],['Resolución / amplitud','Separación ≥5 ns; aceptación ≥max(80 mV,4,5σ)'],['Forma','Ancho 3-35 ns a mitad de altura; ≥2 muestras'],['Coincidencia inicial','CH1/CH2 en 170-270 ns; separación ≤15 ns'],['Fallos duros','Ruido >60 mV, base saturada, impulso aislado u oscilación'],['Marcas ambiguas','Saturación local, deriva, lóbulo positivo, ancho o borde']]),
        txt('Para la vida media se exige coincidencia inicial aceptada y CH3 inicial no detectado sobre umbral. CH1 tardío no veta ni define el retardo del secundario CH2/CH3. Un grupo puede tener un pulso limpio y otra semilla débil; tras revisión el usuario aprobó los grupos mixtos. Se mantienen las etiquetas automáticas originales.'),
        image('signals.png',227,'Cuatro trazas originales del TXT, ampliadas alrededor del secundario. #142 conserva saturación; #373 guarda el mínimo pero no toda la cola. La aprobación morfológica no certifica identidad física.'),
        txt('El flag automático de borde usa 35 ns. Tras inspección y decisión humana, la ventana final del ajuste usa 10 ns, conservando aquel flag. Un fallo tardío no invalida por sí solo la coincidencia inicial. La selección para conteo, para eficiencia y para vida media tiene objetivos distintos.')
    ]),('3. Selecciones y controles de fondo',[
        txt('En las cinco corridas previas hubo 182709 coincidencias aceptadas, 9835 ambiguas y 136 excluidas. De 197 candidatos automáticos revisados, 195 mostraron secundario distinguible y dos quedaron dudosos. La revisión fue no ciega y no midió pureza física. Por decisión del usuario ninguno de esos eventos entra en el ajuste final.'),
        txt('Los controles compararon ventanas anteriores y posteriores de 120-170 ns, con selecciones y bordes pareados: 87915 padres elegibles, tres secundarios anteriores y 15 posteriores. El tramo anterior corto y la posible respuesta tardía instrumental limitan una extrapolación. El control triple ponderado es descriptivo y no se trató como fondo puro.'),
        txt('El TXT es una adquisición independiente preseleccionada por secundario; carece de una muestra de disparos sin seleccionar. Los controles anteriores no calibran su fondo. El modelo final fija fondo cero por instrucción del usuario, como hipótesis de análisis. No se resta una tasa anterior al TXT.'),
        table(['Estado final de las 847 trazas del TXT','N'],[['Seleccionados','525'],['CH3 inicial detectado','212'],['CH3 inicial incierto','41'],['Calidad inicial pendiente','8'],['Bajo 120 ns','44'],['Exclusión explícita del usuario','8'],['Aprobados sin tiempo utilizable','7'],['Fuera por margen final de 10 ns','2'],['Total','847']]),
        txt('La revisión de 88 casos resolvió 80 aprobaciones y ocho exclusiones. Con la ventana final: 67 seleccionados, cuatro bajo 120 ns, dos por borde y siete sin tiempo. Exclusiones explícitas: #14, #107, #278, #325, #397, #418, #733 y #781. No se inventaron notas del usuario ni tiempos para agregar eventos.'),
        txt('Quedan sin tiempo secundario utilizable #81, #201, #429, #448, #569, #593 y #627. Las 41 dudas de CH3 inicial y ocho de calidad inicial permanecen identificadas. La entrega conserva decisiones por todas las trazas y por las corridas previas; no presenta los pendientes como descartes físicos demostrados.')
    ]),('4. Vida media: modelo y resultado final',[
        txt(f'<b>525 eventos =500 conservados +13 limpios tardíos +12 tardíos aprobados.</b><br/><b>τ = {fmt(tau)} µs</b>; intervalo estadístico nominal 68 % [{fmt(ci["68"][0])};{fmt(ci["68"][1])}] µs y 95 % [{fmt(ci["95"][0])};{fmt(ci["95"][1])}] µs. Solo TXT independiente, fondo cero y peso 1 por evento.'),
        txt('El ajuste usa los tiempos individuales por máxima verosimilitud. Cada registro tiene 120 ns ≤t≤U_i, con U_i=t_final_i-t_CH1_inicial_i-10 ns. La exponencial se normaliza en su intervalo observable: p(t|τ,U_i)=exp(-t/τ)/{τ[exp(-120 ns/τ)-exp(-U_i/τ)]}. No se usa la media truncada como τ ni se prolonga artificialmente el registro hasta infinito.'),
        image('lifetime.png',215,'Datos y predicción integrada por ventana individual. Los bins finales de 40 ns se expresan como eventos equivalentes por 80 ns. El histograma ilustra; el ajuste no depende de sus bins.'),
        table(['Cota superior comparada','N','τ [µs]'],[['Común 1400 ns','500','1,799'],['Fin individual -35 ns','515','1,832'],['Fin individual -25 ns','523','2,027'],['Fin individual -10 ns (adoptada)','525','1,948'],['Fin individual completo','527','1,923']]),
        txt('Se inspeccionaron los 27 tardíos en siete láminas. #373/#737 están a 4,981/8,301 ns del final y no guardan cola completa: quedan fuera por margen, con calidad aprobada conservada. El usuario eligió 10 ns por esos bordes, no por aproximarse al valor tabulado. #68 conserva el tiempo exportado como promedio de dos semillas CH2.')
    ]),('5. Validación, alcance y reproducibilidad',[
        txt('Pasaron 31 pruebas de lectura, alcance, pulsos, ventanas, pesos y likelihood. Se verificaron las 847 trazas y etiquetas automáticas contra el TXT original y los 525 tiempos contra muestras CH2/CH3; el ajuste compacto reproduce exactamente la selección adoptada. Las pruebas son comprobaciones de código, no eventos físicos certificados.'),
        txt('3000 simulaciones condicionales con 525 retardos, semilla 2026092811 y τ generador=1,947766 µs dieron cobertura local nominal 68/95 % de 67,77/94,87 % y KS con reajuste p=0,786. Su repetición coincidió con la validación anterior. Son tiempos artificiales bajo el modelo y no se suman a la estadística real ni simulan la electrónica.'),
        txt('Los filtros se examinaron también con 7128 inyecciones CH2 sobre fondos reales y 7776 ensayos pareados posteriores. La recuperación depende de amplitud, forma, retardo y fondo; no constituye eficiencia universal de CH2/CH3. Las inyecciones que reutilizan una traza están correlacionadas.'),
        txt('<b>Interpretación.</b> Los intervalos estadísticos expresan fluctuación por muestra finita bajo el modelo. No incluyen sistemáticos de aceptación temporal, selección de adquisición, calibración entre canales, afterpulses o material de la barra. La ventana corta limita la información de la cola. No se midió flujo absoluto ni eficiencia de CH2 con una muestra ya seleccionada por CH2.'),
        txt('El resultado es compatible, dentro del intervalo nominal 68 %, con aproximadamente 2,197 µs de la hoja PDG histórica aportada [2]. Esa compatibilidad no valida pureza, aceptación ni el modelo. Se concluye esta etapa con un estimador condicionado, decisiones trazables y casos pendientes preservados.'),
        txt('<b>Reproducción.</b> Dependencias fijadas en requirements.txt. Ejecutar scripts/reproduce.py, las pruebas, scripts/build_report.py y scripts/audit_delivery.py. Con --txt se verifica el original externo; --simulate repite las simulaciones. Los hashes, entradas congeladas y decisiones quedan en data/ y los resultados en results/. Los originales e informes parciales se conservan en un respaldo local externo.'),
        txt('<b>Referencias.</b> [1] Del Compare, Pellegrino y Romero, Guía de la práctica de muones, Grupo 9, FCEN-UBA, documento aportado, 9 pp. [2] PDG, Nakamura et al., J. Phys. G 37, 075021 (2010), actualización 2011, hoja del muón p. 2: <link href="https://pdg.lbl.gov/2011/listings/rpp2011-list-muon.pdf" color="#245b82">pdg.lbl.gov/2011</link>. [3] <link href="https://www.psi.ch/drs/DocumentationEN/manual_rev50.pdf" color="#245b82">PSI: DRS4 V5</link>. [4] <link href="https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.find_peaks.html" color="#245b82">SciPy: find_peaks</link>. Material docente adicional aportado: Vida media del muón y Escuela de Buenos Aires - Instrumentación; referencias completas en docs/REFERENCIAS.md.')
    ])]
    return sections


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse-figures',action='store_true',help='Retain the existing verified figures for an editorial-only update')
    args=parser.parse_args()
    check_inputs();payload=json.loads((OUT/'lifetime_fit.json').read_text(encoding='utf-8'))
    if args.reuse_figures:
        manifest=json.loads((OUT/'report_manifest.json').read_text(encoding='utf-8'))
        for name in ('setup.png','signals.png','lifetime.png'):
            path='results/figures/'+name
            assert sha256(ROOT/path)==manifest[path],path
    else:figures()
    fontdir=Path(matplotlib.get_data_path())/'fonts/ttf'
    for name,file in [('DejaVu','DejaVuSans.ttf'),('DejaVu-Bold','DejaVuSans-Bold.ttf')]:pdfmetrics.registerFont(TTFont(name,str(fontdir/file)))
    pdfmetrics.registerFontFamily('DejaVu',normal='DejaVu',bold='DejaVu-Bold',italic='DejaVu',boldItalic='DejaVu-Bold')
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle('ReportTitle',fontName='DejaVu-Bold',fontSize=19,leading=25,textColor=colors.HexColor(BLUE),spaceAfter=15))
    styles.add(ParagraphStyle('ReportText',fontName='DejaVu',fontSize=9.3,leading=13.5,spaceAfter=9,textColor=colors.HexColor(BLUE)))
    styles.add(ParagraphStyle('CaptionSmall',fontName='DejaVu',fontSize=8,leading=11,spaceAfter=10,textColor=colors.HexColor('#526878')))
    styles.add(ParagraphStyle('CellSmall',fontName='DejaVu',fontSize=8.2,leading=11,textColor=colors.HexColor(BLUE)))
    sections=content(payload);story=[]
    for number,(title,items) in enumerate(sections,1):
        if number>1:story.append(PageBreak())
        story.append(Paragraph(title,styles['ReportTitle']))
        for kind,data in items:
            if kind=='text':story.append(Paragraph(data,styles['ReportText']))
            elif kind=='image':
                name,height,caption=data;p=OUT/'figures'/name
                story.append(Image(str(p),width=483,height=height,kind='proportional'))
                story.append(Paragraph(caption,styles['CaptionSmall']))
            else:
                headers,rows=data
                body=[[Paragraph(html.escape(str(x)),styles['CellSmall']) for x in row] for row in [headers]+rows]
                widths=[245,80,158] if len(headers)==3 else [245,238]
                if len(headers)==3 and headers[0]=='Adquisición':widths=[303,80,100]
                t=Table(body,colWidths=widths,hAlign='LEFT')
                t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e2ecf2')),('VALIGN',(0,0),(-1,-1),'TOP'),
                    ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f5f8fa')]),
                    ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
                story.extend([t,Spacer(1,11)])
    PDF.parent.mkdir(parents=True,exist_ok=True)
    def footer(c,doc):
        c.setFont('DejaVu',7);c.setFillColor(colors.HexColor('#607687'))
        c.drawString(56,811,'MUONES EN CENTELLADORES / LABORATORIO 5 / 28-09-2026')
        if doc.page==1:
            c.setFont('DejaVu',8)
            c.drawString(56,797,AUTHORS)
            c.setFont('DejaVu',7)
        c.drawString(56,28,'Entrega consolidada - originales preservados - 1024 muestras')
        c.drawRightString(539,28,str(doc.page))
    SimpleDocTemplate(str(PDF),pagesize=(595.276,841.89),leftMargin=56,rightMargin=56,topMargin=55,bottomMargin=50,
        title='Muones en centelladores: proyecto de análisis',author=AUTHORS).build(story,onFirstPage=footer,onLaterPages=footer)
    parts=[]
    for n,(title,items) in enumerate(sections,1):
        parts.append(f'<section id="s{n}"><h2>{html.escape(title)}</h2>')
        for kind,data in items:
            if kind=='text':parts.append('<p>'+data.replace('<link href=','<a href=').replace(' color="#245b82"','').replace('</link>','</a>')+'</p>')
            elif kind=='image':
                name,height,caption=data;encoded=base64.b64encode((OUT/'figures'/name).read_bytes()).decode('ascii')
                parts.append(f'<figure><img src="data:image/png;base64,{encoded}" alt="{html.escape(caption)}"><figcaption>{html.escape(caption)}</figcaption></figure>')
            else:
                headers,rows=data;parts.append('<div class="tablewrap"><table><thead><tr>'+''.join('<th>'+html.escape(x)+'</th>' for x in headers)+'</tr></thead><tbody>')
                parts.extend('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows);parts.append('</tbody></table></div>')
        parts.append('</section>')
    nav=''.join(f'<a href="#s{i}">{label}</a>' for i,label in enumerate(['Datos','Filtros','Selección','Vida media','Validación'],1))
    document='''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Muones en centelladores: proyecto completo</title><style>
body{font:17px/1.65 system-ui,sans-serif;color:#203e54;background:#f5f7f9;margin:0}main{max-width:1030px;margin:auto;background:white;padding:30px 42px 50px}header{border-bottom:4px solid #b9792f;padding-bottom:22px}h1{font-size:37px;line-height:1.15;margin:12px 0}h2{font-size:26px;line-height:1.25}section{padding-top:24px}nav{display:flex;gap:20px;flex-wrap:wrap;padding:18px 0}a{color:#245b82}img{width:100%;height:auto}figure{margin:22px 0}figcaption{font-size:14px;color:#526878}table{width:100%;border-collapse:collapse;font-size:15px}th,td{text-align:left;padding:9px;border-bottom:1px solid #dce5eb}th{background:#e2ecf2}.tablewrap{overflow-x:auto}.subtitle{font-size:15px;color:#526878}footer{margin-top:28px;font-size:14px}@media(max-width:640px){main{padding:20px}h1{font-size:29px}body{font-size:16px}}@media print{body{background:white}main{padding:0}nav{display:none}}
</style></head><body><main><header><p class="subtitle">LABORATORIO 5 / CENTELLADORES / 28-09-2026</p><h1>Muones en centelladores</h1><p class="authors">'''+html.escape(AUTHORS)+'''</p><p>Lectura de señales, filtros, revisión humana, controles accidentales y vida media en una ventana finita.</p><p><a href="pdf/proyecto_muones.pdf">PDF de entrega, cinco páginas</a></p></header><nav>'''+nav+'</nav>'+''.join(parts)+'''<footer>Un informe autónomo: las figuras están incorporadas. Código, tablas por evento, configuración y auditoría acompañan el repositorio. Documentación: <a href="../README.md">README</a> y <a href="../docs/REPRODUCIBILIDAD.md">reproducción</a>.</footer></main></body></html>'''
    HTML.write_text(document,encoding='utf-8')
    tracked=[Path(__file__),OUT/'lifetime_fit.json',HTML,PDF]+list((OUT/'figures').glob('*.png'))
    (OUT/'report_manifest.json').write_text(json.dumps({p.relative_to(ROOT).as_posix():sha256(p) for p in tracked},indent=2),encoding='utf-8')
    print(PDF);print(HTML)


if __name__=='__main__':main()
