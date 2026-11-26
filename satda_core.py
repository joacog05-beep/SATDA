"""Lógica de SATDA: modos DEMO y DATASET REAL.

Reproduce las tres variables, el objetivo D/F, 80/20, random_state=42 y
Regresión Logística del notebook suministrado. NO predice deserción.
"""
from __future__ import annotations

from io import BytesIO
from dataclasses import dataclass
import math
import re
import unicodedata
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import AdaBoostClassifier, GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = ("Absences", "Tutoring", "ParentalSupport")
TEST_SIZE = 0.20
SEED = 42
MAX_ABSENCES = 30
THRESHOLD_RED = 0.80
THRESHOLD_YELLOW = 0.50

NAVY = "#102E57"
PURPLE = "#7454D6"
CYAN = "#35B9D8"
RED = "#EA5A72"
YELLOW = "#EDA940"
GREEN = "#23B3A7"

ALERT_ORDER = ["Alerta roja", "Alerta amarilla", "Sin alerta"]
ALERT_COLORS = {"Alerta roja": RED, "Alerta amarilla": YELLOW, "Sin alerta": GREEN}

# Valores REALES transcritos de la salida del notebook del equipo.
PROJECT_METRICS = pd.DataFrame([
    ["KNN", .8612, .9436, .8091, .8712, .8102, 18, 71],
    ["Gradient Boosting", .8580, .9624, .7995, .8734, .8102, 12, 77],
    ["AdaBoost", .8501, .9530, .8042, .8723, .8102, 15, 74],
    ["Random Forest", .8494, .8997, .8130, .8542, .7910, 32, 66],
    ["Regresión Logística", .8385, .9436, .8179, .8763, .8188, 18, 67],
], columns=["Modelo", "AUC-ROC", "Recall", "Precisión", "F1-Score", "Accuracy", "FN", "FP"])
PROJECT_EVALUATION_N = 469
PROJECT_RL_CONFUSION = np.array([[83, 67], [18, 301]])  # VN, FP / FN, VP


def classify_risk(p: float) -> str:
    """Corresponde a los umbrales del notebook: rojo si p>0.80, amarillo si p>=0.50."""
    if float(p) > THRESHOLD_RED:
        return "Alerta roja"
    if float(p) >= THRESHOLD_YELLOW:
        return "Alerta amarilla"
    return "Sin alerta"


def _key(text: Any) -> str:
    s = unicodedata.normalize("NFKD", str(text))
    return re.sub(r"[^a-z0-9]", "", "".join(x for x in s if not unicodedata.combining(x)).lower())


def _grade(value: Any) -> tuple[str, int] | None:
    """GradeClass: A=0, B=1, C=2, D=3, F=4, clase positiva D/F."""
    if pd.isna(value):
        return None
    txt = str(value).strip().upper()
    codes = {"A": 0, "B": 1, "C": 2, "D": 3, "F": 4}
    if txt in codes:
        n = codes[txt]
    else:
        try:
            raw = float(txt.replace(",", "."))
        except (ValueError, TypeError):
            return None
        if not math.isfinite(raw) or raw not in (0, 1, 2, 3, 4):
            return None
        n = int(raw)
    return ("A", "B", "C", "D", "F")[n], int(n >= 3)


def _find_col(columns, *aliases):
    lookup = {_key(c): c for c in columns}
    for alias in aliases:
        if _key(alias) in lookup:
            return lookup[_key(alias)]
    return None


