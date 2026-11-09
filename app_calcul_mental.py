import json
import time
import pandas as pd
import streamlit as st

# Configuration de la page
st.set_page_config(page_title="Test de Calcul Mental", layout="wide")

# ---------------------------------------------------------
# LISTE DES CALCULS (à adapter selon tes besoins)
# ---------------------------------------------------------
# Chaque élément contient l'énoncé et la réponse exacte (ou une fonction de validation)
CALCULS = [
    {"id": 1, "enonce": "7 × 8", "reponse": "56"},
    {"id": 2, "enonce": "12 + 19", "reponse": "31"},
    {"id": 3, "enonce": "50 - 17", "reponse": "33"},
    {"id": 4, "enonce": "9 × 9", "reponse": "81"},
    {"id": 5, "enonce": "144 / 12", "reponse": "12"},
    {"id": 6, "enonce": "15 × 4", "reponse": "60"},
    {"id": 7, "enonce": "25 + 38", "reponse": "63"},
    {"id": 8, "enonce": "81 / 9", "reponse": "9"},
    {"id": 9, "enonce": "6 × 13", "reponse": "78"},
    {"id": 10, "enonce": "100 - 43", "reponse": "57"}
]

# ---------------------------------------------------------
# STOCKAGE CENTRALISÉ (PARTAGÉ ENTRE TOUS LES APPAREILS)
# ---------------------------------------------------------
@st.cache_resource
def get_global_database():
    return {
        "scores": {},          # {pseudo: score_total}
        "responses": {},       # {pseudo: {calcul_id: rep}}
        "notes_cours": {},     # {pseudo: note_evaluation}
        "test_lance": False,   # Indique si le test a démarré
        "duree_minutes": 2,    # Durée par défaut en minutes
        "show_correction": False
    }

db = get_global_database()

# Fragment de mise en attente (rafraîchissement automatique)
@st.fragment(run_every=2)
def waiting_screen_fragment():
    if db["show_correction"] or not db["test_lance"]:
        st.rerun()
    else:
        st.info("Test en cours ou en attente des résultats...")

# Barre latérale : Commutateur Vue Élève / Vue Enseignant
mode = st.sidebar.radio("Mode d'affichage", ["Smartphone Élève", "Écran Projeté (Enseignant)"])

