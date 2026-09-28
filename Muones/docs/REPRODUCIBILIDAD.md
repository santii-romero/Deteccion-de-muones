# Reproducción y auditoría

Dependencias exactas en `requirements.txt`. Entorno comprobado: Python 3.14 en Windows. Las rutas se resuelven desde cada script, sin depender de una carpeta personal. La reproducción del ajuste usa decisiones y tiempos congelados; las decisiones humanas no se regeneran automáticamente.

```powershell
python -X utf8 scripts/reproduce.py
python -m unittest discover -s tests
python -X utf8 scripts/build_report.py
python -X utf8 scripts/audit_delivery.py
```

La auditoría comprueba hashes de entradas, 847 identidades, 525 eventos, pesos unitarios, fondo cero, ausencia de corridas previas, normalización individual y coincidencia con el ajuste adoptado. El paquete incluye todos los estados, no solo los aceptados. Las tablas comprimidas preservan decisiones de las corridas previas y metadatos de exclusión por 300 muestras.

## Verificar el original y repetir simulaciones

```powershell
python -X utf8 scripts/reproduce.py --txt "RUTA_AL_RESPALDO/Datos/Med_con_Decaimientos/decaimientos.txt" --simulate
```

La opción `--txt` verifica el SHA-256, los 847 bloques, eje temporal, clasificación automática de todas las semillas y los 525 tiempos contra las muestras originales. No modifica el TXT ni suma eventos anteriores. La opción `--simulate` repite las 3000 realizaciones condicionales con la semilla registrada y comprueba que coincide la validación conservada. Sin esa opción se reutiliza la validación exacta existente; no se presenta como una ejecución nueva.

`build_report.py` genera el único HTML y PDF (máximo cinco páginas). Las figuras, la síntesis y las referencias provienen de las mismas entradas. El HTML lleva las imágenes incorporadas y no necesita internet para mostrar el informe; los enlaces bibliográficos sí son externos.

Para comprobar cambios de presentación, renderizar las páginas del PDF con PyMuPDF/Poppler y revisar visualmente textos, tablas y figuras. La auditoría estructural comprueba cantidad de páginas, texto, enlaces locales y ausencia de informes duplicados; no reemplaza esa revisión visual. `results/visual_qa.json` documenta la inspección realizada en la entrega actual.

El respaldo conserva el árbol previo íntegro, incluyendo informes y archivos fuente de referencia. Un manifiesto local verifica su contenido antes y después de ordenar. La ubicación personal se guarda solo en `.local_backup.json`, ignorado por Git; no es dependencia del repositorio.
