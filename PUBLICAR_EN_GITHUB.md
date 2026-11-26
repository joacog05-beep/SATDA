# Actualizar la aplicación SATDA que ya está publicada

No necesitás crear otro repositorio ni volver a conectar Streamlit.

## Desde GitHub web

1. Abrí tu repositorio actual.
2. Subí **todo el contenido** de esta carpeta actualizada (no el ZIP) en la raíz, usando **Add file → Upload files**. Reemplazá los archivos existentes y confirmá el commit.
3. Verificá que estén estos cuatro archivos en GitHub: `app.py`, `satda_core.py`, `requirements.txt`, `data/students_performance_dataset.xlsx`.
4. Verificá que la carpeta `.streamlit` mantenga `config.toml`.
5. Abrí la URL actual de Streamlit. Si no se actualiza, usá **Manage app → Reboot app**.
6. Ingresá con `usuario / usuario` y comprobá que el panel muestre 2.343 registros y la búsqueda de `1817`.

## Desde VS Code con Git

Si ya tenés el repositorio clonado, copiá allí el contenido de este paquete y ejecutá:

```powershell
git add -A
git status
git commit -m "SATDA: mejora de UX y dataset academico"
git push origin main
```

**Atención:** Git oculta por defecto todos los `.xlsx`; se agregó la excepción para `data/students_performance_dataset.xlsx`. En `git status` debe figurar ese archivo antes del commit. No incluyas otros archivos de alumnos.

## Qué deberías ver

- Sin avisos repetidos de «Datos ficticios».
- Distribución de inasistencias legible con etiqueta «Sin dato».
- Histograma por rangos de probabilidad y sin zoom accidental.
- Texto y leyendas más oscuros.
- Selector de métricas con botones azules.
- «Acerca del sistema» con enfoque de propuesta de valor.
- «Fuente de información» con la base del TP y opción de importar `.xlsx` o `.csv`.

Si Streamlit muestra un error, consultá **Manage app → Logs** y revisá que se hayan subido todos los archivos del paquete, no solo `app.py`.