def read_uploaded_dataset(file_data: bytes, filename: str) -> pd.DataFrame:
    """Lectura sin escritura en disco. Rechaza columnas críticas ausentes e inconsistencias."""
    suffix = filename.lower().rsplit(".", 1)[-1]
    buf = BytesIO(file_data)
    if suffix == "csv":
        try:
            raw = pd.read_csv(buf, sep=None, engine="python", encoding="utf-8-sig")
        except UnicodeDecodeError:
            raw = pd.read_csv(BytesIO(file_data), sep=None, engine="python", encoding="latin-1")
    elif suffix == "xlsx":
        raw = pd.read_excel(buf, engine="openpyxl")
    else:
        raise ValueError("Formato no admitido. Subí un archivo .xlsx o .csv.")

    required = {
        "Absences": ("Absences", "Inasistencias"),
        "Tutoring": ("Tutoring", "Tutorias", "Tutorías"),
        "ParentalSupport": ("ParentalSupport", "ApoyoFamiliar"),
        "GradeClass": ("GradeClass", "Grade_Class", "ClaseNota"),
    }
    detected = {col: _find_col(raw.columns, *aliases) for col, aliases in required.items()}
    missing = [name for name, raw_col in detected.items() if raw_col is None]
    if missing:
        raise ValueError("Columnas requeridas ausentes: " + ", ".join(missing))

    df = pd.DataFrame({name: raw[source] for name, source in detected.items()})
    invalid_grades = df["GradeClass"].notna() & df["GradeClass"].map(_grade).isna()
    if invalid_grades.any():
        raise ValueError(f"GradeClass contiene {int(invalid_grades.sum())} valores inválidos. Se admiten 0 a 4 o A/B/C/D/F.")
    df["GradeParsed"] = df["GradeClass"].map(_grade)
    df = df.dropna(subset=["GradeParsed"]).copy()
    if df.empty:
        raise ValueError("No hay filas con GradeClass válida.")
    df["GradeLabel"] = df["GradeParsed"].map(lambda x: x[0])
    df["Target"] = df["GradeParsed"].map(lambda x: x[1]).astype(int)
    df = df.drop(columns=["GradeParsed", "GradeClass"])

    for name in FEATURES:
        df[name] = pd.to_numeric(df[name], errors="coerce")
    df.loc[~df["Absences"].between(0, MAX_ABSENCES), "Absences"] = np.nan
    df.loc[~df["Tutoring"].isin([0, 1]), "Tutoring"] = np.nan
    df.loc[~df["ParentalSupport"].isin([0, 1, 2, 3, 4]), "ParentalSupport"] = np.nan
    if any(df[f].notna().sum() == 0 for f in FEATURES):
        raise ValueError("Las tres variables predictoras deben tener al menos algún valor numérico válido.")

    c_id = _find_col(raw.columns, "StudentID", "StudentId", "ID", "Legajo", "IdAlumno")
    c_name = _find_col(raw.columns, "StudentName", "FullName", "NombreApellido", "NombreCompleto", "Name")
    c_first = _find_col(raw.columns, "FirstName", "Nombre")
    c_last = _find_col(raw.columns, "LastName", "Apellido")
    c_study = _find_col(raw.columns, "StudyTimeWeekly", "HorasEstudioSemanales")

    if c_id:
        ids = raw.loc[df.index, c_id].fillna("").astype(str).str.strip()
        missing_id = ids.eq("")
        # No se inventa que las referencias internas son IDs originales de la universidad.
        for idx in ids[missing_id].index:
            ids.at[idx] = f"REG-{int(idx)+1:05d}"
        df["StudentID"] = ids
    else:
        df["StudentID"] = [f"REG-{i+1:05d}" for i in range(len(df))]
    df["StudentID"] = df["StudentID"].astype(str)
    # Resolución de IDs duplicados sin eliminar estudiantes
    if df["StudentID"].duplicated().any():
        counts = df.groupby("StudentID").cumcount()
        df.loc[counts > 0, "StudentID"] += "-" + counts[counts > 0].astype(str)

    if c_name:
        names = raw.loc[df.index, c_name].fillna("").astype(str).str.strip()
    elif c_first or c_last:
        first = raw.loc[df.index, c_first].fillna("").astype(str) if c_first else pd.Series("", index=df.index)
        last = raw.loc[df.index, c_last].fillna("").astype(str) if c_last else pd.Series("", index=df.index)
        names = (first + " " + last).str.strip()
    else:
        names = pd.Series("", index=df.index)
    df["FullName"] = names.mask(names.eq(""), "Estudiante " + df["StudentID"])
    if c_study:
        df["StudyTimeWeekly"] = pd.to_numeric(raw.loc[df.index, c_study], errors="coerce")
    df = df.reset_index(drop=True)
    if len(df) < 50 or df["Target"].value_counts().min() < 10 or df["Target"].nunique() < 2:
        raise ValueError("Se necesitan al menos 50 registros y 10 casos por clase (D/F y A/B/C) para realizar la evaluación 80/20.")
    return df


def create_demo_dataset(n: int = 360) -> pd.DataFrame:
    """Alumnos inventados de forma reproducible; NO pertenece al dataset de la cátedra."""
    rng = np.random.default_rng(2026)
    first = ["Valentina", "Camila", "Sofía", "Lucía", "Martina", "Agustina", "Tomás", "Mateo", "Nicolás", "Julián", "Santiago", "Francisco", "Emilia", "Lautaro", "Micaela", "Florencia", "Alan", "Milagros", "Bruno", "Catalina"]
    last = ["García", "Fernández", "Romero", "López", "Martínez", "Sosa", "Pérez", "Álvarez", "Díaz", "González", "Ruiz", "Molina", "Castro", "Torres", "Acosta", "Suárez", "Ríos", "Vega", "Giménez", "Navarro"]
    absences = rng.integers(0, 30, n)
    tutoring = rng.binomial(1, 0.38, n)
    parental = rng.choice(np.arange(5), size=n, p=[.13, .16, .28, .26, .17])
    study_time = np.round(np.clip(rng.normal(10, 4, n), 0, 25), 1)
    # Generación DE EJEMPLO: esta ecuación NO proviene del modelo entrenado del equipo.
    logits = -1.1 + .13 * absences - .58 * tutoring - .25 * parental + rng.normal(0, .7, n)
    event_probs = 1 / (1 + np.exp(-logits))
    risky = rng.binomial(1, event_probs)
    grades = [rng.choice(["D", "F"], p=[.65, .35]) if is_risky else rng.choice(["A", "B", "C"], p=[.18, .33, .49]) for is_risky in risky]
    return pd.DataFrame({
        "StudentID": [f"SAT-{2026}-{i+1:04d}" for i in range(n)],
        "FullName": [f"{rng.choice(first)} {rng.choice(last)}" for _ in range(n)],
        "Absences": absences.astype(float),
        "Tutoring": tutoring.astype(float),
        "ParentalSupport": parental.astype(float),
        "StudyTimeWeekly": study_time,
        "GradeLabel": grades,
        "Target": risky.astype(int),
    })


