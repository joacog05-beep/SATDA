# Publicar SATDA en GitHub + Streamlit Community Cloud

## Opción A: desde VS Code (recomendada)

1. Extraé `SATDA_GitHub_StreamlitCloud_Listo.zip` en una carpeta vacía, por ejemplo `Documentos\satda-demo`. El archivo `app.py` debe quedar en la raíz de esa carpeta.
2. Ingresá a https://github.com/new y creá un repositorio **público** llamado `satda-demo`. Dejalo **vacío**: no marques `Add a README file`, `.gitignore` ni licencia porque ya los incluimos.
3. Abrí la carpeta en VS Code y luego **Terminal → Nueva terminal**.
4. Corré estos comandos en PowerShell, uno por uno, reemplazando `TU_USUARIO` por tu nombre de GitHub:

```powershell
git init
git branch -M main
git add .
git commit -m "Publicar prototipo SATDA"
git remote add origin https://github.com/TU_USUARIO/satda-demo.git
git push -u origin main
```

Si Git te pide configurar tu identidad, hacelo con `git config --global user.name "Tu nombre"` y `git config --global user.email "tu-correo-de-GitHub"`. Si no encuentra `git`, instalá Git for Windows desde https://git-scm.com/downloads/win y reiniciá VS Code.

5. Abrí https://share.streamlit.io e iniciá sesión con GitHub. Autorizá a Streamlit a acceder al repositorio.
6. Elegí **Create app → Yup, I have an app**. Completá:
   - **Repository:** `TU_USUARIO/satda-demo`
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - **App URL:** un subdominio libre (ej. `satda-demo-fiuba`).
   - **Advanced settings → Python:** `3.11`
7. Pulsá **Deploy**. El enlace queda en la forma `https://SUBDOMINIO.streamlit.app`.
8. Abrí ese enlace desde un celular o ventana de incógnito para comprobar que se puede compartir.

## Opción B: sin usar comandos de Git

Creá `satda-demo` en GitHub e ingresá al repositorio. Elegí **Add file → Upload files**. Arrastrá los archivos y carpetas de la carpeta extraída (incluidas `assets`, `.streamlit`, `.github` y `tests`; las carpetas que empiezan con punto pueden estar ocultas por Windows). Confirmá con **Commit changes**. Asegurate de que `app.py`, `satda_core.py` y `requirements.txt` estén en la raíz. Después seguí el paso 5 anterior.

## Si hay un error en Streamlit

- **ModuleNotFoundError:** asegurate de que `requirements.txt` esté junto a `app.py` y de que el archivo `satda_core.py` se haya subido.
- **No encuentra logo:** comprobá `assets/satda_logo.svg` (respetar mayúsculas/minúsculas en Linux).
- **No aparece el repositorio:** verificá la conexión/autorización de Streamlit a GitHub y que tenés permiso de administración sobre el repositorio.
- **Dependencias incompatibles:** desplegá con Python 3.11.
- **La app se duerme después de un tiempo:** el hosting gratuito puede suspender aplicaciones inactivas; abrí la URL para reactivarla.

## Credenciales de la demostración

- Usuario: `usuario`
- Contraseña: `usuario`

Estas credenciales **no protegen datos reales**. Este repositorio está configurado para mostrar solo estudiantes ficticios e impide cargas de datasets en la app pública. No subas archivos con información académica identificable, ni las bases originales de estudiantes, ni contraseñas o tokens.

## Actualizaciones posteriores

Editá el proyecto en VS Code y ejecutá:

```powershell
git add .
git commit -m "Actualizar SATDA"
git push
```

Streamlit debería detectar los cambios y actualizar la app. Los tests se ejecutan mediante GitHub Actions.

## Enlaces oficiales

- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies
- https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app