# ---------------------------------------------------------
# MODE 1 : INTERFACE SMARTPHONE ÉLÈVE
# ---------------------------------------------------------
if mode == "Smartphone Élève":
    st.title("Test de Calcul Mental")
    
    already_submitted = st.session_state.get("submitted_pseudo", None)
    
    # Si la session a été réinitialisée par l'enseignant
    if already_submitted and already_submitted not in db["scores"]:
        st.session_state.submitted_pseudo = None
        st.session_state.etape = "identite"
        already_submitted = None

    if "etape" not in st.session_state:
        st.session_state.etape = "identite"

    # CAS 1 : LA CORRECTION EST ACTIVÉE
    if db["show_correction"]:
        st.header("Correction détaillée")
        
        if already_submitted and already_submitted in db["responses"]:
            score_eleve = db["scores"][already_submitted]
            st.success(f"Score pour **{already_submitted}** : **{score_eleve} / {len(CALCULS)}**")
            st.divider()
            
            user_res = db["responses"][already_submitted]
            
            for calc in CALCULS:
                st.markdown(f"**Calcul : {calc['enonce']}**")
                rep_eleve = user_res.get(calc["id"], "").strip()
                attendu = calc["reponse"]
                
                est_correct = (rep_eleve == attendu)
                
                col1, col2 = st.columns(2)
                col1.metric("Ta réponse", rep_eleve if rep_eleve else "Aucune")
                col2.metric("Réponse attendue", attendu)
                
                if est_correct:
                    st.caption("Correct (+1 pt)")
                else:
                    st.caption("Incorrect (0 pt)")
                st.divider()
        else:
            st.info("La correction est affichée au tableau. Vous n'avez pas soumis de réponses.")

    # CAS 2 : SOUMIS (EN ATTENTE)
    elif already_submitted and already_submitted in db["scores"]:
        st.success(f"Réponses enregistrées pour **{already_submitted}**.")
        st.info("Vos réponses ont été transmises. Attente de la correction au tableau.")
        waiting_screen_fragment()

    # CAS 3 : ÉTAPE D'ÉVALUATION (AVANT VALIDATION FINALE)
    elif st.session_state.etape == "note_cours":
        st.subheader("Évaluation du test")
        st.write("Donne une note à la difficulté de la session :")

        def forcer_dix_et_compter():
            st.session_state.note_slider = 10
            st.session_state.compteur_tentatives = st.session_state.get("compteur_tentatives", 0) + 1

        if "note_slider" not in st.session_state:
            st.session_state.note_slider = 5
        if "compteur_tentatives" not in st.session_state:
            st.session_state.compteur_tentatives = 0

        est_verrouille = st.session_state.compteur_tentatives >= 3

        note = st.slider(
            "Note sur 10 :", 
            min_value=0, 
            max_value=10, 
            key="note_slider",
            disabled=est_verrouille,
            on_change=forcer_dix_et_compter
        )

        if est_verrouille:
            st.caption("Valeur verrouillée.")
        elif note == 10:
            st.caption("Parfait !")

        if st.button("Envoyer définitivement", type="primary", use_container_width=True):
            pseudo_clean = st.session_state.temp_pseudo
            db["scores"][pseudo_clean] = st.session_state.temp_score
            db["responses"][pseudo_clean] = st.session_state.temp_answers
            db["notes_cours"][pseudo_clean] = note
            st.session_state.submitted_pseudo = pseudo_clean
            st.rerun()

    # CAS 4 : LE TEST N'EST PAS ENCORE LANCÉ PAR LE PROF
    elif not db["test_lance"]:
        st.info("En attente du lancement du test par l'enseignant...")
        st.fragment(run_every=2)(lambda: st.rerun() if db["test_lance"] else None)()

    # CAS 5 : PASSAGE DU TEST
    else:
        # Saisie d'identité optionnelle / anonymat
        if "temp_pseudo" not in st.session_state or not st.session_state.temp_pseudo:
            st.subheader("Identification")
            saisie_nom = st.text_input("Entre ton prénom (laisse vide ou écris 'anonyme' pour rester anonyme) :")
            
            if st.button("Commencer le test", type="primary"):
                if not saisie_nom.strip() or saisie_nom.strip().lower() == "anonyme":
                    import random
                    pseudo_clean = f"Anonyme_{random.randint(100, 999)}"
                else:
                    pseudo_clean = saisie_nom.strip()
                
                st.session_state.temp_pseudo = pseudo_clean
                st.rerun()
        else:
            st.write(f"Candidat : **{st.session_state.temp_pseudo}**")
            st.write(f"Résous le plus de calculs possible :")
            
            user_answers = {}
            with st.form("form_calculs"):
                for calc in CALCULS:
                    user_answers[calc["id"]] = st.text_input(
                        f"Calcul {calc['id']} : {calc['enonce']} =",
                        key=f"calc_{calc['id']}"
                    )
                
                btn_fin = st.form_submit_button("Valider mes réponses", type="primary", use_container_width=True)
            
            if btn_fin:
                score_total = 0
                for calc in CALCULS:
                    rep = user_answers.get(calc["id"], "").strip()
                    if rep == calc["reponse"]:
                        score_total += 1
                
                st.session_state.temp_score = score_total
                st.session_state.temp_answers = user_answers
                st.session_state.etape = "note_cours"
                st.rerun()