def _build_pipeline(estimator):
    prep = ColumnTransformer([("numeric", Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
    ]), list(FEATURES))])
    return Pipeline([("prep", prep), ("model", estimator)])


@dataclass
class ModelResult:
    records: pd.DataFrame
    model: Pipeline
    metrics: pd.DataFrame
    confusion: np.ndarray
    test_n: int
    train_n: int
    is_demo: bool


def fit_model(df: pd.DataFrame, is_demo: bool = True) -> ModelResult:
    """Separa 80/20, evalúa cinco modelos y reentrena RL para el panel completo.

    La evaluación se hace SOLO sobre el conjunto reservado. El panel aplica
    un modelo reentrenado sobre el dataset para ilustrar el flujo operativo.
    """
    X, y = df[list(FEATURES)], df["Target"].astype(int)
    xtr, xte, ytr, yte = train_test_split(X, y, test_size=TEST_SIZE, stratify=y, random_state=SEED)
    algs = {
        "Regresión Logística": LogisticRegression(max_iter=2000, random_state=SEED),
        "Gradient Boosting": GradientBoostingClassifier(random_state=SEED),
        "Random Forest": RandomForestClassifier(n_estimators=200, random_state=SEED, n_jobs=1),
        "AdaBoost": AdaBoostClassifier(random_state=SEED),
        "KNN": KNeighborsClassifier(n_neighbors=7),
    }
    results = []
    cm_rl = None
    for name, algo in algs.items():
        pipe = _build_pipeline(clone(algo))
        pipe.fit(xtr, ytr)
        pred = pipe.predict(xte)
        p = pipe.predict_proba(xte)[:, 1]
        results.append({
            "Modelo": name,
            "AUC-ROC": roc_auc_score(yte, p),
            "Recall": recall_score(yte, pred, zero_division=0),
            "Precisión": precision_score(yte, pred, zero_division=0),
            "F1-Score": f1_score(yte, pred, zero_division=0),
            "Accuracy": accuracy_score(yte, pred),
            "FN": int(((yte == 1) & (pred == 0)).sum()),
            "FP": int(((yte == 0) & (pred == 1)).sum()),
        })
        if name == "Regresión Logística":
            cm_rl = confusion_matrix(yte, pred, labels=[0, 1])
    model = _build_pipeline(LogisticRegression(max_iter=2000, random_state=SEED))
    model.fit(X, y)  # Modelo para el prototipo; métricas anteriores siguen fuera de muestra.
    scored = df.copy()
    scored["RiskProbability"] = model.predict_proba(X)[:, 1]
    scored["Alert"] = scored["RiskProbability"].map(classify_risk)
    scored = scored.sort_values("RiskProbability", ascending=False, kind="mergesort").reset_index(drop=True)
    return ModelResult(scored, model, pd.DataFrame(results), cm_rl, len(xte), len(xtr), is_demo)


def score_scenario(model: Pipeline, absences: int, tutoring: int, parental_support: int) -> float:
    row = pd.DataFrame([{ "Absences": float(absences), "Tutoring": float(tutoring), "ParentalSupport": float(parental_support)}])
    return float(model.predict_proba(row)[0, 1])


def suggested_interventions(student: pd.Series) -> list[tuple[str, str, str]]:
    """Acciones por señales observadas; NO interpretaciones causales del ML."""
    out = []
    if pd.notna(student["Absences"]) and float(student["Absences"]) >= 18:
        out.append(("calendar-check", "Revisar la asistencia", "Programar una conversación respetuosa para comprender las inasistencias y acordar alternativas de seguimiento."))
    if pd.notna(student["Tutoring"]) and float(student["Tutoring"]) == 0:
        out.append(("book-open-check", "Ofrecer apoyo académico", "Invitar a tutorías o mentorías de carácter preventivo; verificar disponibilidad y preferencias del estudiante."))
    if pd.notna(student["ParentalSupport"]) and float(student["ParentalSupport"]) <= 1:
        out.append(("hand-heart", "Fortalecer la red de apoyo", "Acercar opciones institucionales de orientación y acompañamiento, sin inferir dificultades económicas o familiares."))
    if not out:
        out.append(("clipboard-check", "Seguimiento periódico", "Mantener seguimiento académico habitual y comunicar las opciones de tutorías disponibles."))
    return out[:3]
