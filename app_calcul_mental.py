import json
import streamlit as st

# Configuration de la page
st.set_page_config(page_title="Test de Calcul Mental", layout="centered")

# Chargement automatique des calculs depuis le fichier JSON
@st.cache_data
def charger_calculs():
    with open("calculs.json", "r", encoding="utf-8") as f:
        return json.load(f)

CALCULS = charger_calculs()

# Initialisation des états de session
if "soumis" not in st.session_state:
    st.session_state.soumis = False
if "score" not in st.session_state:
    st.session_state.score = 0
if "reponses_eleve" not in st.session_state:
    st.session_state.reponses_eleve = {}
if "pseudo" not in st.session_state:
    st.session_state.pseudo = ""

st.title("Test de Calcul Mental")
st.divider()

# CAS 1 : L'ÉLÈVE A SOUMIS SES RÉPONSES (AFFICHAGE DU RÉSULTAT ET DE LA CORRECTION)
if st.session_state.soumis:
    nom_affiche = st.session_state.pseudo if st.session_state.pseudo else "Anonyme"
    
    st.header("Résultat de l'évaluation")
    st.write(f"Candidat : **{nom_affiche}**")
    st.success(f"Score final : **{st.session_state.score} / {len(CALCULS)}**")
    st.divider()
    
    st.subheader("Correction détaillée")
    
    for calc in CALCULS:
        calc_id = calc["id"]
        # Récupération de la réponse élève en remplaçant la virgule par un point pour les décimaux
        rep_eleve = st.session_state.reponses_eleve.get(calc_id, "").strip().replace(",", ".")
        attendu = str(calc["reponse"])
        
        # Vérification robuste (comparaison numérique si possible, sinon textuelle)
        est_correct = False
        try:
            if float(rep_eleve) == float(attendu):
                est_correct = True
        except ValueError:
            if rep_eleve.lower() == attendu.lower():
                est_correct = True
        
        st.markdown(f"**Niveau {calc['niveau']} — Calcul : {calc['question']}**")
        col1, col2 = st.columns(2)
        col1.metric("Ta réponse", rep_eleve if rep_eleve else "Aucune")
        col2.metric("Réponse attendue", attendu)
        
        if est_correct:
            st.caption("Correct (+1 pt)")
        else:
            st.caption("Incorrect (0 pt)")
        st.divider()
        
    if st.button("Recommencer un test", use_container_width=True):
        st.session_state.soumis = False
        st.session_state.score = 0
        st.session_state.reponses_eleve = {}
        st.session_state.pseudo = ""
        st.rerun()

# CAS 2 : L'ÉLÈVE PASSE LE TEST
else:
    st.subheader("Identification")
    st.session_state.pseudo = st.text_input("Entre ton prénom (laisse vide si tu préfères rester anonyme) :")
    st.divider()
    
    st.subheader("Série de calculs")
    st.write("Résous les calculs suivants de tête, sans calculatrice :")
    
    user_answers = {}
    with st.form("form_calcul_mental"):
        for calc in CALCULS:
            user_answers[calc["id"]] = st.text_input(
                f"Calcul {calc['id']} (Niveau {calc['niveau']}) : {calc['question']} =",
                key=f"calc_{calc['id']}"
            )
        
        btn_valider = st.form_submit_button("Valider et voir la correction", type="primary", use_container_width=True)
        
    if btn_valider:
        score_total = 0
        for calc in CALCULS:
            rep = user_answers.get(calc["id"], "").strip().replace(",", ".")
            attendu = str(calc["reponse"])
            
            try:
                if float(rep) == float(attendu):
                    score_total += 1
            except ValueError:
                if rep.lower() == attendu.lower():
                    score_total += 1
                
        st.session_state.score = score_total
        st.session_state.reponses_eleve = user_answers
        st.session_state.soumis = True
        st.rerun()