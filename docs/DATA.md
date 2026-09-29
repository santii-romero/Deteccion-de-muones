# Datos y procedencia

Solo registros de 1024 muestras, con tiempos en ns y CH1/CH2/CH3 en mV. La ventana exportada es 0–1698,340 ns; paso aproximado 1,660 ns. El eje compartido no certifica alineación temporal entre canales. Los retardos se obtienen de las muestras de los pulsos; `ts` representa reloj de adquisición, no retardo ni tiempo vivo.

| Corrida anterior | Archivos | Eventos |
| --- | ---: | ---: |
| 20260903_152154 | 53 | 5019 |
| 20260903_184041 | 2 | 156 |
| 20260904_134314 | 459 | 64038 |
| 20260907_140421 | 575 | 85843 |
| 20260909_142637 | 284 | 37624 |
| Total previo | 1373 | 192680 |
| TXT independiente, sin fecha/corrida | 1 | 847 |

El TXT es una adquisición aparte según el usuario, preseleccionada por pico secundario apartado. No conserva fecha, corrida, todos los disparos ni la lógica exacta de corte. Sus 847 bloques tienen 1024 filas y cinco columnas: tiempo, tres canales y `#decaimiento`. No hubo errores estructurales ni duplicados exactos observados con las corridas previas. El ajuste final usa solo 525 de esos 847 bloques.

SHA-256 del TXT: `2907d899a5cb5c8e61e2a2eb12a0b3c203aaf411a2b00c2e00645c5eb5a5f7c9`.

En la corrida `PAblo` faltan índices 0–402, 540 y 547; no se reconstruyeron ni se atribuyó tiempo vivo a la rotación. El material de la barra entre los centelladores central e inferior es plomo, confirmado por el usuario; no están disponibles sus dimensiones ni las de los centelladores. Los 23727 registros de 300 muestras quedan fuera; el archivo comprimido de exclusiones contiene metadatos históricos y no vuelve a analizar sus señales.

`data/derived/` conserva el inventario y hashes de las cinco corridas, las decisiones por sus 192680 eventos (gzip sin pérdida), observaciones visuales, controles y las 847 decisiones del TXT. Se incluyen el catálogo automático de pulsos del TXT, decisiones humanas, observaciones y evidencia temporal tardía. Gzip se lee con `gzip.open(..., 'rt', encoding='utf-8')` y el contenido CSV original se preservó byte por byte tras descompresión.

`migration_provenance.json` documenta cada origen y hash anterior; `data/inputs_manifest.json` protege los archivos vigentes. Los originales de unos 6,7 GB permanecen en un respaldo local externo y no se distribuyen con este paquete. Para verificar el TXT se pasa su ruta a `scripts/reproduce.py --txt`; el programa no lo modifica ni registra una ruta personal en las salidas.

El detector profesional se integra desde fuentes documentales y código conservados en `data/reference/ccd/`, con su propio manifiesto y resumen. Los originales de sus imágenes y las tablas completas de validación no están disponibles, según confirmó el usuario. No se mezclan sus conteos con los retardos del laboratorio de enseñanza ni se presentan como una nueva ejecución del análisis del CCD. Ver [procedencia y denominadores](INTEGRACION_DOS_ANALISIS.md).
