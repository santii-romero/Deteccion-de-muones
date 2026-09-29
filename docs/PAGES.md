# Publicación del informe con GitHub Pages

Sitio del proyecto: https://santii-romero.github.io/Deteccion-de-muones/

GitHub Pages se configura con GitHub Actions. El flujo `.github/workflows/pages.yml`, ubicado en la raíz del repositorio, publica desde `Análisis-laboratorio-de-enseñanzas` cuando cambian el HTML, el PDF, su manifiesto o el constructor del sitio. El contenido de la entrega está directamente en la raíz de esa rama; las rutas del flujo ya no incluyen `Muones/`. Esta rama es el nombre vigente de la antigua `main`; la rama anterior `identificador` fue renombrada a `Identificador-instrumental-moderno`. Usa el entorno `github-pages` y permisos de lectura de contenido, escritura de Pages y emisión del token de identidad necesario para el despliegue.

`scripts/prepare_pages.py` genera la página de entrada desde `output/informe.html`, conserva las cuatro imágenes incorporadas y copia el PDF sin cambiar sus bytes. Solo sustituye los dos enlaces de documentación local por sus destinos en GitHub, fijados al commit desplegado mediante `--revision "$GITHUB_SHA"`. El paquete publicado tiene `index.html`, `pdf/proyecto_muones.pdf` y `.nojekyll`; los entregables originales conservan sus rutas y estructura autónoma.

Para preparar el mismo sitio localmente, desde esta carpeta:

```powershell
python -X utf8 scripts/prepare_pages.py --destination tmp/pages_site
```

El constructor verifica los hashes vigentes y que la copia web solo cambie esos enlaces. Usa exclusivamente la biblioteca estándar de Python y no regenera el ajuste, las simulaciones, las figuras ni el PDF. El sitio se revisa después de que GitHub termine el despliegue.

Se puede consultar la ejecución en [Actions](https://github.com/santii-romero/Deteccion-de-muones/actions) y la configuración en [Settings → Pages](https://github.com/santii-romero/Deteccion-de-muones/settings/pages). La rama `Identificador-instrumental-moderno` conserva su contenido.

El procedimiento sigue la [documentación oficial de publicación con workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
