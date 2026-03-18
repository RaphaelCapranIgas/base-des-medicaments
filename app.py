import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from sqlalchemy import create_engine, text
import io
from folium.plugins import MarkerCluster
from folium.plugins import FastMarkerCluster
import plotly.express as px
import plotly.graph_objects as go
# Configuration
st.set_page_config(page_title="Base des médicaments", layout="wide")

# On utilise la boîte à secrets de Streamlit :
try:
    DATABASE_URL = st.secrets["database"]["url"]
except Exception:
    # Option de secours si le fichier secrets est absent
    DATABASE_URL = "postgresql://postgres:0000@localhost:5432/medicaments_db"

engine = create_engine(DATABASE_URL)

@st.cache_data
def get_data(query, params=None):
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)

# Pour pointer sur les anciennes adresses
# @st.cache_data
# def get_liste_pays():
#     """Récupère la liste alphabétique de tous les pays disponibles dans la base"""
#     sql = "SELECT DISTINCT pays_propre FROM fabricant WHERE pays_propre IS NOT NULL ORDER BY pays_propre"
#     df_pays = get_data(sql)
#     return df_pays['pays_propre'].tolist()
@st.cache_data
def get_liste_pays():
    sql = "SELECT DISTINCT pays FROM paysfabrication WHERE pays IS NOT NULL ORDER BY pays"
    df_pays = get_data(sql)
    return df_pays['pays'].tolist()

def injecter_css_pro():
    st.markdown("""
        <style>
        /* Ombre douce sous les cadres et metrics pour un effet 'Dashboard' */
        div[data-testid="metric-container"] {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            padding: 5% 5% 5% 10%;
            border-radius: 10px;
            box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.05);
        }

        /* Cacher le menu "hamburger" en haut à droite (plus pro pour les utilisateurs) */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}

        /* Styliser un peu les expanders (menus déroulants) */
        .streamlit-expanderHeader {
            background-color: #f1f5f9;
            border-radius: 5px;
        }
        </style>
    """, unsafe_allow_html=True)

TRADUCTION_PAYS = {
    "AT": "Autriche",
    "BE": "Belgique",
    "BG": "Bulgarie",
    "CH": "Suisse",
    "CY": "Chypre",
    "CZ": "République Tchèque",
    "DE": "Allemagne",
    "DK": "Danemark",
    "EE": "Estonie",
    "ES": "Espagne",
    "FI": "Finlande",
    "FR": "France",
    "GB": "Royaume-Uni",
    "GF": "Guyane",
    "GP": "Guadeloupe",
    "GR": "Grèce",
    "HR": "Croatie",
    "HT": "Haïti",
    "HU": "Hongrie",
    "IE": "Irlande",
    "IS": "Islande",
    "IT": "Italie",
    "LT": "Lituanie",
    "LV": "Lettonie",
    "MA": "Maroc",
    "MC": "Monaco",
    "MQ": "Martinique",
    "MT": "Malte",
    "NL": "Pays-Bas",
    "NO": "Norvège",
    "PL": "Pologne",
    "PT": "Portugal",
    "RE": "La Réunion",
    "RO": "Roumanie",
    "SE": "Suède",
    "SI": "Slovénie",
    "SK": "Slovaquie"
}

