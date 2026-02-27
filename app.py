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
@st.cache_data
def get_liste_pays():
    """Récupère la liste alphabétique de tous les pays disponibles dans la base"""
    sql = "SELECT DISTINCT pays_propre FROM fabricant WHERE pays_propre IS NOT NULL ORDER BY pays_propre"
    df_pays = get_data(sql)
    return df_pays['pays_propre'].tolist()

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
    # En-têtes des colonnes (Le [2, 1, 1] règle la largeur : le nom prend 2 fois plus de place)
    col_nom, col_inc, col_exc = st.sidebar.columns([2, 1, 1])
    col_nom.write(" ") # Case vide pour aligner
    col_inc.write("✅")
    col_exc.write("❌")

    # Ligne MITM
    col_nom, col_inc, col_exc = st.sidebar.columns([2, 1, 1])
    col_nom.write("MITM")
    inc_mitm = col_inc.checkbox("inc_mitm", key="inc_mitm", label_visibility="collapsed")
    exc_mitm = col_exc.checkbox("exc_mitm", key="exc_mitm", label_visibility="collapsed")

    # Ligne LME
    col_nom, col_inc, col_exc = st.sidebar.columns([2, 1, 1])
    col_nom.write("LME de l'OMS")
    inc_lme = col_inc.checkbox("inc_lme", key="inc_lme", label_visibility="collapsed")
    exc_lme = col_exc.checkbox("exc_lme", key="exc_lme", label_visibility="collapsed")

    # Ligne ULCM
    col_nom, col_inc, col_exc = st.sidebar.columns([2, 1, 1])
    col_nom.write("ULCM")
    inc_ulcm = col_inc.checkbox("inc_ulcm", key="inc_ulcm", label_visibility="collapsed")
    exc_ulcm = col_exc.checkbox("exc_ulcm", key="exc_ulcm", label_visibility="collapsed")

    # ==========================================
    # ZONE CONFIDENTIELLE (2 Colonnes)
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
            # En-têtes
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

            if df_secret['msis'].any():
                col_nom, col_inc, col_exc = st.sidebar.columns([2, 1, 1])
                col_nom.write("MSIS")
                filtres_dynamiques_inc['msis'] = col_inc.checkbox("inc_msis", key="inc_msis", label_visibility="collapsed")
                filtres_dynamiques_exc['msis'] = col_exc.checkbox("exc_msis", key="exc_msis", label_visibility="collapsed")

            if df_secret['spec_lme'].any():
                col_nom, col_inc, col_exc = st.sidebar.columns([2, 1, 1])
                col_nom.write("LME (DGS)")
                filtres_dynamiques_inc['spec_lme'] = col_inc.checkbox("inc_speclme", key="inc_speclme", label_visibility="collapsed")
                filtres_dynamiques_exc['spec_lme'] = col_exc.checkbox("exc_speclme", key="exc_speclme", label_visibility="collapsed")

        else:
            st.sidebar.error("Erreur: Colonne 'ATC 5' introuvable.")

    # ==========================================
    # --- CONSTRUCTION DE LA REQUÊTE SQL ---
    # ==========================================
    sql = """
        SELECT DISTINCT m.cis, m.nom, m.titulaire, m.code_atc 
        FROM medicament m
        LEFT JOIN composition c ON m.cis = c.cis
        WHERE 1=1
    """
    params = {}

    if query_med:
        sql += " AND (m.nom ILIKE :q_med OR c.denomination_substance ILIKE :q_med)"
        params['q_med'] = f"%{query_med}%"

    if query_code:
        # On nettoie les espaces éventuels
        code_propre = query_code.strip()
        sql += " AND (m.cis ILIKE :q_code OR m.code_atc ILIKE :q_code)"
        params['q_code'] = f"%{code_propre}%"

    if query_lab:
        sql += " AND m.titulaire ILIKE :q_lab"
        params['q_lab'] = f"%{query_lab}%"

    # --- SQL Géographique ---
    if not pays_selectionnes:
        sql += " AND 1=0" 
    elif len(pays_selectionnes) < len(tous_les_pays):
        sql += " AND m.cis IN (SELECT DISTINCT cis FROM fabricant WHERE pays_propre IN :pays_list)"
        params['pays_list'] = tuple(pays_selectionnes)

    # --- SQL Filtres Publics ---
    if inc_mitm: sql += " AND m.est_mitm = True"
    if exc_mitm: sql += " AND m.est_mitm IS NOT True"

    if inc_lme: sql += " AND m.est_lme = True"
    if exc_lme: sql += " AND m.est_lme IS NOT True"

    if inc_ulcm: sql += " AND m.est_ulcm = True"
    if exc_ulcm: sql += " AND m.est_ulcm IS NOT True"

    # --- SQL Filtres Secrets ---
    if df_secret is not None:
        atc_a_inclure = None
        atc_a_exclure = set()

        # 1. On gère les cases cochées dans la colonne "Inclure"
        for cle_filtre, est_coche in filtres_dynamiques_inc.items():
            if est_coche:
                atc_de_cette_liste = set(df_secret[df_secret[cle_filtre] == True]['ATC'])
                if atc_a_inclure is None:
                    atc_a_inclure = atc_de_cette_liste
                else:
                    atc_a_inclure = atc_a_inclure.intersection(atc_de_cette_liste)

        # 2. On gère les cases cochées dans la colonne "Exclure"
        for cle_filtre, est_coche in filtres_dynamiques_exc.items():
            if est_coche:
                atc_de_cette_liste = set(df_secret[df_secret[cle_filtre] == True]['ATC'])
                atc_a_exclure.update(atc_de_cette_liste)

        # 3. On ajoute les conditions SQL
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

    # 1. Filtre Toggle
    col_f1, _ = st.columns([1, 2])
    with col_f1:
        alerte_only = st.toggle("Uniquement les ruptures/tensions", value=False)

    # 2. Requête SQL Dynamique et Optimisée
    if alerte_only:
        # Si activé : on fait un JOIN strict pour ne récupérer que les alertes
        sql_fab = """
            SELECT f.latitude, f.longitude, f.adresse_complete, f.cis, f.pays_propre, m.nom, d.statut as alerte_statut
            FROM fabricant f
            JOIN medicament m ON f.cis = m.cis
            JOIN disponibilite d ON f.cis = d.cis
            WHERE f.cis IN :cis_list AND f.latitude IS NOT NULL
              AND d.statut IN ('Rupture de stock', 'Tension d''approvisionnement')
        """
    else:
        # Si désactivé : requête simplifiée sans la table disponibilité (gain de vitesse)
        sql_fab = """
            SELECT f.latitude, f.longitude, f.adresse_complete, f.cis, f.pays_propre, m.nom, NULL as alerte_statut
            FROM fabricant f
            JOIN medicament m ON f.cis = m.cis
            WHERE f.cis IN :cis_list AND f.latitude IS NOT NULL
        """

    params = {"cis_list": tuple(cis_list)}
    if pays_selectionnes:
        sql_fab += " AND f.pays_propre IN :pays_list"
        params['pays_list'] = tuple(pays_selectionnes)

    df_fab = get_data(sql_fab, params)

    if not df_fab.empty:
        col1, col2 = st.columns([4, 1]) 

        with col1:
            m = folium.Map(location=[46, 2], zoom_start=3, tiles="CartoDB positron")

            def format_info(row):
                base = f"<b>Médicament:</b> {row['nom']}<br><b>Usine:</b> {row['adresse_complete']}"
                if row['alerte_statut']:
                    color = "red" if "Rupture" in row['alerte_statut'] else "orange"
                    base += f"<br><b style='color:{color};'>Statut: {row['alerte_statut']}</b>"
                return base

            df_fab['info'] = df_fab.apply(format_info, axis=1)
            data_points = df_fab[['latitude', 'longitude', 'info']].values.tolist()

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
            st.metric("Total Usines", len(df_fab))
            st.metric("Médicaments", len(df_fab['cis'].unique()))
            # Le bloc de calcul et de warning a été supprimé ici
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
                comp.composants AS "Substances Actives",
                fab.usines AS "Sites de Production",
                COALESCE(dispo.statut_dispo, 'Disponible') AS "État de Disponibilité"
            FROM medicament m

            -- Sous-requête 1 : Substances
            LEFT JOIN (
                SELECT cis, STRING_AGG(DISTINCT denomination_substance, ' + ') AS composants
                FROM composition
                GROUP BY cis
            ) comp ON m.cis = comp.cis

            -- Sous-requête 2 : Usines
            LEFT JOIN (
                SELECT cis, STRING_AGG(DISTINCT adresse_complete, ' | ') AS usines
                FROM fabricant
                GROUP BY cis
            ) fab ON m.cis = fab.cis

            -- Sous-requête 3 : Disponibilité (Les 4 statuts ANSM)
            LEFT JOIN (
                SELECT cis, STRING_AGG(DISTINCT statut, ' / ') AS statut_dispo
                FROM disponibilite
                GROUP BY cis
            ) dispo ON m.cis = dispo.cis

            WHERE m.cis IN :cis_list
        """

        with st.spinner("Génération du fichier Excel"):
            final_df = get_data(sql, {"cis_list": tuple(cis_list)})
            # --- 1. GESTION DES LISTES PUBLIQUES ---
            # On met un "X" si c'est vrai, sinon on laisse vide
            final_df['Liste MITM'] = final_df['est_mitm'].apply(lambda x: "X" if x == True else "")
            final_df['Liste LME (OMS)'] = final_df['est_lme'].apply(lambda x: "X" if x == True else "")
            final_df['Liste ULCM'] = final_df['est_ulcm'].apply(lambda x: "X" if x == True else "")

            # On supprime les colonnes brutes de la base de données pour faire propre
            final_df = final_df.drop(columns=['est_mitm', 'est_lme', 'est_ulcm'])

            # --- 2. GESTION DES LISTES CONFIDENTIELLES ---
            # Si un fichier Excel a été glissé dans l'application, df_secret n'est pas vide
            if df_secret is not None and not df_secret.empty:
                # Magie Pandas : on fusionne les deux tableaux en associant le Code ATC
                final_df = pd.merge(final_df, df_secret, left_on='Code ATC', right_on='ATC', how='left')

                # Dictionnaire de traduction (Nom dans le code -> Nom propre pour l'Excel)
                colonnes_secretes_mapping = {
                    'stock_strat': 'Stock Stratégique',
                    'stock_tact': 'Stock Tactique',
                    'ssa': 'Liste SSA',
                    'msis': 'Liste MSIS',
                    'spec_lme': 'Spécialités LME (DGS)'
                }

                # On boucle sur les colonnes secrètes pour mettre des "X"
                for col_brute, nom_propre in colonnes_secretes_mapping.items():
                    if col_brute in final_df.columns:
                        final_df[nom_propre] = final_df[col_brute].apply(lambda x: "X" if x == True else "")
                        # On supprime la colonne brute
                        final_df = final_df.drop(columns=[col_brute])

                # On nettoie la colonne ATC en double
                if 'ATC' in final_df.columns:
                    final_df = final_df.drop(columns=['ATC'])

            # Petit nettoyage final pour l'esthétique du fichier
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

        # 2. Le dictionnaire de nos cibles
        col_atc = None
        mapping_cibles = {
            'STOCK STRATEGIQUE': 'stock_strat',
            'STOCK TACTIQUE': 'stock_tact',
            'SSA': 'ssa',
            'MSIS': 'msis',
            'SPECIALITES LME': 'spec_lme'
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
    """Calcule les stats ATC (Niveaux 1 et 2) et Pays directement dans le moteur SQL"""
    if not cis_list_tuple:
        return pd.DataFrame() # CORRECTION : Un seul dataframe renvoyé ici

    # On ajoute atc_l2 pour le niveau de précision supplémentaire !
    sql_matrice = """
        SELECT 
            SUBSTRING(m.code_atc, 1, 1) as atc_code,
            SUBSTRING(m.code_atc, 1, 3) as atc_l2,
            f.pays_propre as pays,
            COUNT(*) as nb_sites
        FROM medicament m
        JOIN fabricant f ON m.cis = f.cis
        WHERE m.cis IN :cis_list
        GROUP BY 1, 2, 3
    """
    df_m = get_data(sql_matrice, {"cis_list": cis_list_tuple})

    return df_m

def get_stats_penuries_detaillees(cis_list_tuple):
    if not cis_list_tuple:
        return pd.DataFrame()

    sql = """
        SELECT 
            f.pays_propre as pays,
            SUBSTRING(m.code_atc, 1, 1) as atc_code,
            -- On crée une liste propre : "STATUT : Nom du médicament" [cite: 122, 191]
            STRING_AGG(DISTINCT '(' || d.statut || ') ' || COALESCE(m.nom, 'Inconnu'), '<br>• ') as detail_complet,
            COUNT(DISTINCT m.cis) as nb_total_alertes
        FROM medicament m
        JOIN disponibilite d ON m.cis = d.cis
        JOIN fabricant f ON m.cis = f.cis
        WHERE m.cis IN :cis_list 
          AND d.statut IN ('Rupture de stock', 'Tension d''approvisionnement') -- [cite: 118, 119]
        GROUP BY 1, 2
    """
    return get_data(sql, {"cis_list": cis_list_tuple})


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

    # --- 3. GRAPHIQUE PAYS (Bar Chart épuré) ---
    st.write("**Répartition par Pays**")

    # On regroupe les données de la matrice par pays pour le graphique final
    df_pays_total = df_matrice.groupby('Nom Pays')['nb_sites'].sum().reset_index().sort_values('nb_sites', ascending=False)

    if not df_pays_total.empty:
        fig_bar = px.bar(
            df_pays_total, 
            x='Nom Pays', 
            y='nb_sites',
            text='nb_sites',
            labels={'nb_sites': 'Nombre de sites', 'Nom Pays': 'Pays'},
            template='plotly_white'
        )

        fig_bar.update_traces(
            marker_color='#004B87', 
            hovertemplate="Nombre: %{y}<extra></extra>"
        )

        fig_bar.update_layout(
            xaxis_title=None,
            yaxis_title=None,
            height=400,
            margin=dict(l=20, r=20, t=20, b=20)
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

def dci_section(cis_list, df_secret):
    st.subheader("Synthèse regroupée par ATC")

    # La requête SQL magique qui "écrase" les CIS pour regrouper par ATC
    sql = """
        SELECT 
            m.code_atc AS "Code ATC",
            STRING_AGG(DISTINCT c.denomination_substance, ' + ') AS "DCI",
            COUNT(DISTINCT m.cis) AS "Nb de déclinaisons (CIS)",
            STRING_AGG(DISTINCT m.nom, ' | ') AS "Spécialités concernées",
            STRING_AGG(DISTINCT m.titulaire, ' | ') AS "Laboratoires fabriquant",
            STRING_AGG(DISTINCT f.pays_propre, ' | ') AS "Pays de production",
            STRING_AGG(DISTINCT d.statut, ' / ') AS "Alertes de disponibilité",
            BOOL_OR(m.est_mitm) AS est_mitm,
            BOOL_OR(m.est_lme) AS est_lme,
            BOOL_OR(m.est_ulcm) AS est_ulcm
        FROM medicament m
        LEFT JOIN composition c ON m.cis = c.cis
        LEFT JOIN fabricant f ON m.cis = f.cis
        LEFT JOIN disponibilite d ON m.cis = d.cis
        WHERE m.cis IN :cis_list AND m.code_atc IS NOT NULL
        GROUP BY m.code_atc
        ORDER BY m.code_atc
    """

    with st.spinner("Compression des données par DCI..."):
        df_dci = get_data(sql, {"cis_list": tuple(cis_list)})

        # --- 1. GESTION DES LISTES PUBLIQUES ---
        df_dci['Liste MITM'] = df_dci['est_mitm'].apply(lambda x: "X" if x == True else "")
        df_dci['Liste LME (OMS)'] = df_dci['est_lme'].apply(lambda x: "X" if x == True else "")
        df_dci['Liste ULCM'] = df_dci['est_ulcm'].apply(lambda x: "X" if x == True else "")

        df_dci = df_dci.drop(columns=['est_mitm', 'est_lme', 'est_ulcm'])

        # --- 2. GESTION DES LISTES CONFIDENTIELLES ---
        if df_secret is not None and not df_secret.empty:
            df_dci = pd.merge(df_dci, df_secret, left_on='Code ATC', right_on='ATC', how='left')

            colonnes_secretes_mapping = {
                'stock_strat': 'Stock Stratégique',
                'stock_tact': 'Stock Tactique',
                'ssa': 'Liste SSA',
                'msis': 'Liste MSIS',
                'spec_lme': 'Spécialités LME (DGS)'
            }

            for col_brute, nom_propre in colonnes_secretes_mapping.items():
                if col_brute in df_dci.columns:
                    df_dci[nom_propre] = df_dci[col_brute].apply(lambda x: "X" if x == True else "")
                    df_dci = df_dci.drop(columns=[col_brute])

            if 'ATC' in df_dci.columns:
                df_dci = df_dci.drop(columns=['ATC'])


        df_dci = df_dci.fillna("Non renseigné")

        # 1. On affiche l'aperçu à l'écran
        st.dataframe(df_dci, hide_index=True, use_container_width=True)

        # 2. Le bouton d'export Excel dédié
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
