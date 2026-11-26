# SATDA — Sistema de Alerta Temprana de Deserción Académica

**Versión 1.1 · Plataforma Streamlit para docentes, tutores y directivos.**

SATDA detecta estudiantes con probabilidad estimada de **calificación crítica (D/F)** a partir de `Absences`, `Tutoring` y `ParentalSupport`. La predicción de D/F no equivale a una predicción directa de abandono. Las acciones recomendadas necesitan interpretación institucional.

## Contenido

- **Inicio de sesión de presentación:** usuario `usuario`, contraseña `usuario`.
- **Resumen institucional:** tablero de alertas, distribución de inasistencias y probabilidades, búsqueda y exportación.
- **Ficha individual:** ID, calificación registrada, asistencia, tutorías, apoyo familiar, puntuación y orientaciones.
- **Simulador:** escenarios hipotéticos sin modificar los registros originales.
- **Modelo y métricas:** comparativas de los cinco algoritmos, matriz de confusión, resultados históricos del trabajo y nueva evaluación sobre la base actual.
- **Acerca del sistema:** propuesta de valor institucional y posibles aplicaciones de SATDA.

## Base de datos del trabajo práctico (incluida)

Se incluye `data/students_performance_dataset.xlsx`, la base académica aportada para esta iteración. Contiene **2.343 registros** sin nombres de estudiantes, con `StudentID` de **cuatro cifras**. La aplicación la utiliza automáticamente al iniciar, sin exigir una importación manual.

La base tiene categorías: `Tutoring` (`yes`/`no`) y `ParentalSupport` (`Low`, `Moderate`, `High`, `Very High`). Se transforman para su visualización y se tratan como **categóricas mediante OneHotEncoder** en la predicción; las ausencias se escalan y los valores faltantes se imputan.

**Importante:** «Resultados del proyecto» muestra las métricas históricas del notebook del grupo. «Dataset actual» vuelve a entrenar y evaluar los modelos a partir del archivo incluido (o de uno importado). Pueden diferir por versiones del dataset o detalles de procesamiento; no deben presentarse como idénticos. En la ficha, los puntajes históricos se calculan con un modelo ajustado al conjunto completo, y no son métricas independientes fuera de muestra.

La base no contiene nombres ni apellidos. En la ficha se indica «Estudiante 1817», por ejemplo, conservando el StudentID real.

## Ejecutar en VS Code (Windows)

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Acceder a http://localhost:8501. También podés usar `INICIAR_SATDA.bat`.

## Publicar en Streamlit Community Cloud

1. Actualizá el repositorio de GitHub subiendo **los archivos y carpetas de este paquete en la raíz**, no el ZIP: `app.py`, `satda_core.py`, `requirements.txt`, `data/`, `assets/`, `.streamlit/`, `.github/`, etc.
2. Comprobá especialmente que `data/students_performance_dataset.xlsx` aparece en el repositorio: si no se sube, se utilizará la cohorte de respaldo en lugar de la base del TP.
3. Conservá la aplicación ya creada en Streamlit Cloud. La actualización de la rama principal generalmente provoca un nuevo despliegue; en caso necesario, entrá a **Manage app → Reboot app**.
4. Abrí la URL y comprobá que el tablero muestre **2.343 estudiantes** y permita buscar StudentID `1817`.

El archivo `.gitignore` mantiene excluidos los demás Excel y CSV, pero incluye expresamente la base académica suministrada en `data/`.

### Opciones para cargar archivos

En la barra lateral, **Fuente de información → Cargar archivo** permite importar `.xlsx`/`.csv` con `Absences`, `Tutoring`, `ParentalSupport` y `GradeClass`; `StudentID` y nombres son opcionales. La app procesa los archivos en la memoria de la sesión, sin escribir el contenido en el repositorio. Al ser una app pública con credenciales compartidas, **solo debe utilizarse con bases sintéticas, anónimas o debidamente autorizadas**; para usar datos identificables hacen falta autenticación y controles institucionales.

Para deshabilitar la importación en cualquier entorno, establecer `SATDA_ENABLE_DATA_UPLOAD=0`.

## Pruebas

```bash
python -m pip install pytest
python -m pytest -q
```

## Estructura

```text
app.py
satda_core.py
requirements.txt
README.md
PUBLICAR_EN_GITHUB.md
INICIAR_SATDA.bat
assets/satda_logo.svg
data/students_performance_dataset.xlsx
.streamlit/config.toml
.github/workflows/tests.yml
tests/test_core.py
```

## Uso responsable

Las alertas y las simulaciones ayudan a orientar decisiones humanas, no demuestran que cambiar una variable *cause* una mejora en el rendimiento. Es conveniente validar desempeño, sesgos, umbrales e impacto institucional antes de un despliegue operativo.