def search_section():

    st.sidebar.image("logo_igas.png", use_container_width=True)
    st.sidebar.title("Navigation")

    # Les deux barres de recherche
    query_med = st.sidebar.text_input("Médicament / Composant", "")
    query_code = st.sidebar.text_input("CIS / ATC", "")
    query_lab = st.sidebar.text_input("Laboratoire", "")

    # ==========================================
    # FILTRE GÉOGRAPHIQUE
    # ==========================================
    st.sidebar.markdown("---")
    tous_les_pays = get_liste_pays() # Ça récupère toujours ["AT", "BE", "FR"...]
    pays_selectionnes = []

    with st.sidebar.expander("Filtrer par pays"):

        for code_pays in tous_les_pays:

            # On cherche le nom complet. S'il n'est pas dans le dictionnaire, on affiche le code par défaut.
            nom_complet = TRADUCTION_PAYS.get(code_pays, code_pays) 

            if st.checkbox(nom_complet, value=True, key=f"geo_{code_pays}"):
                # Si c'est coché, on garde le CODE pour que le SQL fonctionne 
                pays_selectionnes.append(code_pays)

    # ==========================================
    # FILTRES (2 Colonnes)
    # ==========================================

    st.sidebar.markdown("---")
    st.sidebar.write("**Filtres par liste :**")

    col_nom, col_inc, col_exc = st.sidebar.columns([2, 1, 1])
    col_nom.write(" ") 
    col_inc.write("✅")
    col_exc.write("❌")

    # === MITM ===
    col_nom, col_inc, col_exc = st.sidebar.columns([2, 1, 1])
    col_nom.markdown(
        "<p style='margin-bottom: 0; line-height: 1.2;'>MITM<br><span style='font-size: 0.8rem; color: #888;'>MàJ : 04/07/2025</span></p>", 
        unsafe_allow_html=True
    )
    inc_mitm = col_inc.checkbox("inc_mitm", key="inc_mitm", label_visibility="collapsed")
    exc_mitm = col_exc.checkbox("exc_mitm", key="exc_mitm", label_visibility="collapsed")

    # === LME de l'OMS ===
    col_nom, col_inc, col_exc = st.sidebar.columns([2, 1, 1])
    col_nom.markdown(
        "<p style='margin-bottom: 0; line-height: 1.2;'>LME de l'OMS<br><span style='font-size: 0.8rem; color: #888;'>MàJ : 05/10/2025</span></p>", 
        unsafe_allow_html=True
    )
    inc_lme = col_inc.checkbox("inc_lme", key="inc_lme", label_visibility="collapsed")
    exc_lme = col_exc.checkbox("exc_lme", key="exc_lme", label_visibility="collapsed")

    # === ULCM ===
    col_nom, col_inc, col_exc = st.sidebar.columns([2, 1, 1])
    col_nom.markdown(
        "<p style='margin-bottom: 0; line-height: 1.2;'>ULCM<br><span style='font-size: 0.8rem; color: #888;'>MàJ : 19/01/2026</span></p>", 
        unsafe_allow_html=True
    )
    inc_ulcm = col_inc.checkbox("inc_ulcm", key="inc_ulcm", label_visibility="collapsed")
    exc_ulcm = col_exc.checkbox("exc_ulcm", key="exc_ulcm", label_visibility="collapsed")

    col_nom, col_inc, col_exc = st.sidebar.columns([2, 1, 1])
    col_nom.write("MSIS")
    inc_msis = col_inc.checkbox("inc_msis", key="inc_msis", label_visibility="collapsed")
    exc_msis = col_exc.checkbox("exc_msis", key="exc_msis", label_visibility="collapsed")

    col_nom, col_inc, col_exc = st.sidebar.columns([2, 1, 1])
    col_nom.write("LME (DGS)")
    inc_speclme = col_inc.checkbox("inc_speclme", key="inc_speclme", label_visibility="collapsed")
    exc_speclme = col_exc.checkbox("exc_speclme", key="exc_speclme", label_visibility="collapsed")

    # ==========================================
    # ZONE CONFIDENTIELLE (Allégée)
    # ==========================================
    st.sidebar.markdown("---")
    st.sidebar.write("**Listes Complémentaires :**")
    fichier_secret = st.sidebar.file_uploader("Glissez le fichier (Excel)", type=['xlsx', 'xls'])

    filtres_dynamiques_inc = {}
    filtres_dynamiques_exc = {}
    df_secret = None

    if fichier_secret is not None:
        df_secret = charger_liste_confidentielle(fichier_secret)
        if df_secret is not None:
            col_nom, col_inc, col_exc = st.sidebar.columns([2, 1, 1])
            col_nom.write(" ") 
            col_inc.write("✅")
            col_exc.write("❌")

            if df_secret['stock_strat'].any():
                col_nom, col_inc, col_exc = st.sidebar.columns([2, 1, 1])
                col_nom.write("Stock Strat")
                filtres_dynamiques_inc['stock_strat'] = col_inc.checkbox("inc_strat", key="inc_strat", label_visibility="collapsed")
                filtres_dynamiques_exc['stock_strat'] = col_exc.checkbox("exc_strat", key="exc_strat", label_visibility="collapsed")

            if df_secret['stock_tact'].any():
                col_nom, col_inc, col_exc = st.sidebar.columns([2, 1, 1])
                col_nom.write("Stock Tact")
                filtres_dynamiques_inc['stock_tact'] = col_inc.checkbox("inc_tact", key="inc_tact", label_visibility="collapsed")
                filtres_dynamiques_exc['stock_tact'] = col_exc.checkbox("exc_tact", key="exc_tact", label_visibility="collapsed")

            if df_secret['ssa'].any():
                col_nom, col_inc, col_exc = st.sidebar.columns([2, 1, 1])
                col_nom.write("SSA")
                filtres_dynamiques_inc['ssa'] = col_inc.checkbox("inc_ssa", key="inc_ssa", label_visibility="collapsed")
                filtres_dynamiques_exc['ssa'] = col_exc.checkbox("exc_ssa", key="exc_ssa", label_visibility="collapsed")
        else:
            st.sidebar.error("Erreur: Colonne 'ATC 5' introuvable.")

    # ==========================================
    # --- CONSTRUCTION DE LA REQUÊTE SQL ---
    # ==========================================
    sql = """
        SELECT DISTINCT m.cis, m.nom, m.titulaire, m.code_atc 
        FROM medicament m
        LEFT JOIN composition c ON m.cis = c.cis
        LEFT JOIN listes_publiques_add lpa ON m.code_atc = lpa.code_atc
        WHERE 1=1
    """
    params = {}

    if query_med:
        sql += " AND (m.nom ILIKE :q_med OR c.denomination_substance ILIKE :q_med)"
        params['q_med'] = f"%{query_med}%"

    if query_code:
        code_propre = query_code.strip()
        sql += " AND (m.cis::text ILIKE :q_code OR m.code_atc ILIKE :q_code)"
        params['q_code'] = f"%{code_propre}%"

    if query_lab:
        sql += " AND m.titulaire ILIKE :q_lab"
        params['q_lab'] = f"%{query_lab}%"

    if not pays_selectionnes:
        sql += " AND 1=0" 
    elif len(pays_selectionnes) < len(tous_les_pays):
        # ON CHANGE 'fabricant' par 'paysfabrication' et 'pays_propre' par 'pays'
        sql += " AND m.cis IN (SELECT DISTINCT cis FROM paysfabrication WHERE pays IN :pays_list)"
        params['pays_list'] = tuple(pays_selectionnes)

    # --- SQL Filtres Publics ---
    if inc_mitm: sql += " AND m.est_mitm = True"
    if exc_mitm: sql += " AND m.est_mitm IS NOT True"

    if inc_lme: sql += " AND m.est_lme = True"
    if exc_lme: sql += " AND m.est_lme IS NOT True"

    if inc_ulcm: sql += " AND m.est_ulcm = True"
    if exc_ulcm: sql += " AND m.est_ulcm IS NOT True"

    if inc_msis: sql += " AND lpa.est_msis = True"
    if exc_msis: sql += " AND lpa.est_msis IS NOT True"

    if inc_speclme: sql += " AND lpa.est_spec_lme = True"
    if exc_speclme: sql += " AND lpa.est_spec_lme IS NOT True"

    # --- SQL Filtres Secrets ---
    if df_secret is not None:
        atc_a_inclure = None
        atc_a_exclure = set()

        for cle_filtre, est_coche in filtres_dynamiques_inc.items():
            if est_coche:
                atc_de_cette_liste = set(df_secret[df_secret[cle_filtre] == True]['ATC'])
                if atc_a_inclure is None:
                    atc_a_inclure = atc_de_cette_liste
                else:
                    atc_a_inclure = atc_a_inclure.intersection(atc_de_cette_liste)

        for cle_filtre, est_coche in filtres_dynamiques_exc.items():
            if est_coche:
                atc_de_cette_liste = set(df_secret[df_secret[cle_filtre] == True]['ATC'])
                atc_a_exclure.update(atc_de_cette_liste)

        if atc_a_inclure is not None:
            if len(atc_a_inclure) == 0:
                sql += " AND 1=0" 
            else:
                sql += " AND m.code_atc IN :atc_secrets_inclus"
                params['atc_secrets_inclus'] = tuple(atc_a_inclure)

        if atc_a_exclure:
            sql += " AND m.code_atc NOT IN :atc_secrets_exclus"
            params['atc_secrets_exclus'] = tuple(atc_a_exclure)

    sql += " LIMIT 20000"

    results = get_data(sql, params)
    titre_recherche = " & ".join(filter(None, [query_med.upper(), query_code.upper(), query_lab.upper()]))

    return results, titre_recherche, pays_selectionnes, df_secret



