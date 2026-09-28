"""User-mandated population for every active analysis (27 September 2026)."""
from pathlib import Path, PurePosixPath
import json

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / 'results/active_1024'
DATA = ROOT / 'Datos/Med_con_Decaimientos'
CONFIG = ROOT / 'config/filters_v1_1024.json'


def in_scope(source, n_samples):
    parts = PurePosixPath(str(source).replace('\\', '/')).parts
    return (parts[:2] == ('Datos', 'Med_con_Decaimientos')
            and '..' not in parts and int(n_samples) == 1024)


def require_event(event):
    if not in_scope(event.source, len(event.data)):
        raise ValueError('Outside user-authorized analysis scope: ' + event.uid)


def config():
    cfg = json.loads(CONFIG.read_text(encoding='utf-8'))
    assert cfg['expected_samples'] == [1024]
    return cfg


def read_indexed(row, root=ROOT):
    from .io import read_indexed as read
    if not in_scope(row['source'], row.get('n_samples', 1024)):
        raise ValueError('Outside user-authorized analysis scope: ' + row['source'])
    event = read(row, root)
    require_event(event)
    return event
