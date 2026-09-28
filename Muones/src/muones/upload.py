"""Strict parser of the independent five-column acquisition. Times ns; voltages mV."""
from pathlib import Path
import numpy as np
SRC=Path("Datos/Med_con_Decaimientos/decaimientos.txt")

def blocks(path=SRC):
    with Path(path).open(encoding='utf-8-sig') as f:
        header=next(f).strip().split('\t')
        expected=['tiempo [ns]','canal 1 [mV]','canal 2 [mV]','canal 3 [mV]','#decaimiento']
        if header!=expected:raise ValueError(f'Unexpected header: {header}')
        rows=[];key=None;start=2
        for line,raw in enumerate(f,2):
            fields=raw.strip().split('\t')
            if len(fields)!=5:raise ValueError(f'Line {line}: {len(fields)} columns')
            try:values=[float(x) for x in fields[:4]];current=int(fields[4])
            except ValueError as e:raise ValueError(f'Line {line}: nonnumeric field') from e
            if not np.isfinite(values).all():raise ValueError(f'Line {line}: nonfinite value')
            if current!=key and key is not None:
                yield key,start,line-1,np.array(rows,dtype=float)
                rows=[];start=line
            key=current;rows.append(values)
        if key is not None:yield key,start,line,np.array(rows,dtype=float)