def display_hierarchy(cis_list, search_term):
    st.subheader(f"Résultats pour : {search_term}")


    # 1. Filtre 
    col_f1, _ = st.columns([1, 2])
    with col_f1:
        alerte_only = st.toggle("Uniquement ruptures/tensions", value=False, key="hier_alerte")

    # 2. Récupération des données avec filtrage dynamique
    if alerte_only:
        # On filtre sur les codes statut 1 (Rupture) et 2 (Tension) via les libellés [cite: 118, 119, 122]
        sql = """
            SELECT DISTINCT m.cis, m.nom, m.forme_pharma, m.titulaire, c.dosage, c.denomination_substance
            FROM medicament m
            JOIN composition c ON m.cis = c.cis
            JOIN disponibilite d ON m.cis = d.cis
            WHERE m.cis IN :cis_list
              AND d.statut IN ('Rupture de stock', 'Tension d''approvisionnement')
        """
    else:
        sql = """
            SELECT DISTINCT m.cis, m.nom, m.forme_pharma, m.titulaire, c.dosage, c.denomination_substance
            FROM medicament m
            JOIN composition c ON m.cis = c.cis
            WHERE m.cis IN :cis_list
        """

    df = get_data(sql, {"cis_list": tuple(cis_list)})
    df = df.fillna("Non renseigné")

    # 1. Dictionnaire de traduction (Ce que voit l'utilisateur -> La colonne SQL)
    colonnes_dispos = {
        "Nom du médicament": "nom",
        "Laboratoire Titulaire": "titulaire",
        "Substance": "denomination_substance",
        "Forme": "forme_pharma",
        "Dosage": "dosage"
    }

    # 2. Le sélecteur magique (L'ordre de sélection définit la hiérarchie)
    niveaux_choisis = st.multiselect(
        label="Construisez votre arborescence :",
        options=list(colonnes_dispos.keys()),
        label_visibility="collapsed"
    )

    if not niveaux_choisis:

        # S'il ne choisit rien, on affiche juste un tableau plat
        st.dataframe(df[['nom', 'titulaire', 'denomination_substance', 'dosage', 'forme_pharma']], hide_index=True)
        return

    # On traduit les choix en vrais noms de colonnes Pandas
    colonnes_groupement = [colonnes_dispos[n] for n in niveaux_choisis]

    # 3. La fonction récursive pour construire l'arbre à l'infini
    def construire_noeuds(sous_df, colonnes_restantes, profondeur=0):
        # Condition d'arrêt : on a épuisé tous les niveaux de filtre
        if len(colonnes_restantes) == 0:
            # On affiche les résultats restants dans un tableau
            # On cache les colonnes qui ont déjà servi de "titre" de dossier pour ne pas faire doublon
            cols_a_afficher = ['nom', 'titulaire', 'denomination_substance', 'dosage', 'forme_pharma']
            cols_a_afficher = [c for c in cols_a_afficher if c not in colonnes_groupement]

            # On s'assure que le 'nom' est toujours là, SAUF si on a groupé par le nom
            if 'nom' not in cols_a_afficher and 'nom' not in colonnes_groupement:
                cols_a_afficher.insert(0, 'nom')

            st.table(sous_df[cols_a_afficher].rename(columns={
                'nom': 'Dénomination', 'titulaire': 'Laboratoire', 
                'denomination_substance': 'Substance', 'forme_pharma': 'Forme'
            }).drop_duplicates())
            return

        # On prend la première colonne de la liste pour faire le niveau actuel
        col_actuelle = colonnes_restantes[0]
        # On retrouve le nom pour l'affichage
        nom_affichage = [k for k, v in colonnes_dispos.items() if v == col_actuelle][0]

        # On boucle sur chaque groupe Pandas
        for valeur, groupe in sous_df.groupby(col_actuelle):
            if profondeur == 0:
                # Le Niveau 1 (Racine) : Un gros bloc info bien visible
                st.info(f" **{nom_affichage} :** {valeur}")
                # On relance la fonction pour le niveau d'en dessous (récursivité)
                construire_noeuds(groupe, colonnes_restantes[1:], profondeur + 1)
            else:
                # Les Niveaux suivants : Des expanders (menus déroulants)
                with st.expander(f"🔹 {nom_affichage} : {valeur}"):
                    construire_noeuds(groupe, colonnes_restantes[1:], profondeur + 1)

    # 4. On lance la construction de l'arbre
    construire_noeuds(df, colonnes_groupement)

def map_section(cis_list, pays_selectionnes):
    st.subheader("Cartographie mondiale de la production")

    # 1. Filtres (Toggle + Boutons de choix pour la carte)
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        alerte_only = st.toggle("Uniquement les ruptures/tensions", value=False)
    with col_f2:
        # Le sélecteur magique : il ne charge qu'une seule carte à la fois !
        vue_carte = st.radio(
            "Mode d'affichage :", 
            ["Vue détaillée (1 point = 1 médicament)", "Vue globale (1 point = 1 site unique)"], 
            horizontal=True
        )

    # Pour pointer sur les anciennes adresses issu de la notice du médicaments :
    # # 2. Requête SQL Dynamique et Optimisée
    # if alerte_only:
    #     sql_fab = """
    #         SELECT f.latitude, f.longitude, f.adresse_complete, f.cis, f.pays_propre, m.nom, d.statut as alerte_statut
    #         FROM fabricant f
    #         JOIN medicament m ON f.cis = m.cis
    #         JOIN disponibilite d ON f.cis = d.cis
    #         WHERE f.cis IN :cis_list AND f.latitude IS NOT NULL
    #           AND d.statut IN ('Rupture de stock', 'Tension d''approvisionnement')
    #     """
    # else:
    #     sql_fab = """
    #         SELECT f.latitude, f.longitude, f.adresse_complete, f.cis, f.pays_propre, m.nom, NULL as alerte_statut
    #         FROM fabricant f
    #         JOIN medicament m ON f.cis = m.cis
    #         WHERE f.cis IN :cis_list AND f.latitude IS NOT NULL
    #     """

    # params = {"cis_list": tuple(cis_list)}
    # if pays_selectionnes:
    #     sql_fab += " AND f.pays_propre IN :pays_list"
    #     params['pays_list'] = tuple(pays_selectionnes)
    # 2. Requête SQL Dynamique (Pointant sur la nouvelle table paysfabrication)
    if alerte_only:
        sql_fab = """
            SELECT f.latitude, f.longitude, f.pays, f.cis, m.nom, d.statut as alerte_statut
            FROM paysfabrication f
            JOIN medicament m ON f.cis = m.cis
            JOIN disponibilite d ON f.cis = d.cis
            WHERE f.cis IN :cis_list AND f.latitude IS NOT NULL
              AND d.statut IN ('Rupture de stock', 'Tension d''approvisionnement')
        """
    else:
        sql_fab = """
            SELECT f.latitude, f.longitude, f.pays, f.cis, m.nom, NULL as alerte_statut
            FROM paysfabrication f
            JOIN medicament m ON f.cis = m.cis
            WHERE f.cis IN :cis_list AND f.latitude IS NOT NULL
        """

    params = {"cis_list": tuple(cis_list)}
    if pays_selectionnes:
        sql_fab += " AND f.pays IN :pays_list" # Changement de pays_propre vers pays
        params['pays_list'] = tuple(pays_selectionnes)

    df_fab = get_data(sql_fab, params)

    if not df_fab.empty:
        col1, col2 = st.columns([4, 1]) 

        with col1:
            m = folium.Map(location=[46, 2], zoom_start=3, tiles="CartoDB positron")

           # --- LOGIQUE DE BASCULEMENT ---
           # Pareil pour le pointage sur les anciennes adresses :
            # if vue_carte == "Vue globale (1 point = 1 site unique)":

            #     # On groupe UNIQUEMENT par les coordonnées GPS exactes !
            #     df_groupe = df_fab.groupby(['latitude', 'longitude']).agg(
            #         # Pour l'adresse, on prend juste la première trouvée à ces coordonnées ('first')
            #         adresse_complete=('adresse_complete', 'first'),
            #         # On compte les vrais médicaments uniques
            #         nb_meds=('cis', 'nunique'), 
            #         # On vérifie s'il y a une alerte
            #         a_alerte=('alerte_statut', lambda x: any(pd.notna(x))) 
            #     ).reset_index()

            #     def format_info_site(row):
            #         base = f"<b>Usine:</b> {row['adresse_complete']}<br><b>Médicaments produits ici:</b> {row['nb_meds']}"
            #         if row['a_alerte']:
            #             base += "<br><b style='color:red;'>Contient des ruptures/tensions</b>"
            #         return base
            if vue_carte == "Vue globale (1 point = 1 site unique)":
                # On groupe par Pays pour avoir un seul point central par pays
                df_groupe = df_fab.groupby(['latitude', 'longitude', 'pays']).agg(
                    nb_meds=('cis', 'nunique'), 
                    a_alerte=('alerte_statut', lambda x: any(pd.notna(x))) 
                ).reset_index()

                def format_info_site(row):
                    base = f"<b>Pays:</b> {row['pays']}<br><b>Médicaments produits ici:</b> {row['nb_meds']}"
                    if row['a_alerte']:
                        base += "<br><b style='color:red;'>⚠️ Contient des ruptures/tensions</b>"
                    return base

                df_groupe['info'] = df_groupe.apply(format_info_site, axis=1)
                data_points = df_groupe[['latitude', 'longitude', 'info']].values.tolist()

            else:
                # Pareil pour l'ancien pointage :
                # # --- ANCIENNE LOGIQUE : TOUT AFFICHER ---
                # def format_info(row):
                #     base = f"<b>Médicament:</b> {row['nom']}<br><b>Usine:</b> {row['adresse_complete']}"
                #     if row['alerte_statut']:
                #         color = "red" if "Rupture" in row['alerte_statut'] else "orange"
                #         base += f"<br><b style='color:{color};'>Statut: {row['alerte_statut']}</b>"
                #     return base

                def format_info(row):
                    base = f"<b>Médicament:</b> {row['nom']}<br><b>Pays de production:</b> {row['pays']}"
                    if row['alerte_statut']:
                        color = "red" if "Rupture" in row['alerte_statut'] else "orange"
                        base += f"<br><b style='color:{color};'>Statut: {row['alerte_statut']}</b>"
                    return base

                df_fab['info'] = df_fab.apply(format_info, axis=1)
                data_points = df_fab[['latitude', 'longitude', 'info']].values.tolist()

            # Ajout des points sur la carte
            callback = """
                function (row) {
                    var marker = L.marker(new L.LatLng(row[0], row[1]));
                    marker.bindPopup(row[2]);
                    return marker;
                };
            """
            FastMarkerCluster(data=data_points, callback=callback).add_to(m)
            st_folium(m, height=600, use_container_width=True, key="map_fast")

        with col2:
            # J'ai corrigé "Total Usines" : avant il comptait les lignes, maintenant il compte les vraies usines uniques !
            st.metric("Total Pays", df_fab['pays'].nunique())
            st.metric("Médicaments", df_fab['cis'].nunique())
    else:
        st.warning("Aucune donnée disponible pour ces critères.")