# ---------------------------------------------------------
# MODE 2 : ÉCRAN PROJETÉ (ENSEIGNANT)
# ---------------------------------------------------------
else:
    st.title("Tableau de bord - Enseignant")
    
    if "reveal_stage" not in st.session_state:
        st.session_state.reveal_stage = 0

    col_ctrl1, col_ctrl2 = st.columns(2)
    with col_ctrl1:
        if not db["test_lance"]:
            if st.button("Lancer le test", type="primary", use_container_width=True):
                db["test_lance"] = True
                st.rerun()
        else:
            if st.button("Arrêter / Verrouiller le test", use_container_width=True):
                db["test_lance"] = False
                st.rerun()
    with col_ctrl2:
        st.write(état := f"Statut : {'En cours' if db['test_lance'] নয় else 'En attente / Arrêté'}")

    st.divider()
    
    st.write(f"Nombre de participants ayant validé : **{len(db['scores'])}**")

    if db["scores"]:
        col_note = f"Score (/{len(CALCULS)})"
        df_complet = pd.DataFrame(
            list(db["scores"].items()), 
            columns=["Élève", col_note]
        )
        df_complet = df_complet.sort_values(by=col_note, ascending=False, kind="stable").reset_index(drop=True)
        df_complet.index += 1

        stage = st.session_state.reveal_stage
        
        if stage == 0:
            st.warning("Classement masqué.")
        else:
            if stage == 6:
                st.subheader("Classement complet")
                st.dataframe(df_complet, use_container_width=True, height=350)
            else:
                st.subheader("Top 5 en cours de révélation...")
                indices_a_montrer = [5 - i - 1 for i in range(stage)]
                for idx in indices_a_montrer:
                    if idx < len(df_complet):
                        row = df_complet.iloc[idx]
                        rang = idx + 1
                        st.markdown(f"Rang #{rang} : **{row['Élève']}** — `{row[col_note]}/{len(CALCULS)} pts`")
                    st.divider()

        c1, c2, c3 = st.columns(3)
        with c1:
            if stage < 5:
                prochain_rang = 5 - stage
                if st.button(f"Révéler la {prochain_rang}e place"):
                    st.session_state.reveal_stage += 1
                    st.rerun()
            elif stage == 5:
                st.success("Top 5 révélé.")
        with c2:
            if st.button("Afficher TOUT le classement"):
                st.session_state.reveal_stage = 6
                st.rerun()
        with c3:
            if st.button("Masquer le classement"):
                st.session_state.reveal_stage = 0
                st.rerun()

    st.divider()

    col_g, col_m, col_d = st.columns(3)
    with col_g:
        if st.button("Rafraîchir les données"):
            st.rerun()
    with col_m:
        btn_label = "Masquer la correction" if db["show_correction"] else "Afficher la correction"
        if st.button(btn_label, type="primary"):
            db["show_correction"] = not db["show_correction"]
            st.rerun()
    with col_d:
        if st.button("Réinitialiser la session"):
            db["scores"].clear()
            db["responses"].clear()
            db["notes_cours"].clear()
            db["test_lance"] = False
            db["show_correction"] = False
            st.session_state.reveal_stage = 0
            st.rerun()

    # SECTION CORRECTION
    if db["show_correction"]:
        st.divider()
        st.subheader("Synthèse & Correction générale")
        
        if db["notes_cours"]:
            notes_list = list(db["notes_cours"].values())
            moyenne_cours = sum(notes_list) / len(notes_list)
            st.metric("Appréciation moyenne du test", f"{moyenne_cours:.1f} / 10")
            st.divider()

        if db["responses"]:
            nb_eleves = len(db["responses"])
            for calc in CALCULS:
                st.markdown(f"**Calcul {calc['id']} : {calc['enonce']}** (Réponse : {calc['reponse']})")
                nb_reussite = 0
                for user_resp in db["responses"].values():
                    if user_resp.get(calc["id"], "").strip() == calc["reponse"]:
                        nb_reussite += 1
                
                pct = int((nb_reussite / nb_eleves) * 100) if nb_eleves > 0 else 0
                st.progress(pct / 100, text=f"Taux de réussite : {pct}% ({nb_reussite}/{nb_eleves})")
                st.divider()
        else:
            st.info("Aucune réponse enregistrée.")