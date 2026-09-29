# Método de análisis

La configuración real comunicada por el usuario tiene disparo en CH1 superior, detección adicional exigida en CH2, sin exigir CH3, y una barra de plomo entre CH2/CH3. El material está confirmado; las dimensiones no están disponibles. Las notas, guía y código de referencia no sustituyen esta información. No se conoce la condición exacta del rechazo de positivos aplicado durante adquisición y no se vuelve a aplicar un veto arbitrario.

## Lectura y filtros

`muones.io` separa registros `Event #`; `muones.upload.blocks` lee el TXT independiente. Se verifican unidades, columnas, longitudes, finitud, monotonicidad y duplicados. No se suavizan ni cambian las muestras. El filtro congelado `config/filters_v1_1024.json` estima base por mediana y ruido mediante 1,4826 MAD fuera de 160–300 ns, con un recorte para estimar la base, sin borrar pulsos.

| Criterio | Regla v1 |
| --- | --- |
| Semilla | Altura ≥max(45 mV,3σ); prominencia ≥max(30 mV,2,5σ); separación ≥5 ns |
| Amplitud aceptada | ≥max(80 mV,4,5σ), respecto de la base |
| Ancho | 3–35 ns a mitad de altura; ≥2 muestras |
| Coincidencia inicial | CH1/CH2 en 170–270 ns, separación ≤15 ns |
| Ruido duro | σ>60 mV; base saturada>2 %; impulso aislado; oscilación bipolar |
| Marcas ambiguas | Saturación local, deriva, lóbulo positivo grande, ancho excesivo o borde |

σ es una escala robusta de ruido, no significancia gaussiana. El catálogo conserva todas las semillas y sus motivos; fluctuaciones que no alcanzan el umbral no están catalogadas. El flag morfológico original de borde usa 35 ns; la ventana final de vida media usa 10 ns tras revisión y decisión humana, conservando ese flag histórico.

## Selección final y ajuste

Se requiere coincidencia inicial aceptada y CH3 inicial no detectado sobre umbral. CH1 tardío no veta ni entra en la estimación del tiempo secundario. Se preservan los tiempos asignados antes de imponer la ventana; las aprobaciones humanas aceptan calidad pero no inventan tiempos.

Los 525 retardos se ajustan individualmente con una exponencial sola, fondo cero y peso 1. Para cada evento `120 ns ≤t≤U_i`, `U_i=t_final_i−t_CH1_inicial_i−10 ns`. La densidad es `exp(−t/τ) / {τ[exp(−120 ns/τ)−exp(−U_i/τ)]}`. Se normaliza en la ventana observable de cada registro, no hasta infinito. La media truncada de los retardos no estima directamente τ. El histograma es ilustrativo.

`muones.finite_window.fit` resuelve el score, comprueba un optimizador independiente y obtiene intervalos nominales de perfil por cambios de log-verosimilitud. El límite de tasa cero corresponde a τ infinita y se conserva cuando procede. La interpretación depende de aceptación constante en la ventana y fondo cero, solicitado por el usuario; no es pureza experimental medida.

## Controles y validación

Las cinco corridas previas aportaron controles en ventanas pareadas de 120–170 ns, limitadas por los bordes: tres secundarios anteriores y 15 posteriores en 87915 padres elegibles. El tramo anterior corto no caracteriza toda la cola y no calibra el fondo del TXT preseleccionado. No se trasladan como una resta al ajuste final; el control triple ponderado es descriptivo.

Se revisaron 197 candidatos previos (195 secundarios distinguibles, dos dudosos) y los 88 pendientes de calidad del TXT. Revisión no ciega, sin certificación de identidad física. Las inyecciones y sensibilidad examinaron recuperación del algoritmo en fondos reales, no eficiencia universal. Se conservan resúmenes de 7128 inyecciones CH2 de la etapa de filtros y 7776 ensayos pareados posteriores.

Las 31 pruebas cubren lectura, alcance, selección, pesos y likelihood. Para los 525 se realizaron 3000 simulaciones condicionales, semilla 2026092811: cobertura nominal 68/95 % 67,77/94,87 %, KS con reajuste p=0,786. No son nuevas mediciones ni simulación de electrónica. Pendientes científicos: aceptación temporal, calibración entre canales, afterpulses y captura posible en los materiales. No se midió flujo absoluto ni eficiencia de CH2 con una muestra que ya exige respuesta de ese canal.

## Integración con el análisis espacial

La incorporación del Skipper-CCD está documentada en `INTEGRACION_DOS_ANALISIS.md`. Se verifican fuentes y resúmenes conservados del detector; no hay imágenes originales disponibles para repetir calibración, entrenamiento o evaluación. La adquisición temporal y las imágenes del CCD no tienen un estimando común que permita sumar sus eventos para vida media.
