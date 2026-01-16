
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Paraisópolis | Clusters", layout="wide")

@st.cache_data
def load_data():
    df_clientes = pd.read_excel("dashboard_clientes.xlsx")
    df_setores = pd.read_excel("dashboard_setores.xlsx")
    return df_clientes, df_setores

df_clientes, df_setores = load_data()

st.title("Paraisópolis — Segmentação de Clientes e Território")
st.caption("Dashboard para análise de clusters e apoio à estratégia de redução de inadimplência.")

# -------------------------
# Sidebar (filtros)
# -------------------------
st.sidebar.header("Filtros")

territorios = sorted([x for x in df_clientes["cluster_territorial"].dropna().unique()])
clusters = sorted([x for x in df_clientes["cluster"].dropna().unique()])

sel_territorio = st.sidebar.multiselect("Cluster territorial", territorios, default=territorios)
sel_cluster = st.sidebar.multiselect("Cluster de cliente", clusters, default=clusters)

sel_tarifa_social = st.sidebar.multiselect(
    "Enquadra tarifa social",
    sorted(df_clientes["ENQUADRA_TARIFA_SOCIAL"].dropna().unique()),
    default=sorted(df_clientes["ENQUADRA_TARIFA_SOCIAL"].dropna().unique())
)

# aplicar filtros
df_f = df_clientes[
    (df_clientes["cluster_territorial"].isin(sel_territorio)) &
    (df_clientes["cluster"].isin(sel_cluster)) &
    (df_clientes["ENQUADRA_TARIFA_SOCIAL"].isin(sel_tarifa_social))
].copy()

# -------------------------
# KPIs
# -------------------------
c1, c2, c3, c4 = st.columns(4)

total = len(df_f)
pct_inad = (df_f["TEM_DEBITO"].mean() * 100) if total else 0
valor_medio = df_f["VALOR_TOTAL_ABERTO"].mean() if total else 0
consumo_medio = df_f["MEDIA_CONSUMO_12_MESES"].mean() if total else 0

c1.metric("Clientes (filtrados)", f"{total:,}".replace(",", "."))
c2.metric("% Inadimplentes", f"{pct_inad:.1f}%")
c3.metric("Valor médio aberto (R$)", f"{valor_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
c4.metric("Consumo médio 12m (m³)", f"{consumo_medio:.2f}".replace(".", ","))

st.divider()

# -------------------------
# Matriz Cliente × Território
# -------------------------
st.subheader("Matriz Cliente × Território")
matriz = pd.crosstab(df_f["cluster"], df_f["cluster_territorial"])
st.dataframe(matriz, use_container_width=True)

matriz_pct = pd.crosstab(df_f["cluster"], df_f["cluster_territorial"], normalize="columns") * 100
st.dataframe(matriz_pct.round(1), use_container_width=True)

st.divider()

# -------------------------
# Distribuição de clusters
# -------------------------
c5, c6 = st.columns(2)
with c5:
    st.subheader("Distribuição — Cluster de cliente")
    fig1 = px.histogram(df_f, x="cluster")
    st.plotly_chart(fig1, use_container_width=True)

with c6:
    st.subheader("Distribuição — Cluster territorial")
    fig2 = px.histogram(df_f, x="cluster_territorial")
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# -------------------------
# Mapa (pontos por cliente)
# -------------------------
st.subheader("Mapa (pontos por cliente)")
df_map = df_f.dropna(subset=["LATITUDE", "LONGITUDE"]).copy()

if len(df_map) == 0:
    st.warning("Sem coordenadas para os filtros selecionados.")
else:
    fig_map = px.scatter_mapbox(
        df_map,
        lat="LATITUDE",
        lon="LONGITUDE",
        color="cluster",
        hover_data=["PDE", "CD_SETOR", "cluster_territorial", "TEM_DEBITO", "VALOR_TOTAL_ABERTO"],
        zoom=12,
        height=650
    )
    fig_map.update_layout(mapbox_style="open-street-map", margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig_map, use_container_width=True)

st.divider()

# -------------------------
# Tabela de setores (território)
# -------------------------
st.subheader("Indicadores por setor (base agregada)")
st.dataframe(df_setores.sort_values("inadimplencia_media", ascending=False), use_container_width=True)