def export_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
    return output.getvalue()

def download_section(cis_list, df_secret):
    if st.button("Exporter en Excel"):

        sql = """
            SELECT 
                m.cis AS "Code CIS",
                m.nom AS "Dénomination",
                m.forme_pharma AS "Forme Pharmaceutique",
                m.titulaire AS "Titulaire",
                m.code_atc AS "Code ATC",
                m.est_mitm,
                m.est_lme,
                m.est_ulcm,
                COALESCE(lpa.est_msis, FALSE) AS est_msis,
                COALESCE(lpa.est_spec_lme, FALSE) AS est_spec_lme,
                comp.composants AS "Substances Actives",
                fab.usines AS "Sites de Production",
                COALESCE(dispo.statut_dispo, 'Disponible') AS "État de Disponibilité"
            FROM medicament m
            LEFT JOIN listes_publiques_add lpa ON m.code_atc = lpa.code_atc
            LEFT JOIN (
                SELECT cis, STRING_AGG(DISTINCT denomination_substance, ' + ') AS composants
                FROM composition
                GROUP BY cis
            ) comp ON m.cis = comp.cis
            LEFT JOIN (
                SELECT cis, STRING_AGG(DISTINCT pays, ' | ') AS usines
                FROM paysfabrication
                GROUP BY cis
            ) fab ON m.cis = fab.cis
            LEFT JOIN (
                SELECT cis, STRING_AGG(DISTINCT statut, ' / ') AS statut_dispo
                FROM disponibilite
                GROUP BY cis
            ) dispo ON m.cis = dispo.cis
            WHERE m.cis IN :cis_list
        """

        with st.spinner("Génération du fichier Excel"):
            final_df = get_data(sql, {"cis_list": tuple(cis_list)})

            final_df['Liste MITM'] = final_df['est_mitm'].apply(lambda x: "X" if x == True else "")
            final_df['Liste LME (OMS)'] = final_df['est_lme'].apply(lambda x: "X" if x == True else "")
            final_df['Liste ULCM'] = final_df['est_ulcm'].apply(lambda x: "X" if x == True else "")
            final_df['Liste MSIS'] = final_df['est_msis'].apply(lambda x: "X" if x == True else "")
            final_df['Spécialités LME (DGS)'] = final_df['est_spec_lme'].apply(lambda x: "X" if x == True else "")

            final_df = final_df.drop(columns=['est_mitm', 'est_lme', 'est_ulcm', 'est_msis', 'est_spec_lme'])

            if df_secret is not None and not df_secret.empty:
                final_df = pd.merge(final_df, df_secret, left_on='Code ATC', right_on='ATC', how='left')
                colonnes_secretes_mapping = {
                    'stock_strat': 'Stock Stratégique',
                    'stock_tact': 'Stock Tactique',
                    'ssa': 'Liste SSA'
                }
                for col_brute, nom_propre in colonnes_secretes_mapping.items():
                    if col_brute in final_df.columns:
                        final_df[nom_propre] = final_df[col_brute].apply(lambda x: "X" if x == True else "")
                        final_df = final_df.drop(columns=[col_brute])
                if 'ATC' in final_df.columns:
                    final_df = final_df.drop(columns=['ATC'])

            final_df = final_df.fillna("Non renseigné")
            excel_data = export_excel(final_df)

            st.download_button(
                label="Télécharger", 
                data=excel_data, 
                file_name="rapport_resilience_sante.xlsx", 
                mime="application/vnd.ms-excel"
            )

@st.cache_data
def charger_liste_confidentielle(fichier_upload):
    """
    Analyse ultra-robuste d'un Excel complexe (fusion de cellules, doubles en-têtes).
    Cherche les mots-clés directement dans les cases, sans se soucier de la ligne d'en-tête.
    """
    try:
        # 1. On lit tout le fichier SANS définir de ligne d'en-tête (header=None)
        # Comme ça, Pandas ne fusionne rien et lit chaque case individuellement
        df = pd.read_excel(fichier_upload, header=None, dtype=str)

        # 2. Le dictionnaire de nos cibles (Allégé)
        col_atc = None
        mapping_cibles = {
            'STOCK STRATEGIQUE': 'stock_strat',
            'STOCK TACTIQUE': 'stock_tact',
            'SSA': 'ssa'
        }

        # On va stocker le numéro de la colonne (0, 1, 2...) pour chaque mot clé
        col_indices = {k: None for k in mapping_cibles.keys()}

        # 3. LE RADAR : On scanne les 20 premières lignes et toutes les colonnes
        for i in range(min(20, len(df))):
            for j in range(len(df.columns)):
                val_brute = df.iloc[i, j]

                if pd.isna(val_brute):
                    continue

                # On nettoie la case : majuscules, et on enlève les espaces invisibles !
                val = str(val_brute).upper().strip()

                if 'ATC 5' in val or val == 'ATC5':
                    col_atc = j

                for mot_cle in mapping_cibles.keys():
                    if mot_cle in val:
                        col_indices[mot_cle] = j

        # Si on n'a pas trouvé la colonne ATC, on bloque
        if col_atc is None:
            return None

        # On regarde uniquement la colonne ATC. Si la case fait 7 caractères, c'est un médicament.
        # Ça élimine automatiquement les titres, les lignes vides, et les fusions
        df['ATC_CLEAN'] = df[col_atc].astype(str).str.strip()
        df_propre = df[df['ATC_CLEAN'].str.len() == 7].copy()

        # 5. Fonction de détection d'activation
        def est_actif(val):
            if pd.isna(val): return False
            v = str(val).strip().upper()
            # Accepte X, OUI, 1, ou tout texte qui n'est pas "NON" ou "0"
            return v in ['X', 'OUI', 'VRAI', '1', 'YES', 'TRUE'] or (v != '' and v != 'NON' and v != 'FAUX' and v != '0' and v != 'NAN')

        # 6. Assemblage du résultat final
        resultats = {'ATC': df_propre['ATC_CLEAN'].tolist()}

        for mot_cle, cle_dict in mapping_cibles.items():
            idx = col_indices[mot_cle]
            if idx is not None:

                resultats[cle_dict] = df_propre[idx].apply(est_actif).tolist()
            else:
                resultats[cle_dict] = [False] * len(df_propre)

        return pd.DataFrame(resultats)

    except Exception as e:
        st.error(f"Erreur de lecture : {e}")
        return None
