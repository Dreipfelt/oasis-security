import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configuration de la page
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
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """Charge et traite les données CSV"""
    try:
        # Charger le fichier CSV
        df = pd.read_csv("serieschrono-datagouv.csv", sep=";", encoding="latin-1", low_memory=False)
        
        # Nettoyer les données
        df = df[['Unite_temps', 'Zone_geographique', 'Valeurs', 'Indicateur', 'Code_dep']].dropna()
        df['Valeurs'] = pd.to_numeric(df['Valeurs'], errors='coerce')
        df = df.dropna()
        
        # Filtrer seulement la France métropolitaine et la Corse (codes 01-95)
        df = df[df['Code_dep'].str.match(r'^[0-9]{2}$', na=False)]
        df = df[df['Code_dep'].astype(str).str.zfill(2).between('01', '95')]
        
        return df
    except FileNotFoundError:
        st.error("❌ Fichier 'serieschrono-datagouv.csv' non trouvé. Assurez-vous qu'il est dans le même répertoire.")
        return None
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement des données : {e}")
        return None

def get_national_statistics(df, selected_indicators, selected_years):
    """Calcule les statistiques nationales"""
    filtered_df = df[
        (df['Indicateur'].isin(selected_indicators)) &
        (df['Unite_temps'].isin(selected_years))
    ]
    
    # Agrégation nationale par année et indicateur
    national_data = filtered_df.groupby(['Unite_temps', 'Indicateur'])['Valeurs'].sum().reset_index()
    
    return national_data

