"""Prepare the existing HTML and PDF for GitHub Pages, without scientific changes."""
import argparse,hashlib,json,shutil
from pathlib import Path
from urllib.parse import quote

ROOT=Path(__file__).resolve().parents[1]
REPOSITORY='https://github.com/santii-romero/Deteccion-de-muones'
DOCUMENTS=('REPRODUCIBILIDAD.md','INTEGRACION_DOS_ANALISIS.md')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination',default='tmp/pages_site')
    parser.add_argument('--revision',default='Análisis-laboratorio-de-enseñanzas',help='Published commit or branch used for documentation links')
    args=parser.parse_args()
    destination=Path(args.destination).resolve()
    assert destination.is_relative_to(Path.cwd().resolve()) and destination!=Path.cwd().resolve()
    html_path=ROOT/'output/informe.html';pdf_path=ROOT/'output/pdf/proyecto_muones.pdf'
    manifest=json.loads((ROOT/'results/report_manifest.json').read_text(encoding='utf-8'))
    assert digest(html_path)==manifest['output/informe.html']
    assert digest(pdf_path)==manifest['output/pdf/proyecto_muones.pdf']
    source=html_path.read_bytes().decode('utf-8');public=source
    revision=quote(args.revision,safe='')
    for name in DOCUMENTS:
        local='href="../docs/'+name+'"'
        remote='href="'+REPOSITORY+'/blob/'+revision+'/Muones/docs/'+name+'"'
        assert source.count(local)==1
        public=public.replace(local,remote)
    assert '../docs/' not in public and 'href="pdf/proyecto_muones.pdf"' in public
    assert public.count('data:image/png;base64,')==4
    # The two documentation links are the only changes in the web copy.
    restored=public
    for name in DOCUMENTS:
        restored=restored.replace('href="'+REPOSITORY+'/blob/'+revision+'/Muones/docs/'+name+'"','href="../docs/'+name+'"')
    assert restored==source
    expected={'index.html','pdf/proyecto_muones.pdf','.nojekyll'}
    if destination.exists():
        existing={p.relative_to(destination).as_posix() for p in destination.rglob('*') if p.is_file()}
        assert existing<=expected,sorted(existing-expected)
    (destination/'pdf').mkdir(parents=True,exist_ok=True)
    (destination/'index.html').write_bytes(public.encode('utf-8'))
    shutil.copy2(pdf_path,destination/'pdf/proyecto_muones.pdf')
    (destination/'.nojekyll').write_bytes(b'')
    assert digest(destination/'pdf/proyecto_muones.pdf')==digest(pdf_path)
    actual={p.relative_to(destination).as_posix() for p in destination.rglob('*') if p.is_file()}
    assert actual==expected
    print(json.dumps({'status':'prepared','site_files':sorted(actual),'pdf_byte_identical':True,
        'html_changes':'two documentation links point to the repository',
        'html_source_sha256':digest(html_path),'public_html_sha256':digest(destination/'index.html')},indent=2))

if __name__=='__main__':main()
