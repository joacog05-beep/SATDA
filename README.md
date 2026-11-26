# SATDA · Sistema de Alerta Temprana de Deserción Académica

**Prototipo académico interactivo para docentes y directivos.** Proyecto de Introducción a la Ciencia de Datos (Grupo 12, FIUBA). Desarrollado con Python, Streamlit, Plotly y scikit-learn.

> **Importante:** el prototipo predice **riesgo de obtener calificaciones D/F**; no estima directamente probabilidades de deserción. La versión pública utiliza alumnos ficticios y un modelo entrenado sobre datos sintéticos. Las métricas del proyecto original aparecen separadas de los indicadores simulados.

## 🚀 Desplegar en Streamlit Community Cloud

1. Creá un repositorio nuevo en GitHub, por ejemplo `satda-demo`, y subí **los archivos de esta carpeta en la raíz del repositorio**. `app.py` y `requirements.txt` tienen que estar al mismo nivel. No subas el archivo ZIP ni datos de estudiantes.
2. Abrí [share.streamlit.io](https://share.streamlit.io), iniciá sesión con GitHub y autorizá el acceso al repositorio.
3. Seleccioná **Create app → Yup, I have an app** y completá:
   - **Repository:** `TU_USUARIO/satda-demo`
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - **App URL (opcional):** `satda-demo` o `satda-grupo12` si está libre.
4. En **Advanced settings**, seleccioná **Python 3.11**. No hacen falta secretos de Streamlit para este modo.
5. Pulsá **Deploy** y compartí el enlace resultante `https://TU_SUBDOMINIO.streamlit.app`.

**GitHub conserva el código. Streamlit Community Cloud ejecuta Python y publica la app.** Los cambios que hagas en la rama principal se volverán a desplegar.

## 🔑 Acceso demostrativo

- Usuario: `usuario`
- Contraseña: `usuario`

**No es autenticación real ni segura.** Es un recurso visual para una demostración. La versión pública trae la importación de datasets **deshabilitada por defecto**, precisamente para no recibir registros de estudiantes.

## 🖥️ Uso local en Windows (VS Code)

Desde la terminal de la carpeta del proyecto:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Como alternativa, doble clic en `INICIAR_SATDA.bat`. Abrí [http://localhost:8501](http://localhost:8501).

### Cargar un dataset de forma local (modo avanzado)

La versión pública no admite cargas. Para habilitar el módulo de importación **solo en tu computadora y con datos autorizados**:

```powershell
$env:SATDA_ENABLE_DATA_UPLOAD="1"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

En otra consola o en un nuevo inicio, la opción vuelve a estar deshabilitada. **No configures esta variable en Streamlit Community Cloud.** El módulo acepta `.csv` o `.xlsx` con `Absences`, `Tutoring`, `ParentalSupport`, `GradeClass` y, opcionalmente, `StudentID` y nombres. Para estudios reales se requiere consentimiento, seguridad institucional, auditoría y validación externa, que este prototipo no ofrece.

## 📁 Estructura

```text
app.py
satda_core.py
requirements.txt
README.md
.gitignore
.streamlit/config.toml
assets/satda_logo.svg
datos_ficticios_ejemplo.csv
INICIAR_SATDA.bat
tests/test_core.py
.github/workflows/tests.yml
```

- `app.py`: pantallas, acceso, dashboard, búsqueda, fichas, simulaciones y gráficos.
- `satda_core.py`: datos ficticios, validación de datasets, ML, métricas y recomendaciones.
- `requirements.txt`: dependencias instaladas automáticamente por la nube.
- `.streamlit/config.toml`: colores, tipografías y configuración de la app.
- `.github/workflows/tests.yml`: verificaciones automáticas de la lógica en GitHub Actions.

## 🧪 Pruebas

Instalá opcionalmente `pytest` y ejecutá:

```bash
python -m pip install pytest
python -m pytest -q
```

## 🔒 Alcance y privacidad

- Los 360 estudiantes del modo demostración son **ficticios**, y las probabilidades ilustran el funcionamiento de un modelo entrenado con datos sintéticos.
- Las métricas históricas corresponden al experimento original; no deben confundirse con resultados de la cohorte sintética.
- El acceso `usuario/usuario` **no protege información**. Si se implementa en una institución, debe reemplazarse por acceso robusto, perfiles, permisos, auditoría y cumplimiento de la normativa de datos.
- Las recomendaciones sirven como apoyo para profesionales y **no constituyen decisiones automáticas** ni garantías de resultados.
- No hay backend institucional, usuarios persistentes ni base de datos conectada.

**Desarrollado con fines académicos y de exposición.**