def create_evolution_chart(national_data, chart_type="line"):
    """Crée le graphique d'évolution"""
    if chart_type == "line":
        fig = px.line(
            national_data, 
            x='Unite_temps', 
            y='Valeurs', 
            color='Indicateur',
            title="Évolution des infractions en France métropolitaine et Corse",
            labels={'Unite_temps': 'Année', 'Valeurs': 'Nombre de cas', 'Indicateur': 'Type d\'infraction'},
            markers=True
        )
    else:
        fig = px.bar(
            national_data, 
            x='Unite_temps', 
            y='Valeurs', 
            color='Indicateur',
            title="Évolution des infractions en France métropolitaine et Corse",
            labels={'Unite_temps': 'Année', 'Valeurs': 'Nombre de cas', 'Indicateur': 'Type d\'infraction'},
            barmode='group'
        )
    
    fig.update_layout(
        height=600,
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

def create_comparison_chart(national_data, selected_indicators):
    """Crée un graphique de comparaison avec plusieurs axes Y"""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    colors = px.colors.qualitative.Set1
    
    for i, indicator in enumerate(selected_indicators):
        indicator_data = national_data[national_data['Indicateur'] == indicator]
        
        # Première infraction sur l'axe principal, les autres sur l'axe secondaire
        secondary_y = i > 0
        
        fig.add_trace(
            go.Scatter(
                x=indicator_data['Unite_temps'],
                y=indicator_data['Valeurs'],
                mode='lines+markers',
                name=indicator,
                line=dict(color=colors[i % len(colors)], width=3),
                marker=dict(size=6)
            ),
            secondary_y=secondary_y
        )
    
    fig.update_xaxes(title_text="Année")
    fig.update_yaxes(title_text="Nombre de cas", secondary_y=False)
    if len(selected_indicators) > 1:
        fig.update_yaxes(title_text="Nombre de cas (échelle secondaire)", secondary_y=True)
    
    fig.update_layout(
        title="Comparaison des infractions (axes multiples pour différentes échelles)",
        height=600,
        hovermode='x unified'
    )
    
    return fig

def calculate_statistics(national_data, selected_indicators):
    """Calcule les statistiques détaillées"""
    stats = {}
    
    for indicator in selected_indicators:
        indicator_data = national_data[national_data['Indicateur'] == indicator].sort_values('Unite_temps')
        
        if len(indicator_data) > 1:
            first_value = indicator_data['Valeurs'].iloc[0]
            last_value = indicator_data['Valeurs'].iloc[-1]
            first_year = indicator_data['Unite_temps'].iloc[0]
            last_year = indicator_data['Unite_temps'].iloc[-1]
            
            # Calculs statistiques
            evolution_abs = last_value - first_value
            evolution_pct = ((last_value - first_value) / first_value) * 100 if first_value != 0 else 0
            total_cases = indicator_data['Valeurs'].sum()
            mean_annual = indicator_data['Valeurs'].mean()
            max_value = indicator_data['Valeurs'].max()
            min_value = indicator_data['Valeurs'].min()
            max_year = indicator_data[indicator_data['Valeurs'] == max_value]['Unite_temps'].iloc[0]
            min_year = indicator_data[indicator_data['Valeurs'] == min_value]['Unite_temps'].iloc[0]
            
            stats[indicator] = {
                'first_value': first_value,
                'last_value': last_value,
                'first_year': first_year,
                'last_year': last_year,
                'evolution_abs': evolution_abs,
                'evolution_pct': evolution_pct,
                'total_cases': total_cases,
                'mean_annual': mean_annual,
                'max_value': max_value,
                'min_value': min_value,
                'max_year': max_year,
                'min_year': min_year
            }
    
    return stats

def create_departmental_analysis(df, selected_indicator, selected_year):
    """Analyse par département"""
    dept_data = df[
        (df['Indicateur'] == selected_indicator) &
        (df['Unite_temps'] == selected_year)
    ]
    
    if dept_data.empty:
        return None
    
    # Agrégation par département
    dept_summary = dept_data.groupby('Zone_geographique')['Valeurs'].sum().reset_index()
    dept_summary = dept_summary.sort_values('Valeurs', ascending=False)
    
    return dept_summary

def main():
    # En-tête
    st.markdown('<h1 class="main-header">🚨 Analyse des Infractions en France</h1>', unsafe_allow_html=True)
    st.markdown("**France métropolitaine et Corse - Données 2016-2024**")
    
    # Chargement des données
    with st.spinner("Chargement des données..."):
        df = load_data()
    
    if df is None:
        st.stop()
    
    # Sidebar pour les filtres
    st.sidebar.header("🔧 Paramètres")
    
    # Informations sur les données
    st.sidebar.markdown("### 📊 Informations")
    st.sidebar.info(f"""
    **Données chargées :**
    - {len(df):,} enregistrements
    - {df['Unite_temps'].nunique()} années
    - {df['Indicateur'].nunique()} types d'infractions
    - {df['Zone_geographique'].nunique()} départements
    """)
    
    # Sélection des indicateurs
    available_indicators = sorted(df['Indicateur'].unique())
    selected_indicators = st.sidebar.multiselect(
        "🎯 Sélectionner les types d'infractions",
        available_indicators,
        default=available_indicators[:3],
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
        selected_years = list(range(selected_years[0], selected_years[1] + 1))
    else:
        selected_years = [selected_years]
    
    # Type de graphique
    chart_type = st.sidebar.selectbox(
        "📈 Type de graphique",
        ["line", "bar"],
        format_func=lambda x: "Courbe" if x == "line" else "Barres"
    )
    
    if not selected_indicators:
        st.warning("⚠️ Veuillez sélectionner au moins un type d'infraction.")
        st.stop()
    
    # Calculs des données nationales
    national_data = get_national_statistics(df, selected_indicators, selected_years)
    
    if national_data.empty:
        st.warning("⚠️ Aucune donnée disponible pour la sélection actuelle.")
        st.stop()
    
    # Métriques principales
    st.markdown("## 📊 Vue d'ensemble")
    
    total_current = national_data[national_data['Unite_temps'] == max(selected_years)]['Valeurs'].sum()
    total_first = national_data[national_data['Unite_temps'] == min(selected_years)]['Valeurs'].sum()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total dernière année",
            f"{total_current:,.0f}".replace(",", " "),
            help=f"Total des infractions sélectionnées en {max(selected_years)}"
        )
    
    with col2:
        evolution_pct = ((total_current - total_first) / total_first) * 100 if total_first != 0 else 0
        st.metric(
            "Évolution globale",
            f"{evolution_pct:+.1f}%",
            delta=f"{total_current - total_first:,.0f}".replace(",", " "),
            help=f"Évolution entre {min(selected_years)} et {max(selected_years)}"
        )
    
    with col3:
        mean_annual = national_data.groupby('Unite_temps')['Valeurs'].sum().mean()
        st.metric(
            "Moyenne annuelle",
            f"{mean_annual:,.0f}".replace(",", " "),
            help="Moyenne annuelle sur la période sélectionnée"
        )
    
    with col4:
        st.metric(
            "Types d'infractions",
            len(selected_indicators),
            help="Nombre de types d'infractions sélectionnés"
        )
    
    # Graphique principal
    st.markdown("## 📈 Évolution temporelle")
    
    if len(selected_indicators) == 1:
        fig = create_evolution_chart(national_data, chart_type)
    else:
        # Onglets pour différentes vues
        tab1, tab2 = st.tabs(["Vue standard", "Comparaison multi-axes"])
        
        with tab1:
            fig = create_evolution_chart(national_data, chart_type)
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            fig_comparison = create_comparison_chart(national_data, selected_indicators)
            st.plotly_chart(fig_comparison, use_container_width=True)
    
    if len(selected_indicators) == 1:
        st.plotly_chart(fig, use_container_width=True)
    
    # Statistiques détaillées
    st.markdown("## 📋 Statistiques détaillées")
    
    stats = calculate_statistics(national_data, selected_indicators)
    
    for indicator, stat in stats.items():
        with st.expander(f"📊 {indicator}", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 🔢 Évolution")
                st.markdown(f"""
                - **{stat['first_year']} :** {stat['first_value']:,.0f} cas
                - **{stat['last_year']} :** {stat['last_value']:,.0f} cas
                - **Évolution :** {stat['evolution_pct']:+.1f}% ({stat['evolution_abs']:+,.0f} cas)
                - **Moyenne annuelle :** {stat['mean_annual']:,.0f} cas
                """.replace(",", " "))
            
            with col2:
                st.markdown("### 📈 Extremums")
                st.markdown(f"""
                - **Maximum :** {stat['max_value']:,.0f} cas ({stat['max_year']})
                - **Minimum :** {stat['min_value']:,.0f} cas ({stat['min_year']})
                - **Total période :** {stat['total_cases']:,.0f} cas
                - **Écart max-min :** {stat['max_value'] - stat['min_value']:,.0f} cas
                """.replace(",", " "))
    
    # Analyse départementale
    st.markdown("## 🗺️ Analyse par département")
    
    col1, col2 = st.columns(2)
    with col1:
        dept_indicator = st.selectbox(
            "Choisir l'infraction à analyser",
            selected_indicators,
            help="Sélectionnez le type d'infraction pour l'analyse départementale"
        )
    with col2:
        dept_year = st.selectbox(
            "Choisir l'année",
            selected_years,
            index=len(selected_years)-1,
            help="Sélectionnez l'année pour l'analyse départementale"
        )
    
    dept_data = create_departmental_analysis(df, dept_indicator, dept_year)
    
    if dept_data is not None and not dept_data.empty:
        # Top 15 des départements
        top_15 = dept_data.head(15)
        
        fig_dept = px.bar(
            top_15,
            x='Valeurs',
            y='Zone_geographique',
            orientation='h',
            title=f"Top 15 des départements - {dept_indicator} ({dept_year})",
            labels={'Valeurs': 'Nombre de cas', 'Zone_geographique': 'Département'},
            color='Valeurs',
            color_continuous_scale='Reds'
        )
        fig_dept.update_layout(height=600, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_dept, use_container_width=True)
        
        # Statistiques départementales
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Département le plus touché", 
                     dept_data.iloc[0]['Zone_geographique'],
                     f"{dept_data.iloc[0]['Valeurs']:,.0f} cas".replace(",", " "))
        with col2:
            st.metric("Moyenne départementale", 
                     f"{dept_data['Valeurs'].mean():,.0f}".replace(",", " "))
        with col3:
            st.metric("Écart-type", 
                     f"{dept_data['Valeurs'].std():,.0f}".replace(",", " "))
    
    # Footer
    st.markdown("---")
    st.markdown("**Source :** Données de sécurité publique - France métropolitaine et Corse")
    st.markdown(f"**Dernière mise à jour :** {datetime.now().strftime('%d/%m/%Y à %H:%M')}")

if __name__ == "__main__":
    main()