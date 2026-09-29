"""Read event boundaries explicitly. Never concatenate or silently drop bad rows."""
from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import re
import io
import numpy as np

EVENT = re.compile(r"Event\s+#(\d+)\s+ts=(.*?)(?:\s+\[SELECTED\])?\s*$")
RUN = re.compile(r"(run_\d{8}_\d{6})_idx(\d+)")


@dataclass
class Event:
    source: str
    run: str
    file_index: int
    ordinal: int
    event_id: int
    timestamp: str
    line: int
    data: np.ndarray
    errors: list = field(default_factory=list)
    byte_offset: int = 0
    byte_length: int = 0

    @property
    def uid(self):
        return f"{self.source}::block{self.ordinal}::event{self.event_id}"


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_events_slow(path, root):
    path, root = Path(path), Path(root)
    source = path.relative_to(root).as_posix()
    match = RUN.search(path.name)
    run = match[1] if match else path.stem
    file_index = int(match[2]) if match else -1
    header = None
    rows, errors = [], []
    ordinal = 0
    unit_ok = False

    def build():
        a = np.asarray(rows, dtype=np.float64).reshape(-1, 4)
        flags = list(errors)
        if not unit_ok:
            flags.append('missing_or_unrecognized_units')
        if not len(a):
            flags.append('empty_event')
        elif not np.isfinite(a).all():
            flags.append('nonfinite_values')
        elif np.any(np.diff(a[:, 0]) <= 0):
            flags.append('nonmonotonic_time')
        return Event(source, run, file_index, ordinal, int(header[1]),
                     header[2].strip(), start, a, flags)

    with path.open(encoding='utf-8-sig') as stream:
        for number, raw in enumerate(stream, 1):
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('Event'):
                if header is not None:
                    yield build()
                header = EVENT.fullmatch(line)
                if header is None:
                    raise ValueError(f'{source}:{number}: malformed event header: {line}')
                ordinal += 1
                start = number
                rows, errors, unit_ok = [], [], False
            elif line.startswith(('t[', 'tiempo[')):
                unit_ok = line.split() in [
                    ['t[ns]', 'u1[mV]', 'u2[mV]', 'u3[mV]'],
                    ['tiempo[ns]', 'u1[mV]', 'u2[mV]', 'u3[mV]']]
            else:
                if header is None:
                    raise ValueError(f'{source}:{number}: row outside event')
                try:
                    values = [float(x) for x in line.split()]
                    if len(values) != 4:
                        raise ValueError('expected 4 columns')
                    rows.append(values)
                except ValueError:
                    errors.append(f'malformed_row_line_{number}')
        if header is not None:
            yield build()


def parse_block(block, source, run, file_index, ordinal, line, offset):
    """Strict 4-column parser; malformed rows are flagged, never silently accepted."""
    head, units, payload = block.split(b'\n', 2)
    header = EVENT.fullmatch(head.decode('utf-8-sig').strip())
    if header is None:
        raise ValueError(f'{source}:{line}: malformed event header')
    flags = []
    if units.split() not in [[b't[ns]', b'u1[mV]', b'u2[mV]', b'u3[mV]'],
                             [b'tiempo[ns]', b'u1[mV]', b'u2[mV]', b'u3[mV]']]:
        flags.append('missing_or_unrecognized_units')
    try:
        a = np.loadtxt(io.BytesIO(payload), ndmin=2)
        if a.shape[1] != 4:
            raise ValueError('expected four columns')
    except ValueError:
        rows = []
        for j, raw in enumerate(payload.splitlines(), line+2):
            if not raw.strip():
                continue
            try:
                row = [float(x) for x in raw.split()]
                if len(row) != 4:
                    raise ValueError()
                rows.append(row)
            except ValueError:
                flags.append(f'malformed_row_line_{j}')
        a = np.asarray(rows, dtype=float).reshape(-1, 4)
    if not len(a):
        flags.append('empty_event')
    elif not np.isfinite(a).all():
        flags.append('nonfinite_values')
    elif np.any(np.diff(a[:, 0]) <= 0):
        flags.append('nonmonotonic_time')
    return Event(source, run, file_index, ordinal, int(header[1]), header[2].strip(),
                 line, a, flags, offset, len(block))


def read_events(path, root):
    """Read one file at a time, storing byte positions for exact later retrieval."""
    path, root = Path(path), Path(root)
    source = path.relative_to(root).as_posix()
    match = RUN.search(path.name)
    run, idx = (match[1], int(match[2])) if match else (path.stem, -1)
    raw = path.read_bytes()
    starts = [m.start() for m in re.finditer(rb'^Event', raw, re.MULTILINE)]
    if not starts and raw.strip() and any(not x.startswith(b'#') for x in raw.splitlines() if x.strip()):
        raise ValueError(f'{source}: nonempty file without event headers')
    if starts:
        prefix = raw[:starts[0]]
        if any(not x.lstrip().startswith(b'#') for x in prefix.splitlines() if x.strip()):
            raise ValueError(f'{source}: rows outside event')
        line = raw[:starts[0]].count(b'\n')+1
    for ordinal, (start, end) in enumerate(zip(starts, starts[1:]+[len(raw)]), 1):
        block = raw[start:end]
        yield parse_block(block, source, run, idx, ordinal, line, start)
        line += block.count(b'\n')


def read_indexed(row, root):
    """Retrieve a catalogued event without re-reading preceding events."""
    with (Path(root) / row['source']).open('rb') as stream:
        stream.seek(int(row['byte_offset']))
        block = stream.read(int(row['byte_length']))
    return parse_block(block, row['source'], row['run'], int(row['file_index']),
                       int(row['ordinal']), int(row['line']), int(row['byte_offset']))
