import json
import random
import time
import pandas as pd
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

# ---------------------------------------------------------
# STOCKAGE CENTRALISÉ (POUR LE SUIVI ENSEIGNANT)
# ---------------------------------------------------------
@st.cache_resource
def get_global_database():
    return {
        "scores": {},      # {pseudo: score_total}
        "responses": {},   # {pseudo: {calcul_id: rep}}
        "details": {}      # {pseudo: {"nb_traites": x}}
    }

db = get_global_database()

# Barre latérale : Commutateur Vue Élève / Vue Enseignant
mode_vue = st.sidebar.radio("Mode d'affichage", ["Smartphone Élève", "Tableau de Bord Enseignant"])

# ---------------------------------------------------------
# MODE 1 : INTERFACE SMARTPHONE ÉLÈVE
# ---------------------------------------------------------
if mode_vue == "Smartphone Élève":
    # Initialisation des états de session élève
    if "etape" not in st.session_state:
        st.session_state.etape = "login"
    if "pseudo" not in st.session_state:
        st.session_state.pseudo = ""
    if "mode_jeu" not in st.session_state:
        st.session_state.mode_jeu = ""
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

    # ÉTAPE 1 : IDENTIFICATION
    if st.session_state.etape == "login":
        st.title("Test de Calcul Mental")
        st.divider()
        
        nom = st.text_input("Entre ton prénom (laisse vide pour rester anonyme) :")
        
        if st.button("Valider", type="primary", use_container_width=True):
            st.session_state.pseudo = nom.strip() if nom.strip() else f"Anonyme_{random.randint(100, 999)}"
            st.session_state.etape = "menu"
            st.rerun()

    # ÉTAPE 2 : CHOIX DU MODE (ENTRAÎNEMENT OU DÉFI)
    elif st.session_state.etape == "menu":
        st.title(f"Bonjour {st.session_state.pseudo}")
        st.divider()
        st.write("Choisis ton mode de jeu :")
        
        if st.button("Mode Entraînement (Aléatoire)", use_container_width=True):
            st.session_state.mode_jeu = "Entraînement"
            session_calculs = list(CALCULS)
            random.shuffle(session_calculs)
            st.session_state.calculs_session = session_calculs
            st.session_state.current_index = 0
            st.session_state.reponses_eleve = {}
            st.session_state.start_time = time.time()
            st.session_state.etape = "test"
            st.rerun()
            
        st.write("")
        st.markdown("---")
        st.write("Mode Défi (Affrontement)")
        mot_de_passe = st.text_input("Entre le mot de passe du défi :")
        
        if st.button("Lancer le Défi", type="primary", use_container_width=True):
            if mot_de_passe.strip():
                st.session_state.mode_jeu = f"Défi ({mot_de_passe.strip()})"
                session_calculs = list(CALCULS)
                # La seed garantit que tous ceux qui entrent ce mot de passe ont le même ordre
                random.seed(mot_de_passe.strip())
                random.shuffle(session_calculs)
                random.seed() # Réinitialisation
                st.session_state.calculs_session = session_calculs
                st.session_state.current_index = 0
                st.session_state.reponses_eleve = {}
                st.session_state.start_time = time.time()
                st.session_state.etape = "test"
                st.rerun()
            else:
                st.warning("Entre un mot de passe valide pour lancer le défi.")

    # ÉTAPE 3 : PASSAGE DU TEST
    elif st.session_state.etape == "test":
        timer_widget()
        
        calculs_session = st.session_state.calculs_session
        idx = st.session_state.current_index
        
        if idx >= len(calculs_session):
            st.session_state.etape = "fin"
            enregistrer_resultats()
            st.rerun()
            
        calc = calculs_session[idx]
        
        st.write(f"Calcul n°{idx + 1} ({st.session_state.mode_jeu})")
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

    # ÉTAPE 4 : RÉSULTAT ET CORRECTION
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
            
        if st.button("Revenir au menu", use_container_width=True):
            st.session_state.etape = "menu"
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
        eleve_selectionne = st.selectbox("Sélectionner un élève :", list(db["scores"].keys()))
        
        if eleve_selectionne:
            st.write(f"Détails des réponses pour **{eleve_selectionne}** :")
            reps_eleve = db["responses"].get(eleve_selectionne, {})
            
            for cid, val in reps_eleve.items():
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
                    st.write(f"- `{calc_trouve['question']}` -> Réponse : **{val}** (Attendu : {calc_trouve['reponse']}) → *{statut}*")
    else:
        st.info("Aucun résultat enregistré pour le moment.")
        
    st.divider()
    if st.button("Réinitialiser les données de session"):
        db["scores"].clear()
        db["responses"].clear()
        db["details"].clear()
        st.rerun()