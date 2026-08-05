"""
Dashboard de test rapide — Smart Campus E-ID
Interface temporaire (Streamlit) pour tester visuellement le backend,
en attendant le vrai dashboard Angular (BF-13 à BF-16).

Installation :
    pip install streamlit requests pandas

Lancement :
    streamlit run app.py
    (ouvre automatiquement http://localhost:8501)

Le thème sombre "poste de contrôle" est défini dans .streamlit/config.toml
(à côté de ce fichier) — c'est le moteur de thème natif de Streamlit, pas
juste du CSS collé par-dessus.

Note : les formulaires s'ouvrent dans des boîtes de dialogue (st.dialog),
disponible à partir de Streamlit 1.37. Si le bouton "+ Ajouter" ne fait
rien, mets à jour Streamlit : pip install --upgrade streamlit

Prérequis : le backend doit tourner (docker compose up), accessible
sur http://localhost:8080 depuis la machine où ce script s'exécute.
"""

import time
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

API_BASE = "http://localhost:8080/api"

st.set_page_config(
    page_title="Smart Campus E-ID — Dashboard de test",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Tokens de design — "poste de contrôle d'accès", version sombre
# ---------------------------------------------------------------------------

TEAL = "#3EA88F"
TEAL_SOFT = "rgba(62, 168, 143, 0.14)"
AMBER = "#E3A339"
AMBER_SOFT = "rgba(227, 163, 57, 0.14)"
RUST = "#D9604A"
RUST_SOFT = "rgba(217, 96, 74, 0.14)"
STEEL = "#7C8B99"
TEXT_MUTED = "#8A98A6"
GLASS_BG = "rgba(255, 255, 255, 0.035)"
GLASS_BORDER = "rgba(255, 255, 255, 0.08)"
CARD_BG = "rgba(15, 20, 27, 0.82)"
CARD_TEXT = "#F2F4F5"

ROLE_ACCENT = {
    "ELEVE": TEAL,
    "PROFESSEUR": AMBER,
    "SURVEILLANT": RUST,
    "ADMIN": "#8E7CE8",
    "VISITEUR": STEEL,
}

# Colonnes qu'on affiche en pastille colorée dans les tableaux, par valeur
TABLE_PILLS = {
    "role": ROLE_ACCENT,
    "resultat": {"ACCORDE": TEAL, "REFUSE": RUST},
    "statut": {"NON_TRAITEE": RUST, "TRAITEE": TEAL},
}

NAV_ITEMS = [
    ("overview", "◆", "Vue d'ensemble"),
    ("zones", "▦", "Zones"),
    ("personnes", "◐", "Personnes"),
    ("regles", "⌘", "Règles d'accès"),
    ("test", "▶", "Tester un accès"),
    ("alertes", "▲", "Alertes"),
]

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"] {{
        font-family: 'IBM Plex Sans', sans-serif;
    }}
    h1, h2, h3 {{
        font-family: 'Space Grotesk', sans-serif !important;
        letter-spacing: -0.01em;
    }}

    /* Fond de page : grille subtile façon plan de campus */
    .stApp {{
        background-image:
            linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px);
        background-size: 34px 34px;
    }}

    /* ---- Navigation latérale ---- */
    [data-testid="stSidebar"] {{
        border-right: 1px solid {GLASS_BORDER};
    }}
    [data-testid="stSidebar"] .stButton > button {{
        width: 100%;
        justify-content: flex-start;
        text-align: left;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.86rem;
        border-radius: 8px;
        border: 1px solid transparent;
        background-color: transparent;
        color: {TEXT_MUTED};
        padding: 0.55rem 0.9rem;
    }}
    [data-testid="stSidebar"] .stButton > button:hover {{
        background-color: {GLASS_BG};
        border-color: {GLASS_BORDER};
        color: #E8ECEE;
    }}
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {{
        background-color: {TEAL_SOFT};
        border: 1px solid {TEAL};
        color: {TEAL} !important;
        box-shadow: none;
    }}
    .rail-badge {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.7rem;
        letter-spacing: 0.14em;
        color: {TEAL};
        border: 1px solid {TEAL};
        border-radius: 3px;
        padding: 3px 8px;
        display: inline-block;
        margin-bottom: 10px;
    }}

    /* ---- Pastille "système en ligne" ---- */
    .pulse-chip {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.72rem;
        letter-spacing: 0.08em;
        color: {TEAL};
        background: {TEAL_SOFT};
        border: 1px solid {TEAL};
        border-radius: 20px;
        padding: 5px 12px 5px 10px;
        float: right;
    }}
    .pulse-dot {{
        width: 7px; height: 7px; border-radius: 50%;
        background: {TEAL};
        box-shadow: 0 0 0 0 {TEAL};
        animation: pulse 2s infinite;
    }}
    @keyframes pulse {{
        0% {{ box-shadow: 0 0 0 0 rgba(62,168,143,0.55); }}
        70% {{ box-shadow: 0 0 0 7px rgba(62,168,143,0); }}
        100% {{ box-shadow: 0 0 0 0 rgba(62,168,143,0); }}
    }}
    .refresh-note {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.7rem;
        color: {TEXT_MUTED};
        float: right;
        margin-top: 6px;
        margin-right: 12px;
    }}

    /* ---- Cartes KPI en verre ---- */
    .kpi-card {{
        position: relative;
        background: {CARD_BG};
        border: 1px solid {GLASS_BORDER};
        border-radius: 14px;
        padding: 16px 18px;
        backdrop-filter: blur(6px);
        overflow: hidden;
    }}
    .kpi-card::before {{
        content: "";
        position: absolute; top: 0; left: 0; right: 0; height: 3px;
        background: linear-gradient(90deg, var(--accent), transparent 85%);
    }}
    .kpi-top {{ display: flex; justify-content: space-between; align-items: center; }}
    .kpi-icon {{ font-size: 1.1rem; color: var(--accent); }}
    .kpi-value {{
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2rem;
        font-weight: 600;
        margin-top: 6px;
        color: {CARD_TEXT} !important;
    }}
    .kpi-label {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.72rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: {TEXT_MUTED} !important;
        margin-top: 2px;
    }}
    .kpi-teal {{ --accent: {TEAL}; }}
    .kpi-amber {{ --accent: {AMBER}; }}
    .kpi-rust {{ --accent: {RUST}; }}
    .kpi-steel {{ --accent: {STEEL}; }}

    /* ---- Tampon de décision (signature du dashboard) ---- */
    .stamp {{
        display: flex; align-items: center; gap: 14px;
        font-family: 'IBM Plex Mono', monospace;
        border-radius: 10px;
        padding: 14px 18px;
        margin: 8px 0;
        border: 1px solid;
        backdrop-filter: blur(6px);
    }}
    .stamp-icon {{ font-size: 1.5rem; line-height: 1; }}
    .stamp-label {{ font-weight: 600; letter-spacing: 0.05em; font-size: 0.98rem; }}
    .stamp-detail {{ font-family: 'IBM Plex Sans', sans-serif; font-size: 0.85rem; color: {TEXT_MUTED}; }}
    .stamp-granted {{ background: {TEAL_SOFT}; border-color: {TEAL}; color: {TEAL}; }}
    .stamp-denied  {{ background: {RUST_SOFT}; border-color: {RUST}; color: {RUST}; }}
    .stamp-warn    {{ background: {AMBER_SOFT}; border-color: {AMBER}; color: {AMBER}; }}

    /* ---- Carte d'alerte ---- */
    .alert-card {{
        display: flex; justify-content: space-between; align-items: center;
        background: {CARD_BG};
        border: 1px solid {GLASS_BORDER};
        border-left: 3px solid {STEEL};
        border-radius: 10px;
        padding: 12px 18px;
        margin-bottom: 8px;
    }}
    .alert-card.pending {{ border-left-color: {RUST}; }}
    .alert-card.done {{ border-left-color: {TEAL}; opacity: 0.6; }}
    .alert-type {{
        font-family: 'Space Grotesk', sans-serif; font-weight: 600; font-size: 0.95rem;
        color: {CARD_TEXT} !important;
    }}
    .alert-meta {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.76rem; color: {TEXT_MUTED}; }}

    /* ---- Avatars initiales ---- */
    .avatar-row {{ display: flex; gap: 14px; flex-wrap: wrap; margin: 6px 0 18px 0; }}
    .avatar {{ display: flex; flex-direction: column; align-items: center; gap: 6px; width: 68px; }}
    .avatar-circle {{
        width: 44px; height: 44px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Space Grotesk', sans-serif; font-weight: 600; font-size: 0.9rem;
        color: #0B0F14;
    }}
    .avatar-name {{
        font-size: 0.68rem; color: {TEXT_MUTED}; text-align: center;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; width: 100%;
    }}

    /* ---- En-tête de section (titre de tableau + bouton ajouter) ---- */
    .section-row {{
        display: flex; align-items: center; justify-content: space-between;
        margin-top: 4px;
    }}
    .section-title {{
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600;
        font-size: 1.1rem;
    }}
    .section-count {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.75rem;
        color: {TEXT_MUTED};
        margin-left: 8px;
    }}

    /* Eyebrow au-dessus des titres */
    .eyebrow {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.72rem;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: {TEAL};
        margin-bottom: -4px;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Petits utilitaires d'appel API, avec gestion d'erreur affichée à l'écran
# ---------------------------------------------------------------------------

def api_get(path: str):
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Erreur API ({path}) : {e}")
        return []


def api_post_json(path: str, payload: dict):
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Erreur API ({path}) : {e}")
        return None


def api_patch_json(path: str, payload: dict):
    try:
        r = requests.patch(f"{API_BASE}{path}", json=payload, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Erreur API ({path}) : {e}")
        return None


def df_from(records, drop_cols=None):
    """Convertit une liste de dicts JSON en tableau affichable, en masquant
    au besoin des colonnes trop volumineuses (ex: l'embedding, 512 chiffres)."""
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    if drop_cols:
        df = df.drop(columns=[c for c in drop_cols if c in df.columns])
    return df


def styled_table(df, pill_col=None):
    """Colore une colonne de statut/rôle en pastille plutôt qu'en texte brut."""
    if df.empty or not pill_col or pill_col not in df.columns:
        return df
    colors = TABLE_PILLS.get(pill_col, {})
    if not colors:
        return df

    def _pill(value):
        c = colors.get(value)
        if not c:
            return ""
        return f"background-color: {c}26; color: {c}; font-weight: 600; border-radius: 6px;"

    styler = df.style
    apply_fn = styler.map if hasattr(styler, "map") else styler.applymap
    return apply_fn(_pill, subset=[pill_col])


def section_row(title: str, count: int, key: str, cta_label: str = "＋ Ajouter"):
    """Titre de section avec compteur à gauche, bouton d'ajout à droite."""
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown(
            f"<div class='section-row'><span class='section-title'>{title}</span>"
            f"<span class='section-count'>{count} au total</span></div>",
            unsafe_allow_html=True,
        )
    with col2:
        return st.button(cta_label, key=f"add_{key}", type="primary", use_container_width=True)


def page_header(eyebrow: str, title: str):
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"<div class='eyebrow'>{eyebrow}</div>", unsafe_allow_html=True)
        st.title(title)
    with col2:
        st.markdown(
            "<div class='pulse-chip'><span class='pulse-dot'></span>SYSTÈME EN LIGNE</div>"
            f"<div class='refresh-note'>actualisé à {datetime.now().strftime('%H:%M:%S')}</div>",
            unsafe_allow_html=True,
        )


def kpi_card(col, icon, label, value, accent="teal"):
    with col:
        st.markdown(
            f"""
            <div class="kpi-card kpi-{accent}">
                <div class="kpi-top"><span class="kpi-icon">{icon}</span></div>
                <div class="kpi-value">{value}</div>
                <div class="kpi-label">{label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def stamp(kind: str, icon: str, label: str, detail: str = ""):
    """Rend une décision (accès, alerte) sous forme de tampon de badge coloré."""
    css_class = {"granted": "stamp-granted", "denied": "stamp-denied", "warn": "stamp-warn"}[kind]
    st.markdown(
        f"""
        <div class="stamp {css_class}">
            <span class="stamp-icon">{icon}</span>
            <span class="stamp-label">{label}</span>
            <span class="stamp-detail">{detail}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def avatar_row(personnes, limit=8):
    if not personnes:
        return
    items = ""
    for p in personnes[:limit]:
        nom = p.get("nom", "?")
        role = p.get("role", "VISITEUR")
        initials = "".join([w[0] for w in nom.split()[:2]]).upper() or "?"
        color = ROLE_ACCENT.get(role, STEEL)
        items += (
            f"<div class='avatar'>"
            f"<div class='avatar-circle' style='background:{color};'>{initials}</div>"
            f"<div class='avatar-name'>{nom}</div>"
            f"</div>"
        )
    st.markdown(f"<div class='avatar-row'>{items}</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Boîtes de dialogue — un formulaire par entité, ouvert depuis "＋ Ajouter"
# ---------------------------------------------------------------------------

@st.dialog("Créer une zone")
def zone_dialog():
    nom = st.text_input("Nom de la zone", placeholder="ex : Laboratoire Info 2")
    description = st.text_input("Description (optionnel)", placeholder="ex : Accès réservé aux enseignants")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Annuler", use_container_width=True):
            st.rerun()
    with col2:
        if st.button("Créer", type="primary", use_container_width=True):
            if not nom:
                st.warning("Le nom de la zone est requis.")
            else:
                result = api_post_json("/zones", {"nom": nom, "description": description or None})
                if result:
                    st.success(f"Zone créée : {result.get('nom')}")
                    time.sleep(0.6)
                    st.rerun()


@st.dialog("Enrôler une personne")
def personne_dialog():
    nom = st.text_input("Nom", placeholder="ex : Amine Ben Salah")
    role = st.selectbox("Rôle", ["ELEVE", "PROFESSEUR", "SURVEILLANT", "ADMIN", "VISITEUR"])
    photos = st.file_uploader(
        "Photos (3-5 recommandées)", type=["jpg", "jpeg", "png"], accept_multiple_files=True
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Annuler", use_container_width=True, key="cancel_personne"):
            st.rerun()
    with col2:
        if st.button("Enrôler", type="primary", use_container_width=True, key="submit_personne"):
            if not nom or not photos:
                st.warning("Nom et au moins une photo sont nécessaires.")
            else:
                files = [("images", (p.name, p.getvalue(), p.type)) for p in photos]
                data = {"nom": nom, "role": role}
                try:
                    r = requests.post(f"{API_BASE}/personnes", data=data, files=files, timeout=30)
                    r.raise_for_status()
                    result = r.json()
                    st.success(f"Personne enrôlée : {result.get('nom')}")
                    time.sleep(0.6)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur lors de l'enrôlement : {e}")


@st.dialog("Créer une règle d'accès")
def regle_dialog(personnes, zones):
    personne_options = {p["nom"]: p["id"] for p in personnes}
    zone_options = {z["nom"]: z["id"] for z in zones}

    personne_nom = st.selectbox("Personne", list(personne_options.keys()))
    zone_nom = st.selectbox("Zone", list(zone_options.keys()))
    col1, col2 = st.columns(2)
    horaire_debut = col1.time_input("Horaire début")
    horaire_fin = col2.time_input("Horaire fin")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Annuler", use_container_width=True, key="cancel_regle"):
            st.rerun()
    with col2:
        if st.button("Créer", type="primary", use_container_width=True, key="submit_regle"):
            payload = {
                "personneId": personne_options[personne_nom],
                "zoneId": zone_options[zone_nom],
                "horaireDebut": horaire_debut.strftime("%H:%M"),
                "horaireFin": horaire_fin.strftime("%H:%M"),
            }
            result = api_post_json("/regles", payload)
            if result:
                st.success("Règle créée.")
                time.sleep(0.6)
                st.rerun()


# ---------------------------------------------------------------------------
# Navigation — rail à icônes avec état actif (bouton "primary" Streamlit)
# ---------------------------------------------------------------------------

if "page" not in st.session_state:
    st.session_state.page = "overview"

st.sidebar.markdown("<span class='rail-badge'>E-ID · SYS</span>", unsafe_allow_html=True)
st.sidebar.title("🎓 Smart Campus")
st.sidebar.caption("Poste de contrôle — dashboard de test")
st.sidebar.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

for key, icon, label in NAV_ITEMS:
    is_active = st.session_state.page == key
    if st.sidebar.button(f"{icon}   {label}", key=f"nav_{key}", type="primary" if is_active else "secondary"):
        st.session_state.page = key
        st.rerun()

st.sidebar.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
st.sidebar.markdown(
    f"<span style='font-family: IBM Plex Mono, monospace; font-size: 0.7rem; color: {TEXT_MUTED};'>"
    "BACKEND · localhost:8080</span>",
    unsafe_allow_html=True,
)

page = st.session_state.page

# ---------------------------------------------------------------------------
# Vue d'ensemble
# ---------------------------------------------------------------------------

if page == "overview":
    page_header("État du système", "Vue d'ensemble")

    zones = api_get("/zones")
    personnes = api_get("/personnes")
    evenements = api_get("/access-events")
    alertes = api_get("/alertes")

    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, "▦", "Zones", len(zones), "teal")
    kpi_card(c2, "◐", "Personnes enrôlées", len(personnes), "amber")
    kpi_card(c3, "≋", "Événements journalisés", len(evenements), "steel")
    kpi_card(c4, "▲", "Alertes non traitées",
             sum(1 for a in alertes if a.get("statut") == "NON_TRAITEE"), "rust")

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.markdown("##### Activité — événements journalisés")
        df_evt = df_from(evenements)
        if not df_evt.empty:
            chart_data = pd.DataFrame({"événements": range(1, len(df_evt) + 1)})
            st.area_chart(chart_data, color=TEAL, height=200)
        else:
            st.info("Aucun événement pour l'instant.")
    with col_right:
        st.markdown("##### Décisions")
        if not df_evt.empty and "resultat" in df_evt.columns:
            counts = df_evt["resultat"].value_counts()
            chart_df = pd.DataFrame({
                "ACCORDE": [counts.get("ACCORDE", 0)],
                "REFUSE": [counts.get("REFUSE", 0)],
            })
            st.bar_chart(chart_df, color=[TEAL, RUST], height=200)
        else:
            st.info("Pas encore de données.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### Derniers événements d'accès")
        if not df_evt.empty and "horodatage" in df_evt.columns:
            df_evt = df_evt.sort_values("horodatage", ascending=False)
        st.dataframe(styled_table(df_evt, "resultat"), use_container_width=True, height=260, hide_index=True)
    with col2:
        st.markdown("##### Alertes actives")
        alertes_actives = [a for a in alertes if a.get("statut") == "NON_TRAITEE"]
        st.dataframe(styled_table(df_from(alertes_actives), "statut"),
                     use_container_width=True, height=260, hide_index=True)

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    col_a, col_b = st.columns([1, 5])
    with col_a:
        if st.button("🔄 Rafraîchir"):
            st.rerun()
    with col_b:
        auto = st.checkbox("Rafraîchissement auto (toutes les 5s)")
    if auto:
        time.sleep(5)
        st.rerun()

# ---------------------------------------------------------------------------
# Zones
# ---------------------------------------------------------------------------

elif page == "zones":
    page_header("Périmètres surveillés", "Zones")

    zones = api_get("/zones")
    if section_row("Zones existantes", len(zones), "zone"):
        zone_dialog()

    st.dataframe(df_from(zones), use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Personnes
# ---------------------------------------------------------------------------

elif page == "personnes":
    page_header("Registre biométrique", "Personnes")

    personnes = api_get("/personnes")

    if personnes:
        st.markdown("##### Récemment enrôlées")
        avatar_row(personnes)

    if section_row("Toutes les personnes", len(personnes), "personne"):
        personne_dialog()

    st.dataframe(styled_table(df_from(personnes, drop_cols=["embedding"]), "role"),
                 use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Règles d'accès
# ---------------------------------------------------------------------------

elif page == "regles":
    page_header("Politique d'accès", "Règles d'accès")

    personnes = api_get("/personnes")
    zones = api_get("/zones")
    regles = api_get("/regles")

    if not personnes or not zones:
        st.info("Créez d'abord au moins une personne et une zone avant de définir une règle.")
        st.dataframe(df_from(regles), use_container_width=True, hide_index=True)
    else:
        if section_row("Règles existantes", len(regles), "regle"):
            regle_dialog(personnes, zones)
        st.dataframe(df_from(regles), use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Tester un accès — le plus utile pour valider BF-08 visuellement
# ---------------------------------------------------------------------------

elif page == "test":
    page_header("Simulation caméra", "Tester un accès")
    st.caption("Simule une caméra de zone : envoie une image, affiche la décision en temps réel.")

    zones = api_get("/zones")
    if not zones:
        st.info("Créez d'abord au moins une zone.")
    else:
        zone_options = {z["nom"]: z["id"] for z in zones}
        col1, col2 = st.columns([1, 1])
        with col1:
            zone_nom = st.selectbox("Zone testée", list(zone_options.keys()))
            image = st.file_uploader("Image à tester", type=["jpg", "jpeg", "png"])
            envoyer = st.button("Envoyer et décider", type="primary", disabled=image is None)
        with col2:
            if image is not None:
                st.image(image, width=260)

        if envoyer:
            files = {"image": (image.name, image.getvalue(), image.type)}
            data = {"zoneId": zone_options[zone_nom]}
            try:
                r = requests.post(f"{API_BASE}/access-events", data=data, files=files, timeout=15)
                r.raise_for_status()
                decisions = r.json()
                if not decisions:
                    stamp("warn", "⚠", "AUCUN VISAGE DÉTECTÉ", "L'image ne contient aucun visage exploitable.")
                for d in decisions:
                    nom = d.get("nom") or "INCONNU"
                    raison = d.get("raison", "")
                    if d.get("resultat") == "ACCORDE":
                        stamp("granted", "✅", f"ACCORDÉ · {nom}", raison)
                    else:
                        stamp("denied", "⛔", f"REFUSÉ · {nom}", raison)
            except Exception as e:
                st.error(f"Erreur lors du test : {e}")

# ---------------------------------------------------------------------------
# Alertes
# ---------------------------------------------------------------------------

elif page == "alertes":
    page_header("Supervision", "Alertes")

    alertes = api_get("/alertes")

    if alertes:
        by_type = pd.Series([a.get("type", "AUTRE") for a in alertes]).value_counts()
        st.markdown("##### Répartition par type")
        st.bar_chart(by_type, color=AMBER, height=180)

    if not alertes:
        st.info("Aucune alerte pour l'instant.")
    else:
        st.markdown("##### Détail des alertes")
        for a in alertes:
            statut = a.get("statut")
            is_pending = statut == "NON_TRAITEE"
            card_class = "pending" if is_pending else "done"
            emoji = "🔴" if is_pending else "✅"

            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(
                    f"""
                    <div class="alert-card {card_class}">
                        <div>
                            <div class="alert-type">{emoji} {a.get('type')}</div>
                            <div class="alert-meta">{statut} · {a.get('horodatage', '')}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col2:
                if is_pending:
                    if st.button("Marquer traitée", key=a.get("id")):
                        api_patch_json(f"/alertes/{a['id']}", {"statut": "TRAITEE"})
                        st.rerun()