# Pour les code ATC

TRAD_ATC_L1 = {
    'A': 'Système digestif', 
    'B': 'Sang et organes hématopoïétiques',
    'C': 'Système cardiovasculaire', 
    'D': 'Dermatologie',
    'G': 'Système urogénital', 
    'H': 'Hormones systémiques',
    'J': 'Anti-infectieux (Antibiotiques)', 
    'L': 'Antinéoplasiques (Cancer)',
    'M': 'Système musculo-squelettique', 
    'N': 'Système nerveux',
    'P': 'Antiparasitaires', 
    'R': 'Système respiratoire',
    'S': 'Organes sensoriels', 
    'V': 'Divers'
}

TRAD_ATC_L2 = {
    # A - Système digestif
    'A01': 'Stomatologie', 'A02': 'Acidité', 'A03': 'Gastro-intestinaux', 'A04': 'Antiémétiques', 'A05': 'Biliaire/Hépatique', 'A06': 'Laxatifs', 'A07': 'Antidiarrhéiques', 'A08': 'Antiobésité', 'A09': 'Digestifs', 'A10': 'Antidiabétiques', 'A11': 'Vitamines', 'A12': 'Minéraux',
    # B - Sang
    'B01': 'Antithrombotiques', 'B02': 'Antihémorragiques', 'B03': 'Antianémiques', 'B05': 'Substituts du sang',
    # C - Cardiovasculaire
    'C01': 'Thérapie cardiaque', 'C02': 'Antihypertenseurs', 'C03': 'Diurétiques', 'C04': 'Vasodilatateurs', 'C05': 'Vasoprotecteurs', 'C07': 'Bêtabloquants', 'C08': 'Inhibiteurs calciques', 'C09': 'Médicaments SRAA', 'C10': 'Hypolipidémiants',
    # D - Dermatologie
    'D01': 'Antifongiques', 'D02': 'Émollients', 'D05': 'Antipsoriasiques', 'D06': 'Antibiotiques topiques', 'D07': 'Corticoïdes', 'D08': 'Antiseptiques', 'D10': 'Antiacnéiques',
    # G - Système urogénital
    'G01': 'Anti-infectieux gynéco', 'G02': 'Autres gynéco', 'G03': 'Hormones sexuelles', 'G04': 'Urologiques',
    # H - Hormones
    'H01': 'Hypophysaires', 'H02': 'Corticoïdes systémiques', 'H03': 'Thyroïde', 'H04': 'Hormones pancréatiques', 'H05': 'Calcium',
    # J - Anti-infectieux
    'J01': 'Antibactériens (Antibiotiques)', 'J02': 'Antimycotiques', 'J04': 'Antimycobactériens', 'J05': 'Antiviraux', 'J06': 'Sérums/Immunoglobulines', 'J07': 'Vaccins',
    # L - Cancer / Immunité
    'L01': 'Antinéoplasiques', 'L02': 'Thérapie endocrine', 'L03': 'Immunostimulants', 'L04': 'Immunosuppresseurs',
    # M - Muscles & Os
    'M01': 'Anti-inflammatoires', 'M02': 'Topiques articulaires', 'M03': 'Myorelaxants', 'M04': 'Antigoutteux', 'M05': 'Traitement des os',
    # N - Système Nerveux
    'N01': 'Anesthésiques', 'N02': 'Analgésiques', 'N03': 'Antiépileptiques', 'N04': 'Antiparkinsoniens', 'N05': 'Psycholeptiques', 'N06': 'Psychoanaleptiques',
    # P - Parasites
    'P01': 'Antiprotozoaires', 'P02': 'Anthelminthiques', 'P03': 'Ectoparasiticides',
    # R - Respiratoire
    'R01': 'Préparations nasales', 'R02': 'Gorge', 'R03': 'Antiasthmatiques', 'R05': 'Toux et rhume', 'R06': 'Antihistaminiques',
    # S - Sensoriels (Yeux/Oreilles)
    'S01': 'Ophtalmologie', 'S02': 'Otologie',
    # V - Divers
    'V03': 'Traitements divers', 'V04': 'Diagnostiques', 'V07': 'Non thérapeutiques', 'V08': 'Produits de contraste'
}

@st.cache_data
def get_stats_aggregées(cis_list_tuple):
    if not cis_list_tuple:
        return pd.DataFrame() 

    sql_matrice = """
        SELECT 
            SUBSTRING(m.code_atc, 1, 1) as atc_code,
            SUBSTRING(m.code_atc, 1, 3) as atc_l2,
            f.pays as pays,
            m.voies_admin as voies_admin,  -- AJOUTÉ ICI
            COUNT(*) as nb_sites
        FROM medicament m
        JOIN paysfabrication f ON m.cis = f.cis
        WHERE m.cis IN :cis_list
        GROUP BY 1, 2, 3, 4
    """
    df_m = get_data(sql_matrice, {"cis_list": cis_list_tuple})
    return df_m

def get_stats_penuries_detaillees(cis_list_tuple):
    if not cis_list_tuple:
        return pd.DataFrame()

    sql = """
        SELECT 
            f.pays as pays, -- CHANGÉ ICI
            SUBSTRING(m.code_atc, 1, 1) as atc_code,
            STRING_AGG(DISTINCT '(' || d.statut || ') ' || COALESCE(m.nom, 'Inconnu'), '<br>• ') as detail_complet,
            COUNT(DISTINCT m.cis) as nb_total_alertes
        FROM medicament m
        JOIN disponibilite d ON m.cis = d.cis
        JOIN paysfabrication f ON m.cis = f.cis -- CHANGÉ ICI
        WHERE m.cis IN :cis_list 
          AND d.statut IN ('Rupture de stock', 'Tension d''approvisionnement')
        GROUP BY 1, 2
    """
    return get_data(sql, {"cis_list": cis_list_tuple})

def get_total_unique_atc(cis_list_tuple):
    if not cis_list_tuple:
        return 0
    # On compte désormais les codes ATC uniques dans la table medicament
    sql = """
        SELECT COUNT(DISTINCT code_atc) 
        FROM medicament 
        WHERE cis IN :cis_list AND code_atc IS NOT NULL
    """
    df = get_data(sql, {"cis_list": cis_list_tuple})
    return int(df.iloc[0, 0])

