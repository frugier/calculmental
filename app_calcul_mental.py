import json
import random
import time
import streamlit as st

# Configuration de la page
st.set_page_config(page_title="Test de Calcul Mental", layout="centered")

# Chargement automatique des calculs depuis le fichier JSON[cite: 2]
@st.cache_data
def charger_calculs():
    with open("calculs.json", "r", encoding="utf-8") as f:
        return json.load(f)

CALCULS = charger_calculs()
DUREE_SECONDES = 120  # 2 minutes

# Initialisation des états de session
if "etape" not in st.session_state:
    st.session_state.etape = "accueil"
if "pseudo" not in st.session_state:
    st.session_state.pseudo = ""
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "reponses_eleve" not in st.session_state:
    st.session_state.reponses_eleve = {}
if "calculs_session" not in st.session_state:
    st.session_state.calculs_session = []
if "start_time" not in st.session_state:
    st.session_state.start_time = None

# Fragment pour actualiser le timer chaque seconde
@st.fragment(run_every=1)
def timer_widget():
    if st.session_state.etape == "test" and st.session_state.start_time:
        ecoule = time.time() - st.session_state.start_time
        restant = int(DUREE_SECONDES - ecoule)
        if restant <= 0:
            st.session_state.etape = "fin"
            st.rerun()
        else:
            mins = restant // 60
            secs = restant % 60
            st.markdown(f"**Temps restant : {mins:02d}:{secs:02d}**")

# ---------------------------------------------------------
# ÉTAPE 1 : ACCUEIL / IDENTIFICATION
# ---------------------------------------------------------
if st.session_state.etape == "accueil":
    st.title("Test de Calcul Mental")
    st.divider()
    st.write("Le test dure 2 minutes. Les questions s'enchaînent une par une de manière aléatoire. Vous pouvez passer une question si vous ne savez pas.")
    
    nom = st.text_input("Entre ton prénom (laisse vide pour rester anonyme) :")
    
    if st.button("Commencer le test", type="primary", use_container_width=True):
        st.session_state.pseudo = nom.strip() if nom.strip() else "Anonyme"
        st.session_state.current_index = 0
        st.session_state.reponses_eleve = {}
        
        # Copie et mélange aléatoire des questions pour cette session
        session_calculs = list(CALCULS)
        random.shuffle(session_calculs)
        st.session_state.calculs_session = session_calculs
        
        st.session_state.start_time = time.time()
        st.session_state.etape = "test"
        st.rerun()

# ---------------------------------------------------------
# ÉTAPE 2 : PASSAGE DU TEST (QUESTION PAR QUESTION)
# ---------------------------------------------------------
elif st.session_state.etape == "test":
    timer_widget()
    
    calculs_session = st.session_state.calculs_session
    idx = st.session_state.current_index
    
    if idx >= len(calculs_session):
        st.session_state.etape = "fin"
        st.rerun()
        
    calc = calculs_session[idx]
    
    st.write(f"Question {idx + 1} / {len(calculs_session)}")
    st.progress((idx) / len(calculs_session))
    st.divider()
    
    # Affichage du calcul en grand format au centre
    st.markdown(f"<h1 style='text-align: center; font-size: 2.5rem;'>{calc['question']} = ?</h1>", unsafe_allow_html=True)
    st.write("")
    
    # st.number_input avec value=None force l'affichage du pavé numérique sur smartphone
    with st.form(key=f"form_q_{idx}"):
        reponse_saisie = st.number_input(
            "Ta réponse :", 
            value=None, 
            format="%g", 
            key=f"input_q_{calc['id']}", 
            label_visibility="collapsed"
        )
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            btn_valider = st.form_submit_button("Valider", type="primary", use_container_width=True)
        with col_btn2:
            btn_passer = st.form_submit_button("Passer", use_container_width=True)
        
    if btn_valider:
        st.session_state.reponses_eleve[calc['id']] = reponse_saisie
        st.session_state.current_index += 1
        if st.session_state.current_index >= len(calculs_session):
            st.session_state.etape = "fin"
        st.rerun()
    elif btn_passer:
        st.session_state.reponses_eleve[calc['id']] = None
        st.session_state.current_index += 1
        if st.session_state.current_index >= len(calculs_session):
            st.session_state.etape = "fin"
        st.rerun()

# ---------------------------------------------------------
# ÉTAPE 3 : RÉSULTAT ET CORRECTION DÉTAILLÉE
# ---------------------------------------------------------
elif st.session_state.etape == "fin":
    st.title("Résultat de l'évaluation")
    st.divider()
    
    calculs_session = st.session_state.calculs_session
    score = 0
    for calc in calculs_session:
        cid = calc['id']
        val_eleve = st.session_state.reponses_eleve.get(cid, None)
        attendu = float(calc["reponse"])
        
        if val_eleve is not None:
            try:
                if float(val_eleve) == attendu:
                    score += 1
            except ValueError:
                pass
                
    st.write(f"Candidat : **{st.session_state.pseudo}**")
    st.success(f"Score final : **{score} / {len(calculs_session)}**")
    st.divider()
    
    st.subheader("Correction détaillée")
    
    for calc in calculs_session:
        cid = calc['id']
        val_eleve = st.session_state.reponses_eleve.get(cid, None)
        attendu = float(calc["reponse"])
        
        est_correct = False
        if val_eleve is not None:
            try:
                if float(val_eleve) == attendu:
                    est_correct = True
            except ValueError:
                pass
                
        # Format d'affichage de la réponse de l'élève
        if val_eleve is not None:
            rep_texte = str(val_eleve)
        else:
            rep_texte = "Aucune (Passée)"
            
        st.markdown(f"**Niveau {calc['niveau']} — Calcul : {calc['question']}**")
        col1, col2 = st.columns(2)
        col1.metric("Ta réponse", rep_texte)
        col2.metric("Réponse attendue", str(calc["reponse"]))
        
        if est_correct:
            st.caption("Correct (+1 pt)")
        else:
            st.caption("Incorrect (0 pt)")
        st.divider()
        
    if st.button("Recommencer un test", use_container_width=True):
        st.session_state.etape = "accueil"
        st.session_state.pseudo = ""
        st.session_state.current_index = 0
        st.session_state.reponses_eleve = {}
        st.session_state.calculs_session = []
        st.session_state.start_time = None
        st.rerun()