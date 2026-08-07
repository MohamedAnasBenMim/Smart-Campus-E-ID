"""
Dashboard de test rapide — Smart Campus E-ID
Interface temporaire (Streamlit) pour tester visuellement le backend,
en attendant le vrai dashboard Angular (BF-13 à BF-16).

Installation :
    pip install streamlit requests pandas

Lancement :
    streamlit run app.py
    (ouvre automatiquement http://localhost:8501)

Prérequis : le backend doit tourner (docker compose up), accessible
sur http://localhost:8080 depuis la machine où ce script s'exécute.
"""

import time

import pandas as pd
import requests
import streamlit as st

API_BASE = "http://localhost:8080/api"

st.set_page_config(page_title="Smart Campus E-ID — Dashboard de test", layout="wide")


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
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    if drop_cols:
        df = df.drop(columns=[c for c in drop_cols if c in df.columns])
    return df


st.sidebar.title("🎓 Smart Campus E-ID")
st.sidebar.caption("Dashboard de test — remplace temporairement Angular")
page = st.sidebar.radio(
    "Navigation",
    ["Vue d'ensemble", "Zones", "Personnes", "Règles d'accès", "Tester un accès", "Alertes"],
)

# ---------------------------------------------------------------------------
if page == "Vue d'ensemble":
    st.title("Vue d'ensemble")

    col_a, col_b = st.columns([1, 4])
    with col_a:
        if st.button("🔄 Rafraîchir"):
            st.rerun()
    with col_b:
        auto = st.checkbox("Rafraîchissement auto (toutes les 5s)")

    zones = api_get("/zones")
    personnes = api_get("/personnes")
    evenements = api_get("/access-events")
    alertes = api_get("/alertes")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Zones", len(zones))
    c2.metric("Personnes enrôlées", len(personnes))
    c3.metric("Événements journalisés", len(evenements))
    c4.metric("Alertes non traitées", sum(1 for a in alertes if a.get("statut") == "NON_TRAITEE"))

    st.subheader("Derniers événements d'accès")
    df_evt = df_from(evenements)
    if not df_evt.empty and "horodatage" in df_evt.columns:
        df_evt = df_evt.sort_values("horodatage", ascending=False)
    st.dataframe(df_evt, use_container_width=True)

    st.subheader("Alertes actives")
    alertes_actives = [a for a in alertes if a.get("statut") == "NON_TRAITEE"]
    st.dataframe(df_from(alertes_actives), use_container_width=True)

    if auto:
        time.sleep(5)
        st.rerun()

# ---------------------------------------------------------------------------
elif page == "Zones":
    st.title("Zones")

    st.subheader("Zones existantes")
    zones = api_get("/zones")
    st.dataframe(df_from(zones), use_container_width=True)

    st.subheader("Créer une zone")
    with st.form("form_zone"):
        nom = st.text_input("Nom de la zone")
        description = st.text_input("Description (optionnel)")
        submitted = st.form_submit_button("Créer")
        if submitted and nom:
            result = api_post_json("/zones", {"nom": nom, "description": description or None})
            if result:
                st.success(f"Zone créée : {result.get('nom')} (id: {result.get('id')})")
                st.rerun()

# ---------------------------------------------------------------------------
elif page == "Personnes":
    st.title("Personnes")

    st.subheader("Personnes enrôlées")
    personnes = api_get("/personnes")
    st.dataframe(df_from(personnes, drop_cols=["embedding"]), use_container_width=True)

    st.subheader("Enrôler une nouvelle personne")
    with st.form("form_personne"):
        nom = st.text_input("Nom")
        role = st.selectbox("Rôle", ["ELEVE", "PROFESSEUR", "SURVEILLANT", "ADMIN", "VISITEUR"])
        photos = st.file_uploader(
            "Photos (3-5 recommandées)", type=["jpg", "jpeg", "png"], accept_multiple_files=True
        )
        submitted = st.form_submit_button("Enrôler")
        if submitted:
            if not nom or not photos:
                st.warning("Nom et au moins une photo sont nécessaires.")
            else:
                files = [("images", (p.name, p.getvalue(), p.type)) for p in photos]
                data = {"nom": nom, "role": role}
                try:
                    r = requests.post(f"{API_BASE}/personnes", data=data, files=files, timeout=30)
                    r.raise_for_status()
                    result = r.json()
                    st.success(f"Personne enrôlée : {result.get('nom')} (id: {result.get('id')})")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur lors de l'enrôlement : {e}")