def get_stats_labo_atc(cis_list_tuple):
    if not cis_list_tuple:
        return pd.DataFrame()

    # On utilise un LEFT JOIN pour ne pas perdre un médicament s'il n'a pas de composition détaillée
    sql = """
        SELECT 
            m.titulaire AS "Laboratoire Titulaire",
            COUNT(DISTINCT m.code_atc) AS "Nombre d'ATC uniques",
            STRING_AGG(DISTINCT m.code_atc, ' | ') AS "Liste des codes ATC",
            STRING_AGG(DISTINCT c.denomination_substance, ' | ') AS "Liste des DCI (indicatif)"
        FROM medicament m
        LEFT JOIN composition c ON m.cis = c.cis
        WHERE m.cis IN :cis_list AND m.code_atc IS NOT NULL
        GROUP BY m.titulaire
        ORDER BY "Nombre d'ATC uniques" DESC
    """
    return get_data(sql, {"cis_list": cis_list_tuple})

# --- NOUVELLE FONCTION POUR LE CLASSEMENT PAR PAYS ---
def get_stats_pays_atc(cis_list_tuple):
    if not cis_list_tuple:
        return pd.DataFrame()

    sql = """
        SELECT 
            f.pays AS "Pays de fabrication",
            COUNT(DISTINCT m.code_atc) AS "Nombre d'ATC uniques",
            STRING_AGG(DISTINCT m.code_atc, ' | ') AS "Liste des codes ATC",
            STRING_AGG(DISTINCT c.denomination_substance, ' | ') AS "Liste des DCI (indicatif)"
        FROM medicament m
        JOIN paysfabrication f ON m.cis = f.cis
        LEFT JOIN composition c ON m.cis = c.cis
        WHERE m.cis IN :cis_list AND m.code_atc IS NOT NULL
        GROUP BY f.pays
        ORDER BY "Nombre d'ATC uniques" DESC
    """
    return get_data(sql, {"cis_list": cis_list_tuple})

# --- FONCTION POUR LE CLASSEMENT DES DEPENDANCES HORS EUROPE ---
def get_stats_pays_hors_eu_exclusifs(cis_list_tuple):
    if not cis_list_tuple:
        return pd.DataFrame()

    # Liste des codes pays considérés comme Européens (continent + UK + Suisse)
    # Basée sur les codes de ton dictionnaire TRADUCTION_PAYS
    pays_europe = (
        'Autriche', 'Belgique', 'Bulgarie', 'Suisse', 'Chypre', 'République Tchèque', 
        'Allemagne', 'Danemark', 'Estonie', 'Espagne', 'Finlande', 'France', 
        'Royaume-Uni', 'Grèce', 'Croatie', 'Hongrie', 'Irlande', 'Islande', 
        'Italie', 'Lituanie', 'Lettonie', 'Monaco', 'Malte', 'Pays-Bas', 
        'Norvège', 'Pologne', 'Portugal', 'Roumanie', 'Suède', 'Slovénie', 'Slovaquie'
    )

    sql = """
        WITH atc_europe AS (
            -- 1. On liste tous les ATC produits dans au moins un pays européen
            SELECT DISTINCT m.code_atc
            FROM medicament m
            JOIN paysfabrication f ON m.cis = f.cis
            WHERE m.cis IN :cis_list 
              AND m.code_atc IS NOT NULL
              AND f.pays IN :pays_eu
        )
        -- 2. On prend les pays hors Europe et uniquement les ATC absents de la liste ci-dessus
        SELECT 
            f.pays AS "Pays de fabrication",
            COUNT(DISTINCT m.code_atc) AS "Nombre d'ATC uniques",
            STRING_AGG(DISTINCT m.code_atc, ' | ') AS "Liste des codes ATC",
            STRING_AGG(DISTINCT c.denomination_substance, ' | ') AS "Liste des DCI (indicatif)"
        FROM medicament m
        JOIN paysfabrication f ON m.cis = f.cis
        LEFT JOIN composition c ON m.cis = c.cis
        WHERE m.cis IN :cis_list 
          AND m.code_atc IS NOT NULL
          AND f.pays NOT IN :pays_eu
          AND m.code_atc NOT IN (SELECT code_atc FROM atc_europe)
        GROUP BY f.pays
        ORDER BY "Nombre d'ATC uniques" DESC
    """
    return get_data(sql, {"cis_list": cis_list_tuple, "pays_eu": pays_europe})

