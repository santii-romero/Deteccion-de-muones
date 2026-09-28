# Muones en centelladores

Entrega de la etapa experimental de centelladores: lectura de señales, filtros, revisión de candidatos, controles de coincidencias accidentales y estimación de vida media en una ventana finita.

**Resultado adoptado:** 525 eventos de la adquisición independiente `decaimientos.txt`, τ=**1,947766 µs**; intervalos estadísticos nominales 68 % **[1,596712;2,494230] µs**, 95 % **[1,360399;3,409982] µs**. Fondo cero, peso 1 por evento, 1024 muestras y ventana desde 120 ns hasta el final individual posterior a CH1 menos 10 ns. Cero eventos anteriores en este ajuste.

Los dos entregables son [el informe HTML autónomo](output/informe.html) y [el PDF de cinco páginas](output/pdf/proyecto_muones.pdf). Explican el montaje, los datos, las decisiones, los controles, el modelo y sus límites. Los informes parciales y las mediciones originales se conservan en un respaldo local separado; no se suben al repositorio.

## Organización

| Carpeta | Contenido |
| --- | --- |
| `src/muones/` | Lectores, filtros y modelos matemáticos |
| `scripts/` | Reproducción del ajuste, informe y auditoría |
| `config/` | Parámetros de selección y modelo vigentes |
| `data/derived/` | Evidencia congelada, decisiones por evento y controles |
| `results/` | Ajuste reproducido, tablas y figuras |
| `output/` | Un HTML y un PDF de entrega |
| `tests/` | 31 pruebas de lectura, selección y ajuste |
| `docs/` | Método, procedencia, decisiones y reproducción |

## Reproducir sin los datos grandes

Desde la raíz, con Python 3.14 (versión usada en esta entrega):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -X utf8 scripts/reproduce.py
python -m unittest discover -s tests
python -X utf8 scripts/build_report.py
python -X utf8 scripts/audit_delivery.py
```

El ajuste y el informe se reproducen con los tiempos, las ventanas y decisiones congelados incluidos en el repositorio. [Reproducibilidad](docs/REPRODUCIBILIDAD.md) explica la verificación opcional contra el TXT original y la repetición de simulaciones. [Datos](docs/DATA.md), [método](docs/METODO.md) y [decisiones](docs/DECISIONES.md) documentan el alcance científico.

No se atribuye a esta muestra una pureza medida ni una vida media libre certificada. Los intervalos están condicionados al modelo de fondo cero; aceptación temporal, calibración entre canales y material de la barra no están determinados. La etapa Skipper-CCD prevista para más adelante no se analizó en esta carpeta.

El destino de publicación de esta etapa es la carpeta `Muones/` de la rama `main` del [repositorio del proyecto](https://github.com/santii-romero/Deteccion-de-muones/tree/main). El análisis del detector profesional se conserva en la rama `identificador`; la integración y las correcciones editoriales quedan pendientes de la próxima indicación del usuario. No se asigna una licencia a mediciones o documentos de terceros sin autorización.
