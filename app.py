import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


# =============================================================================
# CONFIGURATION DE LA PAGE
# =============================================================================

st.set_page_config(
    page_title="Analyse des Infractions en France",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f2937;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-container {
        background-color: #f8fafc;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3b82f6;
    }
    .sidebar .sidebar-content {
        background-color: #f1f5f9;
    }
    .stSelectbox > div > div > select {
        background-color: white;
    }
    .info-box {
        background-color: #e0f2fe;
        border-left: 4px solid #0284c7;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# FONCTIONS DE CHARGEMENT DES DONNÉES
# =============================================================================

@st.cache_data
def load_data():
    """
    Charge et traite les données CSV de sécurité publique.
    
    Returns:
        pd.DataFrame: DataFrame nettoyé ou None si erreur
    """
    try:
        # Essayer plusieurs chemins possibles
        possible_paths = [
            "data/serieschrono-datagouv.csv",
            "serieschrono-datagouv.csv",
            "../data/serieschrono-datagouv.csv"
        ]
        
        df = None
        for path in possible_paths:
            try:
                df = pd.read_csv(
                    path,
                    sep=";",
                    encoding="latin-1",
                    low_memory=False
                )
                st.sidebar.success(f"✅ Données chargées depuis : {path}")
                break
            except FileNotFoundError:
                continue
        
        if df is None:
            st.error("❌ Fichier de données non trouvé.")
            st.info("""
            💡 **Comment obtenir les données :**
            1. Téléchargez les données depuis [data.gouv.fr](https://www.data.gouv.fr/)
            2. Recherchez "statistiques criminalité départements"
            3. Placez le fichier CSV dans le dossier `data/`
            4. Renommez-le en `serieschrono-datagouv.csv`
            """)
            return None
        
        # Vérifier les colonnes requises
        required_columns = ['Unite_temps', 'Zone_geographique', 'Valeurs', 'Indicateur']
        missing_cols = [col for col in required_columns if col not in df.columns]
        
        if missing_cols:
            st.error(f"❌ Colonnes manquantes dans le fichier : {missing_cols}")
            st.info(f"Colonnes disponibles : {list(df.columns)}")
            return None
        
        # Gérer Code_dep si absent
        if 'Code_dep' not in df.columns:
            df['Code_dep'] = df['Zone_geographique'].str.extract(r'^(\d{2,3})')
        
        # Nettoyer les données
        df = df[['Unite_temps', 'Zone_geographique', 'Valeurs', 'Indicateur', 'Code_dep']].copy()
        df = df.dropna()
        df['Valeurs'] = pd.to_numeric(df['Valeurs'], errors='coerce')
        df = df.dropna()
        
        # Filtrer France métropolitaine et Corse (codes 01-95)
        df = df[df['Code_dep'].str.match(r'^[0-9]{2}$', na=False)]
        df['Code_dep'] = df['Code_dep'].astype(str).str.zfill(2)
        df = df[df['Code_dep'].between('01', '95')]
        
        # Convertir l'année en entier
        df['Unite_temps'] = df['Unite_temps'].astype(int)
        
        return df
    
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement des données : {e}")
        return None


# =============================================================================
# FONCTIONS D'ANALYSE
# =============================================================================

def get_national_statistics(df, selected_indicators, selected_years):
    """
    Calcule les statistiques nationales agrégées.
    
    Args:
        df: DataFrame des données
        selected_indicators: Liste des indicateurs sélectionnés
        selected_years: Liste des années sélectionnées
    
    Returns:
        pd.DataFrame: Données agrégées par année et indicateur
    """
    filtered_df = df[
        (df['Indicateur'].isin(selected_indicators)) &
        (df['Unite_temps'].isin(selected_years))
    ]
    
    national_data = filtered_df.groupby(
        ['Unite_temps', 'Indicateur']
    )['Valeurs'].sum().reset_index()
    
    return national_data


def calculate_statistics(national_data, selected_indicators):
    """
    Calcule les statistiques détaillées pour chaque indicateur.
    
    Args:
        national_data: DataFrame des données nationales
        selected_indicators: Liste des indicateurs
    
    Returns:
        dict: Dictionnaire des statistiques par indicateur
    """
    stats = {}
    
    for indicator in selected_indicators:
        indicator_data = national_data[
            national_data['Indicateur'] == indicator
        ].sort_values('Unite_temps')
        
        if len(indicator_data) > 1:
            first_value = indicator_data['Valeurs'].iloc[0]
            last_value = indicator_data['Valeurs'].iloc[-1]
            first_year = indicator_data['Unite_temps'].iloc[0]
            last_year = indicator_data['Unite_temps'].iloc[-1]
            
            evolution_abs = last_value - first_value
            evolution_pct = (
                ((last_value - first_value) / first_value) * 100 
                if first_value != 0 else 0
            )
            
            stats[indicator] = {
                'first_value': first_value,
                'last_value': last_value,
                'first_year': first_year,
                'last_year': last_year,
                'evolution_abs': evolution_abs,
                'evolution_pct': evolution_pct,
                'total_cases': indicator_data['Valeurs'].sum(),
                'mean_annual': indicator_data['Valeurs'].mean(),
                'max_value': indicator_data['Valeurs'].max(),
                'min_value': indicator_data['Valeurs'].min(),
                'max_year': indicator_data.loc[
                    indicator_data['Valeurs'].idxmax(), 'Unite_temps'
                ],
                'min_year': indicator_data.loc[
                    indicator_data['Valeurs'].idxmin(), 'Unite_temps'
                ]
            }
    
    return stats


def create_departmental_analysis(df, selected_indicator, selected_year):
    """
    Analyse les données par département.
    
    Args:
        df: DataFrame des données
        selected_indicator: Indicateur sélectionné
        selected_year: Année sélectionnée
    
    Returns:
        pd.DataFrame: Données agrégées par département
    """
    dept_data = df[
        (df['Indicateur'] == selected_indicator) &
        (df['Unite_temps'] == selected_year)
    ]
    
    if dept_data.empty:
        return None
    
    dept_summary = dept_data.groupby(
        'Zone_geographique'
    )['Valeurs'].sum().reset_index()
    dept_summary = dept_summary.sort_values('Valeurs', ascending=False)
    
    return dept_summary


# =============================================================================
# FONCTIONS DE VISUALISATION
# =============================================================================

def create_evolution_chart(national_data, chart_type="line"):
    """
    Crée le graphique d'évolution temporelle.
    
    Args:
        national_data: DataFrame des données nationales
        chart_type: Type de graphique ("line" ou "bar")
    
    Returns:
        plotly.graph_objects.Figure
    """
    if chart_type == "line":
        fig = px.line(
            national_data, 
            x='Unite_temps', 
            y='Valeurs', 
            color='Indicateur',
            title="📈 Évolution des infractions en France métropolitaine et Corse",
            labels={
                'Unite_temps': 'Année',
                'Valeurs': 'Nombre de cas',
                'Indicateur': 'Type d\'infraction'
            },
            markers=True
        )
    else:
        fig = px.bar(
            national_data, 
            x='Unite_temps', 
            y='Valeurs', 
            color='Indicateur',
            title="📊 Évolution des infractions en France métropolitaine et Corse",
            labels={
                'Unite_temps': 'Année',
                'Valeurs': 'Nombre de cas',
                'Indicateur': 'Type d\'infraction'
            },
            barmode='group'
        )
    
    fig.update_layout(
        height=500,
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    fig.update_xaxes(gridcolor='lightgray', tickmode='linear')
    fig.update_yaxes(gridcolor='lightgray')
    
    return fig


def create_comparison_chart(national_data, selected_indicators):
    """
    Crée un graphique de comparaison avec axes multiples.
    
    Args:
        national_data: DataFrame des données nationales
        selected_indicators: Liste des indicateurs
    
    Returns:
        plotly.graph_objects.Figure
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    colors = px.colors.qualitative.Set1
    
    for i, indicator in enumerate(selected_indicators):
        indicator_data = national_data[national_data['Indicateur'] == indicator]
        secondary_y = i > 0
        
        fig.add_trace(
            go.Scatter(
                x=indicator_data['Unite_temps'],
                y=indicator_data['Valeurs'],
                mode='lines+markers',
                name=indicator[:50] + '...' if len(indicator) > 50 else indicator,
                line=dict(color=colors[i % len(colors)], width=3),
                marker=dict(size=8)
            ),
            secondary_y=secondary_y
        )
    
    fig.update_xaxes(title_text="Année", gridcolor='lightgray')
    fig.update_yaxes(title_text="Nombre de cas", secondary_y=False, gridcolor='lightgray')
    
    if len(selected_indicators) > 1:
        fig.update_yaxes(
            title_text="Échelle secondaire",
            secondary_y=True,
            gridcolor='lightgray'
        )
    
    fig.update_layout(
        title="📊 Comparaison multi-axes (utile pour comparer des échelles différentes)",
        height=500,
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig


def create_departmental_chart(dept_data, indicator, year):
    """
    Crée le graphique d'analyse départementale.
    
    Args:
        dept_data: DataFrame des données départementales
        indicator: Indicateur analysé
        year: Année analysée
    
    Returns:
        plotly.graph_objects.Figure
    """
    top_15 = dept_data.head(15)
    
    fig = px.bar(
        top_15,
        x='Valeurs',
        y='Zone_geographique',
        orientation='h',
        title=f"🗺️ Top 15 des départements - {indicator[:40]}... ({year})" if len(indicator) > 40 else f"🗺️ Top 15 des départements - {indicator} ({year})",
        labels={
            'Valeurs': 'Nombre de cas',
            'Zone_geographique': 'Département'
        },
        color='Valeurs',
        color_continuous_scale='Reds'
    )
    
    fig.update_layout(
        height=500,
        yaxis={'categoryorder': 'total ascending'},
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig


# =============================================================================
# FONCTION PRINCIPALE
# =============================================================================

def main():
    """Fonction principale de l'application Streamlit."""
    
    # En-tête
    st.markdown(
        '<h1 class="main-header">🚨 Analyse des Infractions en France</h1>',
        unsafe_allow_html=True
    )
    
    st.markdown("""
    <div class="info-box">
    <strong>🔍 À propos :</strong> Ce module analyse les données de sécurité publique 
    en France métropolitaine et Corse. Il fait partie du projet 
    <a href="https://github.com/nclsprsnw/oasis" target="_blank">OASIS</a>.
    </div>
    """, unsafe_allow_html=True)
    
    # Chargement des données
    with st.spinner("🔄 Chargement des données..."):
        df = load_data()
    
    if df is None:
        st.stop()
    
    # ==========================================================================
    # SIDEBAR - Filtres et paramètres
    # ==========================================================================
    
    st.sidebar.header("🔧 Paramètres")
    
    # Informations sur les données
    st.sidebar.markdown("### 📊 Données chargées")
    st.sidebar.info(f"""
    - **{len(df):,}** enregistrements
    - **{df['Unite_temps'].nunique()}** années ({df['Unite_temps'].min()} → {df['Unite_temps'].max()})
    - **{df['Indicateur'].nunique()}** types d'infractions
    - **{df['Zone_geographique'].nunique()}** départements
    """)
    
    # Sélection des indicateurs
    st.sidebar.markdown("### 🎯 Filtres")
    
    available_indicators = sorted(df['Indicateur'].unique())
    
    # Option pour tout sélectionner/désélectionner
    select_all = st.sidebar.checkbox("Tout sélectionner", value=False)
    
    if select_all:
        default_indicators = available_indicators
    else:
        default_indicators = available_indicators[:3] if len(available_indicators) >= 3 else available_indicators
    
    selected_indicators = st.sidebar.multiselect(
        "Types d'infractions",
        available_indicators,
        default=default_indicators,
        help="Choisissez un ou plusieurs types d'infractions à analyser"
    )
    
    # Sélection des années
    available_years = sorted(df['Unite_temps'].unique())
    
    selected_years = st.sidebar.select_slider(
        "📅 Période d'analyse",
        options=available_years,
        value=(min(available_years), max(available_years)),
        help="Sélectionnez la période à analyser"
    )
    
    if isinstance(selected_years, tuple):
        selected_years = list(range(int(selected_years[0]), int(selected_years[1]) + 1))
    else:
        selected_years = [selected_years]
    
    # Type de graphique
    chart_type = st.sidebar.selectbox(
        "📈 Type de graphique",
        ["line", "bar"],
        format_func=lambda x: "📈 Courbes" if x == "line" else "📊 Barres"
    )
    
    # Vérification
    if not selected_indicators:
        st.warning("⚠️ Veuillez sélectionner au moins un type d'infraction dans la barre latérale.")
        st.stop()
    
    # ==========================================================================
    # CALCUL DES DONNÉES
    # ==========================================================================
    
    national_data = get_national_statistics(df, selected_indicators, selected_years)
    
    if national_data.empty:
        st.warning("⚠️ Aucune donnée disponible pour la sélection actuelle.")
        st.stop()
    
    # ==========================================================================
    # SECTION 1 : Vue d'ensemble
    # ==========================================================================
    
    st.markdown("## 📊 Vue d'ensemble")
    
    # Calcul des métriques
    total_current = national_data[
        national_data['Unite_temps'] == max(selected_years)
    ]['Valeurs'].sum()
    
    total_first = national_data[
        national_data['Unite_temps'] == min(selected_years)
    ]['Valeurs'].sum()
    
    evolution_pct = (
        ((total_current - total_first) / total_first) * 100 
        if total_first != 0 else 0
    )
    
    mean_annual = national_data.groupby('Unite_temps')['Valeurs'].sum().mean()
    
    # Affichage des métriques
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            f"📊 Total {max(selected_years)}",
            f"{total_current:,.0f}".replace(",", " "),
            help=f"Total des infractions sélectionnées en {max(selected_years)}"
        )
    
    with col2:
        delta_formatted = f"{total_current - total_first:+,.0f}".replace(",", " ")
        st.metric(
            "📈 Évolution",
            f"{evolution_pct:+.1f}%",
            delta=delta_formatted,
            delta_color="inverse",  # Rouge si augmentation
            help=f"Évolution entre {min(selected_years)} et {max(selected_years)}"
        )
    
    with col3:
        st.metric(
            "📉 Moyenne annuelle",
            f"{mean_annual:,.0f}".replace(",", " "),
            help="Moyenne annuelle sur la période sélectionnée"
        )
    
    with col4:
        st.metric(
            "🏷️ Indicateurs",
            len(selected_indicators),
            help="Nombre de types d'infractions sélectionnés"
        )
    
    # ==========================================================================
    # SECTION 2 : Évolution temporelle
    # ==========================================================================
    
    st.markdown("## 📈 Évolution temporelle")
    
    if len(selected_indicators) == 1:
        fig = create_evolution_chart(national_data, chart_type)
        st.plotly_chart(fig, use_container_width=True)
    else:
        tab1, tab2 = st.tabs(["📊 Vue standard", "📉 Comparaison multi-axes"])
        
        with tab1:
            fig = create_evolution_chart(national_data, chart_type)
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            st.info("💡 Ce graphique utilise deux axes Y pour comparer des indicateurs ayant des ordres de grandeur différents.")
            fig_comparison = create_comparison_chart(national_data, selected_indicators)
            st.plotly_chart(fig_comparison, use_container_width=True)
    
    # ==========================================================================
    # SECTION 3 : Statistiques détaillées
    # ==========================================================================
    
    st.markdown("## 📋 Statistiques détaillées")
    
    stats = calculate_statistics(national_data, selected_indicators)
    
    # Afficher en colonnes si peu d'indicateurs, sinon en expanders
    if len(stats) <= 2:
        cols = st.columns(len(stats))
        for i, (indicator, stat) in enumerate(stats.items()):
            with cols[i]:
                st.markdown(f"### {indicator[:30]}..." if len(indicator) > 30 else f"### {indicator}")
                
                st.markdown(f"""
                | Métrique | Valeur |
                |----------|--------|
                | **Début ({stat['first_year']})** | {stat['first_value']:,.0f} |
                | **Fin ({stat['last_year']})** | {stat['last_value']:,.0f} |
                | **Évolution** | {stat['evolution_pct']:+.1f}% |
                | **Maximum** | {stat['max_value']:,.0f} ({stat['max_year']}) |
                | **Minimum** | {stat['min_value']:,.0f} ({stat['min_year']}) |
                | **Moyenne annuelle** | {stat['mean_annual']:,.0f} |
                | **Total période** | {stat['total_cases']:,.0f} |
                """.replace(",", " "))
    else:
        for indicator, stat in stats.items():
            with st.expander(f"📊 {indicator}", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### 📈 Évolution")
                    st.markdown(f"""
                    - **{stat['first_year']} :** {stat['first_value']:,.0f} cas
                    - **{stat['last_year']} :** {stat['last_value']:,.0f} cas
                    - **Variation :** {stat['evolution_pct']:+.1f}% ({stat['evolution_abs']:+,.0f})
                    - **Moyenne :** {stat['mean_annual']:,.0f} cas/an
                    """.replace(",", " "))
                
                with col2:
                    st.markdown("#### 🎯 Extremums")
                    st.markdown(f"""
                    - **Maximum :** {stat['max_value']:,.0f} ({stat['max_year']})
                    - **Minimum :** {stat['min_value']:,.0f} ({stat['min_year']})
                    - **Total :** {stat['total_cases']:,.0f} cas
                    - **Amplitude :** {stat['max_value'] - stat['min_value']:,.0f}
                    """.replace(",", " "))
    
    # ==========================================================================
    # SECTION 4 : Analyse départementale
    # ==========================================================================
    
    st.markdown("## 🗺️ Analyse par département")
    
    col1, col2 = st.columns(2)
    
    with col1:
        dept_indicator = st.selectbox(
            "🎯 Infraction à analyser",
            selected_indicators,
            help="Sélectionnez le type d'infraction"
        )
    
    with col2:
        dept_year = st.selectbox(
            "📅 Année",
            sorted(selected_years, reverse=True),
            help="Sélectionnez l'année"
        )
    
    dept_data = create_departmental_analysis(df, dept_indicator, dept_year)
    
    if dept_data is not None and not dept_data.empty:
        # Graphique
        fig_dept = create_departmental_chart(dept_data, dept_indicator, dept_year)
        st.plotly_chart(fig_dept, use_container_width=True)
        
        # Métriques départementales
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "🥇 Département le plus touché",
                dept_data.iloc[0]['Zone_geographique'],
                f"{dept_data.iloc[0]['Valeurs']:,.0f} cas".replace(",", " ")
            )
        
        with col2:
            st.metric(
                "📊 Moyenne départementale",
                f"{dept_data['Valeurs'].mean():,.0f}".replace(",", " ")
            )
        
        with col3:
            st.metric(
                "📏 Écart-type",
                f"{dept_data['Valeurs'].std():,.0f}".replace(",", " ")
            )
        
        # Tableau des données
        with st.expander("📋 Voir toutes les données départementales"):
            st.dataframe(
                dept_data.rename(columns={
                    'Zone_geographique': 'Département',
                    'Valeurs': 'Nombre de cas'
                }),
                use_container_width=True,
                hide_index=True
            )
    else:
        st.warning("⚠️ Aucune donnée disponible pour cette sélection.")
    
    # ==========================================================================
    # FOOTER
    # ==========================================================================
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**📊 Source :** [data.gouv.fr](https://www.data.gouv.fr/)")
    
    with col2:
        st.markdown("**🔗 Projet :** [OASIS](https://github.com/nclsprsnw/oasis)")
    
    with col3:
        st.markdown(f"**🕐 MAJ :** {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 1rem; font-size: 0.8rem;'>
    Développé par <a href="https://github.com/Dreipfelt">@Dreipfelt</a> | 
    Formation Data Science 2024
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

if __name__ == "__main__":
    main()