def stats_section(results):
    # Transformation pour le cache
    cis_tuple = tuple(results['cis'].tolist())

    # Appel des données pré-calculées
    with st.spinner("Analyse des données en cours"):
        df_matrice = get_stats_aggregées(cis_tuple)

    if df_matrice.empty:
        st.warning("Pas assez de données pour générer les statistiques.")
        return

    # --- PRÉPARATION & NETTOYAGE ---
    # Traduction ATC Niveau 1
    df_matrice['Famille'] = df_matrice['atc_code'].map(TRAD_ATC_L1).fillna("Autres")

    # Traduction ATC Niveau 2 
    df_matrice['Sous-famille'] = df_matrice['atc_l2'].map(TRAD_ATC_L2).fillna(df_matrice['atc_l2'])

    # Traduction Pays
    df_matrice['Nom Pays'] = df_matrice['pays'].map(TRADUCTION_PAYS).fillna(df_matrice['pays'])

    # On force tout en texte et on traque le moindre espace vide ou NaN
    for col in ['Famille', 'Sous-famille', 'Nom Pays']:
        df_matrice[col] = df_matrice[col].fillna("Inconnu").astype(str)
        # On remplace les valeurs qui "ressemblent" à du vide par "Inconnu"
        df_matrice[col] = df_matrice[col].replace({'': 'Inconnu', 'nan': 'Inconnu', 'None': 'Inconnu'})

    # On enlève les pays inconnus pour la propreté visuelle (optionnel)
    df_matrice = df_matrice[df_matrice['Nom Pays'] != "Inconnu"]

    # --- 1. LES KPI CARDS (Stats simples) ---
    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Médicaments uniques", len(results['cis'].unique()))
    with c2:
        st.metric("Laboratoires Titulaires", len(results['titulaire'].unique()))
    with c3:
        st.metric("Nombre de Pays", len(df_matrice['Nom Pays'].unique()))

    st.write("---")

    # --- 2. GRAPHIQUE DE DÉPENDANCE (Treemap) ---
    st.write("**Concentration de la production par Famille et Pays**")

    vue_choisie = st.radio(
        "Choisissez l'analyse :",
        options=[
            "Famille > Pays > Sous-catégorie", 
            "Famille > Sous-catégorie > Pays"
        ],
        horizontal=True
    )

    # On adapte le chemin (path) et la profondeur selon le choix de l'utilisateur
    if vue_choisie == "Famille > Pays > Sous-catégorie":
        chemin_treemap = [px.Constant("Toutes les familles"), 'Famille', 'Nom Pays', 'Sous-famille']
        # MASQUAGE : Affiche (1.Racine -> 2.Famille -> 3.Pays) et CACHE la sous-famille
        profondeur = 3
    else:
        # L'ordre inversé pour la vue détail
        chemin_treemap = [px.Constant("Toutes les familles"), 'Famille', 'Sous-famille', 'Nom Pays']
        profondeur = 3

    fig_tree = px.treemap(
        df_matrice,
        path=chemin_treemap, 
        values='nb_sites',
        color='nb_sites',
        color_continuous_scale='Blues',
        template='plotly_white'
    )

    fig_tree.update_traces(maxdepth=profondeur)
    fig_tree.update_layout(margin=dict(t=30, l=10, r=10, b=10), height=550)

    st.plotly_chart(fig_tree, use_container_width=True)

    st.write("---")

    # --- 3. GRAPHIQUE PAYS (Bar Chart épuré avec couleurs Injectables) ---
    st.write("**Répartition du nombre de spécialités (CIS) par Pays et Voie d'administration**")

    # --- A. Classification Injectable / Non injectable ---
    LISTE_NON_INJECTABLES = [
        "auriculaire", "auriculaire;gingivale;nasale;voie buccale autre", "buccogingivale",
        "cutanée", "cutanée;inhalée", "cutanée;nasale", "cutanée;orale;sublinguale",
        "cutanée;transdermique", "dentaire", "dentaire;gingivale", "endocervicale;intra-utérine",
        "endotrachéobronchique", "épilésionnelle", "gastrique;orale", "gastro-entérale;orale",
        "gingivale", "gingivale;voie buccale autre", "inhalée", "intestinale", "intra-utérine",
        "intracervicale", "intradermique", "intravésicale", "intravésicale;rectale;urétrale",
        "laryngopharyngée;voie buccale autre", "nasale", "nasale;orale", "ophtalmique", "orale",
        "orale;rectale", "orale;sublinguale", "orale;vaginale", "oropharyngée", "rectale",
        "sublinguale", "transdermique", "urétrale", "vaginale", "voie buccale autre"
    ]

    def classer_injectable(voie):
        if pd.isna(voie) or str(voie).strip() == "":
            return "Inconnu"
        # On met en minuscules et on écrase les espaces autour des ";"
        voie_propre = str(voie).replace(" ; ", ";").strip().lower()
        if voie_propre in LISTE_NON_INJECTABLES:
            return "Non injectable"
        else:
            return "Injectable"

    df_matrice['Type Injection'] = df_matrice['voies_admin'].apply(classer_injectable)

    # --- B. Préparation des données pour le graphique ---
    # On regroupe par Pays ET par Type Injection
    df_pays_total = df_matrice.groupby(['Nom Pays', 'Type Injection'])['nb_sites'].sum().reset_index()

    # Astuce : On calcule le total global par pays pour les trier correctement sur le graphique
    totaux_par_pays = df_pays_total.groupby('Nom Pays')['nb_sites'].sum().sort_values(ascending=False)
    ordre_pays = totaux_par_pays.index

    # Calcul du total absolu pour les pourcentages
    total_sites_global = totaux_par_pays.sum()

    if not df_pays_total.empty:
        fig_bar = px.bar(
            df_pays_total, 
            x='Nom Pays', 
            y='nb_sites',
            color='Type Injection', # <-- C'est ça qui sépare la barre en deux !
            text='nb_sites',
            category_orders={"Nom Pays": ordre_pays}, # Maintient l'ordre du plus grand au plus petit pays
            labels={'nb_sites': 'Nombre de sites', 'Nom Pays': 'Pays'},
            template='plotly_white',
            color_discrete_map={
                "Injectable": "#E74C3C",        # Rouge
                "Non injectable": "#3498DB",    # Bleu
                "Inconnu": "#BDC3C7"            # Gris clair
            }
        )

        fig_bar.update_traces(
            hovertemplate="<b>%{x}</b><br>%{data.name}: %{y}<extra></extra>",
            textposition='inside' # Garde les chiffres à l'intérieur de leur zone de couleur
        )

        fig_bar.update_layout(
            xaxis_title=None,
            yaxis_title=None,
            height=450,
            margin=dict(l=20, r=20, t=40, b=20),
            barmode='stack', # Empile les couleurs les unes sur les autres
            legend_title_text=""
        )

        # --- C. Ajout des pourcentages au-dessus des barres ---
        for pays, total_pays in totaux_par_pays.items():
            pourcentage = (total_pays / total_sites_global) * 100
            # On ajoute le texte juste au-dessus (y=total_pays)
            fig_bar.add_annotation(
                x=pays,
                y=total_pays,
                text=f"{pourcentage:.1f}%", # Format avec 1 chiffre après la virgule
                showarrow=False,
                yshift=10, # Décale le texte de 10 pixels vers le haut
                font=dict(size=11, color="black")
            )

        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Aucune donnée géographique disponible.")

   # --- GRAPH 2 : PÉNURIES (Blues & Filtré) ---
    # ==========================================
    st.write("---")
    st.write("**Ruptures & Tensions uniquement**")

    with st.spinner("Filtrage des alertes"):
        df_penuries = get_stats_penuries_detaillees(cis_tuple)

    if not df_penuries.empty:
        df_penuries['Famille'] = df_penuries['atc_code'].map(TRAD_ATC_L1).fillna("Autres")
        df_penuries['Nom Pays'] = df_penuries['pays'].map(TRADUCTION_PAYS).fillna(df_penuries['pays'])

        fig_penurie = px.treemap(
            df_penuries,
            path=[px.Constant("Toutes les familles"), 'Famille', 'Nom Pays'],
            values='nb_total_alertes',
            color='nb_total_alertes', # On colore par le NOMBRE (numérique), pas par le texte !
            color_continuous_scale='Blues',
            custom_data=['detail_complet'], 
            template='plotly_white'
        )

        fig_penurie.update_traces(
            hovertemplate="""
            <b>%{label}</b><br>
            Nombre total d'alertes : %{value}<br>
            <br><b>Détail des médicaments :</b><br>• %{customdata[0]}
            <extra></extra>""",
            textinfo="label+value"
        )

        fig_penurie.update_layout(margin=dict(t=30, l=10, r=10, b=10), height=600)
        st.plotly_chart(fig_penurie, use_container_width=True)

    # --- 4. TABLEAU : DIVERSITÉ PAR LABORATOIRE ---
    st.write("---")
    st.write("**Classement des Laboratoires par diversité du portefeuille (Codes ATC uniques)**")

    with st.spinner("Analyse du portefeuille par laboratoire..."):
        df_labo_atc = get_stats_labo_atc(cis_tuple)

        if not df_labo_atc.empty:
            # 1. Total global
            total_atc = get_total_unique_atc(cis_tuple)
            st.metric("Total des classes thérapeutiques (ATC uniques, tous laboratoires)", total_atc)

            # 2. Affichage du tableau
            st.dataframe(
                df_labo_atc, 
                hide_index=True, 
                use_container_width=True,
                column_config={
                    "Nombre d'ATC uniques": st.column_config.ProgressColumn(
                        "Nombre d'ATC uniques",
                        format="%d",
                        min_value=0,
                        max_value=int(df_labo_atc["Nombre d'ATC uniques"].max())
                    )
                }
            )
        else:
            st.info("Aucune donnée ATC disponible pour ces critères.")

    # --- 5. NOUVEAU TABLEAU : DIVERSITÉ PAR PAYS ---
    st.write("---")
    st.write("**Classement des Pays par diversité de fabrication (Codes ATC uniques)**")

    with st.spinner("Analyse de la production par pays..."):
        df_pays_atc = get_stats_pays_atc(cis_tuple)

        if not df_pays_atc.empty:
            # On applique la traduction des pays pour que l'affichage soit propre
            df_pays_atc['Pays de fabrication'] = df_pays_atc['Pays de fabrication'].map(TRADUCTION_PAYS).fillna(df_pays_atc['Pays de fabrication'])

            st.dataframe(
                df_pays_atc, 
                hide_index=True, 
                use_container_width=True,
                column_config={
                    "Nombre d'ATC uniques": st.column_config.ProgressColumn(
                        "Nombre d'ATC uniques",
                        format="%d",
                        min_value=0,
                        max_value=int(df_pays_atc["Nombre d'ATC uniques"].max())
                    )
                }
            )
        else:
            st.info("Aucune donnée de pays disponible pour ces critères.")

    # --- 6. NOUVEAU TABLEAU : DÉPENDANCE HORS EUROPE ---
    st.write("---")
    st.write("**Classement des Pays hors Europe par exclusivité de fabrication (ATC non produits en Europe)**")

    with st.spinner("Analyse"):
        df_hors_eu = get_stats_pays_hors_eu_exclusifs(cis_tuple)

        if not df_hors_eu.empty:
            # --- AJOUT ICI : Calcul du total d'ATC uniques hors Europe ---
            # Comme un même ATC exclusif peut être fabriqué dans plusieurs pays hors Europe (ex: Chine ET Inde),
            # on doit recompter les ATC uniques globaux à partir de la liste texte concaténée.
            tous_les_atc_hors_eu = set()
            for liste_atc in df_hors_eu["Liste des codes ATC"]:
                # On sépare la chaîne "A01A | B02C" en une vraie liste Python et on l'ajoute au set
                atc_individuels = [atc.strip() for atc in str(liste_atc).split('|')]
                tous_les_atc_hors_eu.update(atc_individuels)

            total_atc_hors_eu = len(tous_les_atc_hors_eu)

            # Affichage de la métrique bien visible
            st.metric(
                label="Total des classes thérapeutiques (ATC) produites exclusivement hors Europe", 
                value=total_atc_hors_eu
            )
            # -----------------------------------------------------------

            st.dataframe(
                df_hors_eu, 
                hide_index=True, 
                use_container_width=True,
                column_config={
                    "Nombre d'ATC uniques": st.column_config.ProgressColumn(
                        "Nombre d'ATC uniques",
                        format="%d",
                        min_value=0,
                        max_value=int(df_hors_eu["Nombre d'ATC uniques"].max())
                    )
                }
            )
        else:
            st.success("Tous les codes ATC de cette sélection ont au moins un site de production en Europe.")

