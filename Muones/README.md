# Muones: análisis temporal y espacial

Entrega conjunta de dos etapas: señales de centelladores de un laboratorio de enseñanza y reconstrucción y clasificación de trazas de un detector profesional Skipper-CCD. Integra los resultados y el código documentados en las ramas `main` e `identificador`, sin combinar sus muestras ni modificar el ajuste temporal.

**Resultado temporal adoptado:** 525 eventos de la adquisición independiente, τ=**1,947766 µs**; intervalos estadísticos nominales 68 % **[1,596712;2,494230] µs**, 95 % **[1,360399;3,409982] µs**. Fondo cero, peso 1 por evento, 1024 muestras y ventana desde 120 ns hasta el final individual posterior a CH1 menos 10 ns. Cero eventos anteriores en este ajuste.

**Resultado espacial documentado:** resumen de 30 imágenes con 6251 trazas, 1316 etiquetadas como muones; mAP50 de muones de 0,90 en la validación conservada del clasificador. Las métricas comparan con reglas automáticas, no con identidad física certificada. No están disponibles los originales del CCD para repetir su análisis; la procedencia y los denominadores se explican en [la integración](docs/INTEGRACION_DOS_ANALISIS.md).

Los dos entregables son [el informe HTML autónomo](output/informe.html) y [el PDF académico de cinco páginas](output/pdf/proyecto_muones.pdf), generado en LaTeX. El [fuente portable](output/latex/proyecto_muones.tex) y sus figuras se pueden compilar en Overleaf. Integrantes: **Theo Del Compare y Santiago Romero**. Los informes parciales y las mediciones originales se conservan fuera del paquete y no se suben al repositorio.

## Organización

| Carpeta | Contenido |
| --- | --- |
| `src/muones/` | Lectores, filtros y modelos matemáticos |
| `scripts/` | Reproducción del ajuste, informe y auditoría |
| `config/` | Parámetros de selección y modelo vigentes |
| `data/derived/` | Evidencia congelada, decisiones por evento y controles |
| `data/reference/ccd/` | Fuentes del análisis previo del detector, conservadas con hashes |
| `results/` | Ajuste reproducido, tablas y figuras |
| `output/` | Un HTML, un PDF de entrega y su fuente LaTeX |
| `tests/` | 31 pruebas de lectura, selección y ajuste |
| `docs/` | Método, procedencia, decisiones y reproducción |

## Reproducir sin los datos grandes

Desde la raíz, con Python 3.14 (versión usada en esta entrega) y una distribución LaTeX con `pdflatex` (MiKTeX o TeX Live):

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

No se atribuye a las selecciones una pureza medida ni una vida media libre certificada. Los intervalos están condicionados al modelo de fondo cero; la aceptación temporal y la calibración entre canales no están determinadas. La barra es de plomo, confirmado por el usuario, y sus dimensiones no están disponibles. El análisis del Skipper-CCD anterior se integra con su alcance documental, sin afirmar una nueva ejecución sobre datos ausentes.

El destino de publicación de esta entrega conjunta es la carpeta `Muones/` de la rama `main` del [repositorio del proyecto](https://github.com/santii-romero/Deteccion-de-muones/tree/main). El código original del detector profesional se conserva en la rama `identificador`; su análisis documentado está integrado en ambos entregables con las preferencias editoriales aplicadas. No se asigna una licencia a mediciones o documentos de terceros sin autorización.
