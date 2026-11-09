import json
import random
import time
import pandas as pd
import streamlit as st

# Configuration de la page
st.set_page_config(page_title="Test de Calcul Mental - Suivi & Défis", layout="centered")

# Chargement automatique des calculs depuis le fichier JSON[cite: 2]
@st.cache_data
def charger_calculs():
    with open("calculs.json", "r", encoding="utf-8") as f:
        return json.load(f)

CALCULS = charger_calculs()
DUREE_SECONDES = 120  # 2 minutes

# ---------------------------------------------------------
# STOCKAGE CENTRALISÉ (PARTAGÉ POUR LE SUIVI ENSEIGNANT)
# ---------------------------------------------------------
@st.cache_resource
def get_global_database():
    return {
        "scores": {},      # {pseudo: score_total}
        "responses": {},   # {pseudo: {calcul_id: rep}}
        "details": {}      # {pseudo: {"nb_traites": x, "defi": code}}
    }

db = get_global_database()

# Barre latérale : Commutateur Vue Élève / Vue Enseignant
mode = st.sidebar.radio("Mode d'affichage", ["Smartphone Élève", "Tableau de Bord Enseignant"])

# ---------------------------------------------------------
# MODE 1 : INTERFACE SMARTPHONE ÉLÈVE
# ---------------------------------------------------------
if mode == "Smartphone Élève":
    # Initialisation des états de session élève
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
                # Enregistrement automatique à la fin du temps
                enregistrer_resultats()
                st.rerun()
            else:
                mins = restant // 60
                secs = restant % 60
                st.markdown(f"**Temps restant : {mins:02d}:{secs:02d}**")

    def enregistrer_resultats():
        calculs_session = st.session_state.calculs_session
        score = 0
        nb_traites = st.session_state.current_index
        
        for i in range(nb_traites):
            calc = calculs_session[i]
            cid = calc['id']
            val_eleve = st.session_state.reponses_eleve.get(cid, None)
            attendu = float(calc["reponse"])
            
            if val_eleve is not None:
                try:
                    if float(val_eleve) == attendu:
                        score += 1
                except ValueError:
                    pass
        
        pseudo = st.session_state.pseudo
        db["scores"][pseudo] = score
        db["responses"][pseudo] = st.session_state.reponses_eleve
        db["details"][pseudo] = {"nb_traites": nb_traites}

    # ÉTAPE 1 : ACCUEIL / IDENTIFICATION & DÉFI
    if st.session_state.etape == "accueil":
        st.title("Test de Calcul Mental")
        st.divider()
        st.write("Enchaîne le plus de calculs possible en 2 minutes.")
        
        nom = st.text_input("Entre ton prénom (laisse vide pour rester anonyme) :")
        code_defi = st.text_input("Code de défi (optionnel - laisse vide pour un test aléatoire classique) :")
        
        if st.button("Commencer le test", type="primary", use_container_width=True):
            st.session_state.pseudo = nom.strip() if nom.strip() else f"Anonyme_{random.randint(100, 999)}"
            st.session_state.current_index = 0
            st.session_state.reponses_eleve = {}
            
            # Gestion du défi : si un code est fourni, on s'en sert comme graine (seed)
            session_calculs = list(CALCULS)
            if code_defi.strip():
                random.seed(code_defi.strip())
                random.shuffle(session_calculs)
                random.seed() # Réinitialisation de la graine aléatoire standard
            else:
                random.shuffle(session_calculs)
                
            st.session_state.calculs_session = session_calculs
            st.session_state.start_time = time.time()
            st.session_state.etape = "test"
            st.rerun()

    # ÉTAPE 2 : PASSAGE DU TEST
    elif st.session_state.etape == "test":
        timer_widget()
        
        calculs_session = st.session_state.calculs_session
        idx = st.session_state.current_index
        
        if idx >= len(calculs_session):
            st.session_state.etape = "fin"
            enregistrer_resultats()
            st.rerun()
            
        calc = calculs_session[idx]
        
        st.write(f"Calcul n°{idx + 1}")
        st.markdown(f"<h1 style='text-align: center; font-size: 2.2rem; margin-top: 10px; margin-bottom: 10px;'>{calc['question']} = ?</h1>", unsafe_allow_html=True)
        
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
                enregistrer_resultats()
            st.rerun()
        elif btn_passer:
            st.session_state.reponses_eleve[calc['id']] = None
            st.session_state.current_index += 1
            if st.session_state.current_index >= len(calculs_session):
                st.session_state.etape = "fin"
                enregistrer_resultats()
            st.rerun()

    # ÉTAPE 3 : RÉSULTAT ET CORRECTION
    elif st.session_state.etape == "fin":
        st.title("Résultat de l'évaluation")
        st.divider()
        
        calculs_session = st.session_state.calculs_session
        score = db["scores"].get(st.session_state.pseudo, 0)
        nb_traites = st.session_state.current_index
        
        st.write(f"Candidat : **{st.session_state.pseudo}**")
        st.success(f"Score final : **{score} / {nb_traites}** (traités en 2 minutes)")
        st.divider()
        
        st.subheader("Correction détaillée")
        
        for i in range(nb_traites):
            calc = calculs_session[i]
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
                    
            rep_texte = str(val_eleve) if val_eleve is not None else "Aucune (Passée)"
                
            st.markdown(f"**Calcul : {calc['question']}**")
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

# ---------------------------------------------------------
# MODE 2 : TABLEAU DE BORD ENSEIGNANT
# ---------------------------------------------------------
else:
    st.title("Tableau de bord - Suivi de classe")
    st.divider()
    
    if db["scores"]:
        # Création du tableau récapitulatif
        data_tableau = []
        for pseudo, score in db["scores"].items():
            nb_traites = db["details"].get(pseudo, {}).get("nb_traites", 0)
            data_tableau.append({
                "Élève": pseudo,
                "Score": score,
                "Calculs traités": nb_traites
            })
            
        df = pd.DataFrame(data_tableau)
        df = df.sort_values(by="Score", ascending=False).reset_index(drop=True)
        df.index += 1
        
        st.write(f"Nombre total de participants : **{len(db['scores'])}**")
        st.dataframe(df, use_container_width=True)
        
        st.divider()
        st.subheader("Analyse par élève")
        eleve_selectionne = st.selectbox("Sélectionner un élève pour voir son parcours :", list(db["scores"].keys()))
        
        if eleve_selectionne:
            st.write(f"Détails des réponses pour **{eleve_selectionne}** :")
            reps_eleve = db["responses"].get(eleve_selectionne, {})
            
            for cid, val in reps_eleve.items():
                # Retrouver la question correspondante dans le JSON
                calc_trouve = next((c for c in CALCULS if c["id"] == cid), None)
                if calc_trouve:
                    attendu = float(calc_trouve["reponse"])
                    correct = False
                    if val is not None:
                        try:
                            if float(val) == attendu:
                                correct = True
                        except ValueError:
                            pass
                    statut = "Correct" if correct else ("Passé" if val is None else "Incorrect")
                    st.write(f"- `{calc_trouve['question']}` -> Réponse élève : **{val}** (Attendu : {calc_trouve['reponse']}) → *{statut}*")
    else:
        st.info("Aucun élève n'a encore terminé de test pour le moment.")
        
    st.divider()
    if st.button("Réinitialiser toutes les données de session"):
        db["scores"].clear()
        db["responses"].clear()
        db["details"].clear()
        st.rerun()