def dci_section(cis_list, df_secret):
    st.subheader("Synthèse regroupée par ATC")

    sql = """
        SELECT 
            m.code_atc AS "Code ATC",
            STRING_AGG(DISTINCT c.denomination_substance, ' + ') AS "DCI",
            COUNT(DISTINCT m.cis) AS "Nb de déclinaisons (CIS)",
            STRING_AGG(DISTINCT m.nom, ' | ') AS "Spécialités concernées",
            STRING_AGG(DISTINCT m.titulaire, ' | ') AS "Laboratoires fabriquant",
            -- CHANGEMENT ICI : On utilise la nouvelle table paysfabrication
            STRING_AGG(DISTINCT f.pays, ' | ') AS "Pays de production", 
            STRING_AGG(DISTINCT d.statut, ' / ') AS "Alertes de disponibilité",
            BOOL_OR(m.est_mitm) AS est_mitm,
            BOOL_OR(m.est_lme) AS est_lme,
            BOOL_OR(m.est_ulcm) AS est_ulcm,
            BOOL_OR(lpa.est_msis) AS est_msis,
            BOOL_OR(lpa.est_spec_lme) AS est_spec_lme
        FROM medicament m
        LEFT JOIN composition c ON m.cis = c.cis
        -- CHANGEMENT ICI : Jointure sur la nouvelle table
        LEFT JOIN paysfabrication f ON m.cis = f.cis 
        LEFT JOIN disponibilite d ON m.cis = d.cis
        LEFT JOIN listes_publiques_add lpa ON m.code_atc = lpa.code_atc
        WHERE m.cis IN :cis_list AND m.code_atc IS NOT NULL
        GROUP BY m.code_atc
        ORDER BY m.code_atc
    """

    with st.spinner("Compression des données par DCI..."):
        df_dci = get_data(sql, {"cis_list": tuple(cis_list)})

        df_dci['Liste MITM'] = df_dci['est_mitm'].apply(lambda x: "X" if x == True else "")
        df_dci['Liste LME (OMS)'] = df_dci['est_lme'].apply(lambda x: "X" if x == True else "")
        df_dci['Liste ULCM'] = df_dci['est_ulcm'].apply(lambda x: "X" if x == True else "")
        df_dci['Liste MSIS'] = df_dci['est_msis'].apply(lambda x: "X" if x == True else "")
        df_dci['Spécialités LME (DGS)'] = df_dci['est_spec_lme'].apply(lambda x: "X" if x == True else "")

        df_dci = df_dci.drop(columns=['est_mitm', 'est_lme', 'est_ulcm', 'est_msis', 'est_spec_lme'])

        if df_secret is not None and not df_secret.empty:
            df_dci = pd.merge(df_dci, df_secret, left_on='Code ATC', right_on='ATC', how='left')
            colonnes_secretes_mapping = {
                'stock_strat': 'Stock Stratégique',
                'stock_tact': 'Stock Tactique',
                'ssa': 'Liste SSA'
            }
            for col_brute, nom_propre in colonnes_secretes_mapping.items():
                if col_brute in df_dci.columns:
                    df_dci[nom_propre] = df_dci[col_brute].apply(lambda x: "X" if x == True else "")
                    df_dci = df_dci.drop(columns=[col_brute])

            if 'ATC' in df_dci.columns:
                df_dci = df_dci.drop(columns=['ATC'])

        df_dci = df_dci.fillna("Non renseigné")

        st.dataframe(df_dci, hide_index=True, use_container_width=True)
        st.write("---")
        excel_data = export_excel(df_dci)
        st.download_button(
            label="Télécharger l'Excel", 
            data=excel_data, 
            file_name="synthese_dci_atc.xlsx", 
            mime="application/vnd.ms-excel"
        )

def main():
    injecter_css_pro()
    st.title("Base des médicaments")

    results, titre_recherche, pays_selectionnes, df_secret = search_section()

    if results is not None and not results.empty:
        cis_list = results['cis'].tolist()

        tab_h, tab_m, tab_s, tab_e, tab_dci = st.tabs(["Arborescence", "Carte Mondiale", "Statistiques", "Excel", "Synthèse DCI (ATC)"])

        with tab_h:
            display_hierarchy(cis_list, titre_recherche)

        with tab_m:
            map_section(cis_list, pays_selectionnes)

        with tab_s:
            stats_section(results)

        with tab_e: 
            download_section(cis_list, df_secret)

        with tab_dci:
            dci_section(cis_list, df_secret)

    elif titre_recherche:
        st.warning(f"Aucun résultat pour '{titre_recherche}'.")

if __name__ == "__main__":
    main()