# ---------------------------------------------------------------------------
elif page == "Règles d'accès":
    st.title("Règles d'accès")

    personnes = api_get("/personnes")
    zones = api_get("/zones")

    st.subheader("Règles existantes")
    regles = api_get("/regles")
    st.dataframe(df_from(regles), use_container_width=True)

    if not personnes or not zones:
        st.info("Créez d'abord au moins une personne et une zone.")
    else:
        st.subheader("Créer une règle")
        personne_options = {p["nom"]: p["id"] for p in personnes}
        zone_options = {z["nom"]: z["id"] for z in zones}

        with st.form("form_regle"):
            personne_nom = st.selectbox("Personne", list(personne_options.keys()))
            zone_nom = st.selectbox("Zone", list(zone_options.keys()))
            col1, col2 = st.columns(2)
            horaire_debut = col1.time_input("Horaire début")
            horaire_fin = col2.time_input("Horaire fin")
            submitted = st.form_submit_button("Créer la règle")
            if submitted:
                payload = {
                    "personneId": personne_options[personne_nom],
                    "zoneId": zone_options[zone_nom],
                    "horaireDebut": horaire_debut.strftime("%H:%M"),
                    "horaireFin": horaire_fin.strftime("%H:%M"),
                }
                result = api_post_json("/regles", payload)
                if result:
                    st.success("Règle créée.")
                    st.rerun()

# ---------------------------------------------------------------------------
elif page == "Tester un accès":
    st.title("Tester un accès")
    st.caption("Simule une caméra de zone : envoie une image, affiche la décision en temps réel.")

    zones = api_get("/zones")
    if not zones:
        st.info("Créez d'abord au moins une zone.")
    else:
        zone_options = {z["nom"]: z["id"] for z in zones}
        zone_nom = st.selectbox("Zone testée", list(zone_options.keys()))
        image = st.file_uploader("Image à tester", type=["jpg", "jpeg", "png"])

        if image is not None:
            st.image(image, width=250)

        if st.button("Envoyer et décider", disabled=image is None):
            files = {"image": (image.name, image.getvalue(), image.type)}
            data = {"zoneId": zone_options[zone_nom]}
            try:
                r = requests.post(f"{API_BASE}/access-events", data=data, files=files, timeout=15)
                r.raise_for_status()
                decisions = r.json()
                if not decisions:
                    st.warning("Aucun visage ni personne exploitable détecté dans l'image.")
                for d in decisions:
                    resultat = d.get("resultat")
                    raison = d.get("raison") or ""
                    nom = d.get("nom") or "Inconnu"
                    if resultat == "ACCORDE":
                        st.success(f"✅ ACCORDE — {nom} — {raison}")
                    elif "IDENTITE_A_CONFIRMER" in raison or "confiance réduite" in raison:
                        st.warning(f"⚠️ REFUSE (à vérifier manuellement) — {nom} — {raison}")
                    else:
                        st.error(f"⛔ REFUSE — {nom} — {raison}")
            except Exception as e:
                st.error(f"Erreur lors du test : {e}")

# ---------------------------------------------------------------------------
elif page == "Alertes":
    st.title("Alertes")

    alertes = api_get("/alertes")
    if not alertes:
        st.info("Aucune alerte pour l'instant.")
    else:
        for a in alertes:
            col1, col2, col3 = st.columns([2, 2, 1])
            statut = a.get("statut")
            emoji = "🔴" if statut == "NON_TRAITEE" else "✅"
            col1.write(f"{emoji} **{a.get('type')}**")
            col2.write(f"Statut : {statut} · {a.get('horodatage', '')}")
            if statut == "NON_TRAITEE":
                if col3.button("Marquer traitée", key=a.get("id")):
                    api_patch_json(f"/alertes/{a['id']}", {"statut": "TRAITEE"})
                    st.rerun()