import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path

# -------------------------
# Config
# -------------------------
st.set_page_config(page_title="Paraisópolis | Clusters", layout="wide")

DEFAULT_CLIENTES_XLSX = Path("dashboard_clientes.xlsx")
DEFAULT_SETORES_XLSX  = Path("dashboard_setores.xlsx")

# Arquivo IBGE (por CD_SETOR) — coloque na mesma pasta do app
DEFAULT_IBGE_XLSX = Path("Paraisópolis.xlsx")
SHEET_IBGE = 0  # se precisar, troque pelo nome da aba (ex.: "IBGE" / "Base" etc.)

# -------------------------
# Helpers
# -------------------------
def br_money(x: float) -> str:
    try:
        return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"

def safe_mean(df: pd.DataFrame, col: str) -> float:
    if col in df.columns and len(df) > 0:
        return float(pd.to_numeric(df[col], errors="coerce").mean())
    return 0.0

@st.cache_data
def load_xlsx(path: str) -> pd.DataFrame:
    return pd.read_excel(path)

def require_columns(df: pd.DataFrame, cols: list[str], name: str):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        st.error(f"Arquivo {name} está sem colunas obrigatórias: {missing}")
        st.stop()

def to_int_safe(x):
    try:
        if pd.isna(x):
            return None
        return int(float(x))
    except Exception:
        return None

def normalize_colname(s: str) -> str:
    return str(s).strip()

def build_relative_table(df: pd.DataFrame, group_col: str, value_cols: list[str]) -> pd.DataFrame:
    """
    Tabela relativa (baseline=1,00):
      (média do grupo) / (média geral)
    """
    tmp = df.copy()
    tmp[group_col] = pd.to_numeric(tmp[group_col], errors="coerce")

    for c in value_cols:
        tmp[c] = pd.to_numeric(tmp[c], errors="coerce")

    baseline = tmp[value_cols].mean(numeric_only=True)
    grp = tmp.groupby(group_col)[value_cols].mean(numeric_only=True)
    rel = grp.divide(baseline, axis=1).reset_index()
    return rel

def load_ibge_table() -> tuple[pd.DataFrame | None, list[str]]:
    """Carrega IBGE por CD_SETOR e devolve (df_ibge_sel, cols_ok)."""
    ibge_cols_expected = [
        "Acesso a esgoto",
        "Acesso a água",
        "Lixo coletado_moradores",
        "Alfabetização 15 a 19",
        "Alfabetização 20 a 24",
        "Alfabetização 25 a 29",
        "Alfabetização 30 a 34",
        "Alfabetização 35 a 39",
        "Alfabetização 40 a 44",
        "Alfabetização 45 a 49",
        "Alfabetização 50 a 54",
        "Alfabetização 55 a 59",
        "Alfabetização 60 a 64",
        "Alfabetização 65 a 69",
        "Alfabetização 70 a 80",
    ]

    if not DEFAULT_IBGE_XLSX.exists():
        return None, []

    df_ibge = pd.read_excel(DEFAULT_IBGE_XLSX, sheet_name=SHEET_IBGE)
    df_ibge.columns = [normalize_colname(c) for c in df_ibge.columns]

    if "CD_SETOR" not in df_ibge.columns:
        return None, []

    cols_ok = [c for c in ibge_cols_expected if c in df_ibge.columns]
    if len(cols_ok) == 0:
        return None, []

    df_ibge_sel = df_ibge[["CD_SETOR"] + cols_ok].copy()
    df_ibge_sel["CD_SETOR"] = df_ibge_sel["CD_SETOR"].astype(str).str.strip()
    return df_ibge_sel, cols_ok


# -------------------------
# Labels + Ações
# -------------------------
CLUSTER_NAMES = {
    0: "Residencial social – inadimplência recorrente e consumo estável",
    1: "Residencial social – inadimplência moderada e histórico consolidado",
    2: "Residencial social – inadimplência recente e baixo consumo",
    3: "Residencial social – consumo elevado e inadimplência intermitente",
    4: "Perfil misto/comercial – baixa frequência e alto impacto",
    5: "Outlier crítico – comportamento altamente atípico",
    6: "Perfil operacional sensível – irregularidade e instabilidade",
    7: "Residencial social – inadimplência crônica de alto volume",
}

TERR_NAMES = {
    0: "Território de alta pressão estrutural e vulnerabilidade",
    1: "Território mais consolidado e heterogêneo",
}

CLUSTER_ACTIONS = {
    0: {
        "descricao": "Consumo previsível e inadimplência recorrente; associado a pressão estrutural do território.",
        "acoes": [
            "Programas permanentes de renegociação (não pontuais)",
            "Parcelamentos longos com parcelas baixas e fixas",
            "Campanhas territoriais por setor (mutirões/ação comunitária)",
            "Integração com tarifa social e políticas públicas",
            "Comunicação comunitária (associações, lideranças locais)",
        ],
    },
    1: {
        "descricao": "Inadimplência moderada com histórico consolidado e comportamento relativamente previsível.",
        "acoes": [
            "Renegociação individual padronizada (ofertas claras)",
            "Alertas preventivos (WhatsApp/SMS) antes de acumular",
            "Parcelamento automático ao atingir limite de valor",
            "Incentivo a formas de pagamento recorrente (quando viável)",
        ],
    },
    2: {
        "descricao": "Inadimplência recente e baixo consumo; alto potencial de reversão rápida.",
        "acoes": [
            "Contato rápido após o primeiro débito",
            "Acordos simples (1–3 parcelas) e comunicação objetiva",
            "Mensagens educativas (evitar crescimento do débito)",
            "Ações digitais de baixo custo e alta escala",
        ],
    },
    3: {
        "descricao": "Consumo acima da média com inadimplência intermitente; sensível a variações econômicas.",
        "acoes": [
            "Monitoramento preventivo por variação de consumo",
            "Alertas quando consumo sai do padrão",
            "Renegociação flexível (parcelas ajustáveis)",
            "Educação para uso racional + prevenção de picos",
        ],
    },
    4: {
        "descricao": "Perfil misto/comercial; poucos casos, mas alto impacto financeiro quando inadimplente.",
        "acoes": [
            "Tratamento individualizado (caso a caso)",
            "Acompanhamento próximo e negociação dedicada",
            "Regras específicas de cobrança/regularização",
            "Priorizar por impacto financeiro",
        ],
    },
    5: {
        "descricao": "Outlier crítico: comportamento altamente atípico e raro; não deve orientar política geral.",
        "acoes": [
            "Análise manual/individual",
            "Tratamento fora do fluxo padrão",
            "Checagem de dados e possíveis inconsistências",
            "Ação técnica/jurídica quando aplicável",
        ],
    },
    6: {
        "descricao": "Perfil operacional sensível: irregularidades e instabilidade; cobrança isolada tende a falhar.",
        "acoes": [
            "Vistorias e regularização técnica direcionadas",
            "Integração área técnica + comercial",
            "Acordos condicionados à regularização física",
            "Acompanhamento pós-regularização",
        ],
    },
    7: {
        "descricao": "Inadimplência crônica de alto volume e grande concentração; núcleo duro do problema.",
        "acoes": [
            "Programas contínuos de regularização",
            "Renegociação estruturada (em massa e recorrente)",
            "Ações territoriais integradas (por setor)",
            "Revisão ativa de enquadramento tarifário",
            "Parcerias com assistência social e estratégias comunitárias",
        ],
    },
}

def compute_strategy(territorio_int: int, cluster_int: int) -> dict:
    terr_name = TERR_NAMES.get(territorio_int, f"Território {territorio_int}")
    base = {
        "territorio": terr_name,
        "diretriz_territorial": "",
        "acoes_reforcadas": [],
        "tom_de_comunicacao": "",
        "canais_sugeridos": [],
    }

    if territorio_int == 0:
        base["diretriz_territorial"] = "Priorizar ações coletivas/territoriais, regularização em massa e integração socioassistencial."
        base["tom_de_comunicacao"] = "Comunitário e empático; foco em regularização sustentável."
        base["canais_sugeridos"] = ["Mutirões por setor", "Pontos comunitários", "WhatsApp comunitário", "Ações em campo"]
    elif territorio_int == 1:
        base["diretriz_territorial"] = "Priorizar ações individualizadas, cobrança segmentada e prevenção digital."
        base["tom_de_comunicacao"] = "Objetivo e preventivo; foco em negociação rápida e conveniência."
        base["canais_sugeridos"] = ["WhatsApp/SMS", "Campanhas digitais", "Portal/app", "Atendimento remoto"]
    else:
        base["diretriz_territorial"] = "Diretriz territorial não definida (valor fora do padrão 0/1)."

    info = CLUSTER_ACTIONS.get(cluster_int)
    if info:
        acoes = info["acoes"]
        base["acoes_reforcadas"] = acoes[:2] if len(acoes) >= 2 else acoes

    if cluster_int in (0, 7) and territorio_int == 0:
        base["acoes_reforcadas"] += ["Negociação coletiva por setor", "Programa contínuo (não pontual)"]
    if cluster_int == 2 and territorio_int == 1:
        base["acoes_reforcadas"] += ["Contato rápido (D+1/D+3)", "Oferta simples (1–3 parcelas)"]
    if cluster_int == 6:
        base["acoes_reforcadas"] += ["Acionar time técnico (vistoria/regularização) antes de cobrança intensiva"]

    seen = set()
    base["acoes_reforcadas"] = [x for x in base["acoes_reforcadas"] if not (x in seen or seen.add(x))]
    return base


# -------------------------
# Sidebar: data source
# -------------------------
st.sidebar.header("Fonte de dados (Excel)")
use_upload = st.sidebar.checkbox("Usar upload de arquivos", value=False)

df_clientes = None
df_setores = None

if use_upload:
    up_clientes = st.sidebar.file_uploader("Upload: dashboard_clientes.xlsx", type=["xlsx"])
    up_setores = st.sidebar.file_uploader("Upload: dashboard_setores.xlsx", type=["xlsx"])
    if up_clientes is not None:
        df_clientes = pd.read_excel(up_clientes)
    if up_setores is not None:
        df_setores = pd.read_excel(up_setores)
else:
    if DEFAULT_CLIENTES_XLSX.exists():
        df_clientes = load_xlsx(str(DEFAULT_CLIENTES_XLSX))
    if DEFAULT_SETORES_XLSX.exists():
        df_setores = load_xlsx(str(DEFAULT_SETORES_XLSX))

if df_clientes is None or df_setores is None:
    st.error(
        "Não encontrei os arquivos Excel.\n\n"
        "✅ Coloque na mesma pasta do app:\n"
        "- dashboard_clientes.xlsx\n"
        "- dashboard_setores.xlsx\n\n"
        "OU marque 'Usar upload de arquivos' e envie os dois."
    )
    st.stop()

# -------------------------
# Validations
# -------------------------
require_columns(df_clientes, ["cluster", "cluster_territorial", "TEM_DEBITO", "CD_SETOR"], "dashboard_clientes.xlsx")
require_columns(df_setores,  ["CD_SETOR", "cluster_territorial"], "dashboard_setores.xlsx")

# Padronização de chaves
df_clientes["CD_SETOR"] = df_clientes["CD_SETOR"].astype(str).str.strip()
df_setores["CD_SETOR"]  = df_setores["CD_SETOR"].astype(str).str.strip()

# Ajuste solicitado: trocar "DESCONHECIDO" -> "RESIDENCIAL"
if "TIPO_IMOVEL" in df_clientes.columns:
    df_clientes["TIPO_IMOVEL"] = df_clientes["TIPO_IMOVEL"].replace("DESCONHECIDO", "RESIDENCIAL")

# Numéricos
df_clientes["cluster"] = pd.to_numeric(df_clientes["cluster"], errors="coerce")
df_clientes["cluster_territorial"] = pd.to_numeric(df_clientes["cluster_territorial"], errors="coerce")
df_clientes["TEM_DEBITO"] = pd.to_numeric(df_clientes["TEM_DEBITO"], errors="coerce")
df_setores["cluster_territorial"]  = pd.to_numeric(df_setores["cluster_territorial"], errors="coerce")

# Labels
df_clientes["cluster_int"] = df_clientes["cluster"].apply(to_int_safe)
df_clientes["territorio_int"] = df_clientes["cluster_territorial"].apply(to_int_safe)

df_clientes["cluster_nome"] = df_clientes["cluster_int"].map(CLUSTER_NAMES).fillna(df_clientes["cluster"].astype(str))
df_clientes["territorio_nome"] = df_clientes["territorio_int"].map(TERR_NAMES).fillna(df_clientes["cluster_territorial"].astype(str))

df_setores["territorio_int"] = df_setores["cluster_territorial"].apply(to_int_safe)
df_setores["territorio_nome"] = df_setores["territorio_int"].map(TERR_NAMES).fillna(df_setores["cluster_territorial"].astype(str))

# -------------------------
# Sidebar: navigation + filters
# -------------------------
st.sidebar.divider()
page = st.sidebar.radio(
    "Navegação",
    ["Visão Geral", "Clientes", "Território", "Matriz Estratégica", "Metodologia"],
    index=0,
)

st.sidebar.divider()
st.sidebar.header("Filtros")

territorios = sorted([x for x in df_clientes["cluster_territorial"].dropna().unique()])
clusters = sorted([x for x in df_clientes["cluster"].dropna().unique()])

sel_territorio = st.sidebar.multiselect("Cluster territorial", territorios, default=territorios)
sel_cluster = st.sidebar.multiselect("Cluster de cliente", clusters, default=clusters)

sel_tarifa_social = None
if "ENQUADRA_TARIFA_SOCIAL" in df_clientes.columns:
    op = sorted(df_clientes["ENQUADRA_TARIFA_SOCIAL"].dropna().unique())
    sel_tarifa_social = st.sidebar.multiselect("Tarifa social", op, default=op)

sel_tipo_imovel = None
if "TIPO_IMOVEL" in df_clientes.columns:
    op = sorted(df_clientes["TIPO_IMOVEL"].dropna().unique())
    sel_tipo_imovel = st.sidebar.multiselect("Tipo de imóvel", op, default=op)

# Aplicar filtros (base de clientes)
df_f = df_clientes[
    (df_clientes["cluster_territorial"].isin(sel_territorio)) &
    (df_clientes["cluster"].isin(sel_cluster))
].copy()

if sel_tarifa_social is not None:
    df_f = df_f[df_f["ENQUADRA_TARIFA_SOCIAL"].isin(sel_tarifa_social)].copy()
if sel_tipo_imovel is not None:
    df_f = df_f[df_f["TIPO_IMOVEL"].isin(sel_tipo_imovel)].copy()

# Setores filtrados só para ranking (continua útil)
setores_filtrados = df_f["CD_SETOR"].dropna().unique().tolist()
df_setores_f = df_setores[df_setores["CD_SETOR"].isin(setores_filtrados)].copy()

# -------------------------
# KPIs globais (base filtrada)
# -------------------------
total = len(df_f)
pct_inad = (df_f["TEM_DEBITO"].mean() * 100) if total else 0

if "VALOR_TOTAL_ABERTO" in df_f.columns and total > 0:
    _v = pd.to_numeric(df_f["VALOR_TOTAL_ABERTO"], errors="coerce").fillna(0)
    impacto_total_f = float(_v.sum())
    impacto_medio_f = float(_v.mean())
else:
    impacto_total_f = 0.0
    impacto_medio_f = 0.0

consumo12 = safe_mean(df_f, "MEDIA_CONSUMO_12_MESES")
consumo24 = safe_mean(df_f, "MEDIA_CONSUMO_24_MESES")
irreg_mean = safe_mean(df_f, "QTD_IRREGULARIDADES")

# -------------------------
# Header + KPIs
# -------------------------
st.title("Paraisópolis — Segmentação de Clientes e Território")
st.caption("Dashboard para análise de clusters e apoio à estratégia de redução da inadimplência.")

k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
k1.metric("Clientes (filtrados)", f"{total:,}".replace(",", "."))
k2.metric("% Inadimplentes", f"{pct_inad:.1f}%")
k3.metric("Débito total (R$)", br_money(impacto_total_f))
k4.metric("Débito médio por cliente (R$)", br_money(impacto_medio_f))
k5.metric("Consumo médio 12m", f"{consumo12:.2f}".replace(".", ","))
k6.metric("Consumo médio 24m", f"{consumo24:.2f}".replace(".", ","))
k7.metric("Irregularidades (média)", f"{irreg_mean:.2f}".replace(".", ","))

st.divider()

# -------------------------
# Page: Visão Geral
# -------------------------
if page == "Visão Geral":
    st.subheader("Visão Geral")

    colA, colB = st.columns(2)
    with colA:
        st.markdown("### Distribuição por cluster de cliente")
        fig = px.histogram(df_f, x="cluster_nome")
        fig.update_layout(xaxis_title="", yaxis_title="Clientes")
        st.plotly_chart(fig, use_container_width=True)

    with colB:
        st.markdown("### Distribuição por tipo de território")
        fig2 = px.histogram(df_f, x="territorio_nome")
        fig2.update_layout(xaxis_title="", yaxis_title="Clientes")
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    st.markdown("### Onde está o maior impacto financeiro?")
    if "VALOR_TOTAL_ABERTO" in df_f.columns and len(df_f) > 0:
        df_tmp = df_f.copy()
        df_tmp["VALOR_TOTAL_ABERTO"] = pd.to_numeric(df_tmp["VALOR_TOTAL_ABERTO"], errors="coerce").fillna(0)

        impacto_top = (
            df_tmp.groupby("cluster_nome")["VALOR_TOTAL_ABERTO"]
            .sum()
            .sort_values(ascending=False)
        )

        top_cluster_nome = impacto_top.index[0]
        top_cluster_valor = float(impacto_top.iloc[0])
        st.success(f"Maior impacto total: **{top_cluster_nome}** — **R$ {br_money(top_cluster_valor)}**")
    else:
        st.info("Coluna VALOR_TOTAL_ABERTO não disponível para calcular impacto financeiro.")

    st.divider()

    st.subheader("Ranking — setores com maior inadimplência (base agregada)")
    if "inadimplencia_media" in df_setores_f.columns and len(df_setores_f) > 0:
        top = df_setores_f.sort_values("inadimplencia_media", ascending=False).head(20)
        st.dataframe(top, use_container_width=True)
    else:
        st.info("Coluna 'inadimplencia_media' não encontrada ou sem setores no filtro.")

    # ==========================================================
    # HEATMAPS IBGE (baseline=1) — Territorial primeiro, depois Cliente
    # ==========================================================
    st.divider()
    st.subheader("Comparação relativa (IBGE) — baseline = 1,00")

    df_ibge_sel, cols_ok = load_ibge_table()
    if df_ibge_sel is None or len(cols_ok) == 0:
        st.info(
            "Não foi possível montar os heatmaps IBGE. Verifique se o arquivo "
            f"**{DEFAULT_IBGE_XLSX.name}** está na pasta e contém **CD_SETOR** + colunas IBGE."
        )
    else:
        # -------------------------
        # 1) Heatmap TERRITORIAL
        # -------------------------
        st.markdown("### 1) Perfil socioestrutural por **cluster territorial** (IBGE)")

        df_st = df_setores.copy()
        df_st["CD_SETOR"] = df_st["CD_SETOR"].astype(str).str.strip()
        df_st["cluster_territorial"] = pd.to_numeric(df_st["cluster_territorial"], errors="coerce")

        df_ibge_terr = df_st.merge(df_ibge_sel, on="CD_SETOR", how="left")
        df_rel_terr = build_relative_table(
            df=df_ibge_terr.dropna(subset=["cluster_territorial"]),
            group_col="cluster_territorial",
            value_cols=cols_ok,
        )

        df_rel_terr["territorio_nome"] = df_rel_terr["cluster_territorial"].apply(
            lambda x: TERR_NAMES.get(int(x), str(x)) if pd.notna(x) else "—"
        )
        df_rel_terr = df_rel_terr.sort_values("cluster_territorial")
        heat_terr = df_rel_terr.set_index("territorio_nome")[cols_ok].round(2)

        fig_terr = px.imshow(
            heat_terr,
            text_auto=True,
            aspect="auto",
            labels=dict(x="Indicadores IBGE", y="Cluster territorial", color="Relativo (baseline=1,00)"),
        )
        fig_terr.update_layout(margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_terr, use_container_width=True)

        with st.expander("Metodologia e leitura — heatmap territorial"):
            st.markdown(
                """
**Como foi construído (resumo):**  
1) Pegamos a planilha IBGE (por **setor censitário / CD_SETOR**).  
2) Fazemos *merge* com a base **de setores** (que contém `cluster_territorial`).  
3) Calculamos a **média dos indicadores por cluster territorial**.  
4) Transformamos em “comparação relativa”:  
   **valor_relativo = (média do cluster) ÷ (média geral)** → baseline = 1,00.

**Como ler:**  
- **1,00** = igual à média geral do conjunto  
- **> 1,00** = acima da média geral naquele cluster territorial  
- **< 1,00** = abaixo da média geral naquele cluster territorial  
"""
            )

        st.divider()

        # -------------------------
        # 2) Heatmap CLIENTE
        # -------------------------
        st.markdown("### 2) Perfil socioestrutural por **cluster de cliente** (IBGE)")

        df_cl = df_clientes.copy()
        df_cl["CD_SETOR"] = df_cl["CD_SETOR"].astype(str).str.strip()
        df_cl["cluster"] = pd.to_numeric(df_cl["cluster"], errors="coerce")

        # (opcional) respeitar filtros atuais ao montar o heatmap de cliente
        # Se você quiser SEMPRE global, troque df_f por df_clientes
        df_cl_f = df_f.copy()
        df_cl_f["CD_SETOR"] = df_cl_f["CD_SETOR"].astype(str).str.strip()
        df_cl_f["cluster"] = pd.to_numeric(df_cl_f["cluster"], errors="coerce")

        df_ibge_cli = df_cl_f.merge(df_ibge_sel, on="CD_SETOR", how="left")
        df_rel_cli = build_relative_table(
            df=df_ibge_cli.dropna(subset=["cluster"]),
            group_col="cluster",
            value_cols=cols_ok,
        )

        df_rel_cli["cluster_nome"] = df_rel_cli["cluster"].apply(
            lambda x: CLUSTER_NAMES.get(int(x), str(x)) if pd.notna(x) else "—"
        )
        df_rel_cli = df_rel_cli.sort_values("cluster")
        heat_cli = df_rel_cli.set_index("cluster_nome")[cols_ok].round(2)

        fig_cli = px.imshow(
            heat_cli,
            text_auto=True,
            aspect="auto",
            labels=dict(x="Indicadores IBGE", y="Cluster de cliente", color="Relativo (baseline=1,00)"),
        )
        fig_cli.update_layout(margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_cli, use_container_width=True)

        with st.expander("Metodologia e leitura — heatmap por cliente"):
            st.markdown(
                """
**Como foi construído (resumo):**  
1) A base IBGE é territorial (por **CD_SETOR**). Para “levar” isso ao nível do cliente, fazemos *merge* clientes ↔ IBGE pelo `CD_SETOR`.  
2) Assim, cada cliente “herda” os indicadores IBGE do seu setor.  
3) Calculamos a **média dos indicadores por cluster de cliente**.  
4) Transformamos em “comparação relativa”:  
   **valor_relativo = (média do cluster) ÷ (média geral)** → baseline = 1,00.

**Como ler:**  
- **1,00** = igual à média geral do conjunto  
- **> 1,00** = clientes desse cluster tendem a estar em setores “acima da média” naquele indicador  
- **< 1,00** = clientes desse cluster tendem a estar em setores “abaixo da média” naquele indicador  
"""
            )

# -------------------------
# Page: Clientes
# -------------------------
elif page == "Clientes":
    st.subheader("Clientes")
    st.caption(
        "Análise dos perfis de clientes (clusters) com foco em impacto financeiro médio e inadimplência, "
        "apoiando a priorização de ações."
    )

    # -------------------------
    # Ações recomendadas por cluster (interativo)
    # -------------------------
    st.markdown("### Ações recomendadas por cluster")

    cluster_opts = sorted(
        [to_int_safe(c) for c in df_f["cluster"].dropna().unique() if to_int_safe(c) is not None]
    )

    if cluster_opts:
        cluster_escolhido = st.selectbox(
            "Selecione o cluster de cliente",
            cluster_opts,
            format_func=lambda x: f"{x} — {CLUSTER_NAMES.get(x, str(x))}",
        )

        info = CLUSTER_ACTIONS.get(int(cluster_escolhido))
        if info:
            st.markdown(f"**Nome do cluster:** {CLUSTER_NAMES.get(int(cluster_escolhido), '—')}")
            st.markdown(f"**Descrição:** {info['descricao']}")
            st.markdown("**Ações recomendadas:**")
            for a in info["acoes"]:
                st.write(f"- {a}")
        else:
            st.info("Não há ações cadastradas para este cluster.")
    else:
        st.info("Sem clusters disponíveis para os filtros atuais.")

    st.divider()

    # -------------------------
    # Gráficos estratégicos (lado a lado)
    # -------------------------
    st.markdown("### Visão estratégica por cluster")
    st.caption(
        "Comparação entre impacto financeiro médio por cliente e taxa de inadimplência, "
        "permitindo avaliar simultaneamente severidade financeira e recorrência do problema."
    )

    col1, col2 = st.columns(2)

    # -------- Gráfico 1: Impacto financeiro médio --------
    with col1:
        st.markdown("**Impacto financeiro médio por cliente**")

        if "VALOR_TOTAL_ABERTO" in df_f.columns and len(df_f) > 0:
            df_imp_med = (
                df_f.assign(
                    VALOR_TOTAL_ABERTO=pd.to_numeric(
                        df_f["VALOR_TOTAL_ABERTO"], errors="coerce"
                    ).fillna(0)
                )
                .groupby("cluster_nome")
                .agg(
                    impacto_medio=("VALOR_TOTAL_ABERTO", "mean"),
                )
                .reset_index()
                .sort_values("impacto_medio", ascending=False)
            )

            fig_imp_med = px.bar(
                df_imp_med,
                x="cluster_nome",
                y="impacto_medio",
            )
            fig_imp_med.update_layout(
                xaxis_title="",
                yaxis_title="Impacto financeiro médio (R$)",
            )
            st.plotly_chart(fig_imp_med, use_container_width=True)
        else:
            st.info("Coluna VALOR_TOTAL_ABERTO não disponível para cálculo de impacto financeiro.")

    # -------- Gráfico 2: Taxa de inadimplência --------
    with col2:
        st.markdown("**Taxa de inadimplência**")

        if len(df_f) > 0:
            df_rate = (
                df_f.groupby("cluster_nome")["TEM_DEBITO"]
                .mean()
                .reset_index()
            )
            df_rate["TEM_DEBITO"] = df_rate["TEM_DEBITO"] * 100

            fig_rate = px.bar(
                df_rate,
                x="cluster_nome",
                y="TEM_DEBITO",
            )
            fig_rate.update_layout(
                xaxis_title="",
                yaxis_title="% de clientes inadimplentes",
            )
            st.plotly_chart(fig_rate, use_container_width=True)
        else:
            st.info("Sem dados suficientes para calcular inadimplência.")

    st.divider()

        # -------------------------
    # Tabela resumo por cluster
    # -------------------------
    st.markdown("### Resumo por cluster")

    if len(df_f) > 0 and "VALOR_TOTAL_ABERTO" in df_f.columns:
        agg = (
            df_f.assign(
                VALOR_TOTAL_ABERTO=pd.to_numeric(
                    df_f["VALOR_TOTAL_ABERTO"], errors="coerce"
                ).fillna(0)
            )
            .groupby("cluster_nome")
            .agg(
                clientes=("CD_SETOR", "count"),
                pct_inad=("TEM_DEBITO", "mean"),
                impacto_medio=("VALOR_TOTAL_ABERTO", "mean"),
                impacto_total=("VALOR_TOTAL_ABERTO", "sum"),
            )
            .reset_index()
        )

        agg["pct_inad"] = (agg["pct_inad"] * 100).round(1)

        agg = agg.sort_values("impacto_medio", ascending=False)

        st.dataframe(
            agg,
            use_container_width=True,
        )
    else:
        st.info("Sem dados suficientes para gerar o resumo por cluster.")




# -------------------------
# Page: Território
# -------------------------
elif page == "Território":
    st.subheader("Território")
    st.caption("Mapa e indicadores agregados por setor censitário (com variáveis IBGE quando disponíveis).")

    colA, colB = st.columns([2, 1])

    with colA:
        st.markdown("### Mapa por pontos (clientes)")
        if {"LATITUDE", "LONGITUDE"} <= set(df_f.columns) and len(df_f) > 0:
            df_map = df_f.dropna(subset=["LATITUDE", "LONGITUDE"]).copy()
            if len(df_map) == 0:
                st.warning("Sem coordenadas para os filtros selecionados.")
            else:
                color_mode = st.selectbox("Colorir pontos por", ["cluster_nome", "territorio_nome"], index=0)
                fig_map = px.scatter_mapbox(
                    df_map,
                    lat="LATITUDE",
                    lon="LONGITUDE",
                    color=color_mode,
                    hover_data=[c for c in ["PDE", "CD_SETOR", "cluster_nome", "territorio_nome", "TEM_DEBITO", "VALOR_TOTAL_ABERTO"] if c in df_map.columns],
                    zoom=12,
                    height=650,
                )
                fig_map.update_layout(mapbox_style="open-street-map", margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.info("Mapa não disponível: LATITUDE/LONGITUDE não existem ou não há dados no filtro.")

    with colB:
        st.markdown("### KPIs por setor (filtrado)")
        st.metric("Setores (filtrados)", f"{len(df_setores_f):,}".replace(",", "."))
        if "inadimplencia_media" in df_setores_f.columns and len(df_setores_f) > 0:
            st.metric("Inadimplência média (setores)", f"{df_setores_f['inadimplencia_media'].mean()*100:.1f}%")
        if "DENSIDADE_POP_KM2" in df_setores_f.columns and len(df_setores_f) > 0:
            st.metric("Densidade pop. média", f"{df_setores_f['DENSIDADE_POP_KM2'].mean():,.0f}".replace(",", "."))

        st.divider()
        st.markdown("### Ranking de setores (inadimplência)")
        if "inadimplencia_media" in df_setores_f.columns and len(df_setores_f) > 0:
            st.dataframe(df_setores_f.sort_values("inadimplencia_media", ascending=False).head(20), use_container_width=True)
        else:
            st.info("Coluna inadimplencia_media não encontrada ou sem setores no filtro.")

    st.divider()
    st.markdown("### Base territorial (setores) — para os filtros atuais")
    st.dataframe(df_setores_f, use_container_width=True)

# -------------------------
# Page: Matriz Estratégica
# -------------------------
elif page == "Matriz Estratégica":
    st.subheader("Matriz Estratégica (Cliente × Território)")
    st.caption("Volume, composição, impacto financeiro e recomendação operacional por combinação cliente × território.")

    st.markdown("### Matriz (% por território)")

    matriz_pct = (
        pd.crosstab(
            df_f["cluster_nome"],
            df_f["territorio_nome"],
            normalize="columns"
        ) * 100
    )

    st.dataframe(matriz_pct.round(1), use_container_width=True)

    st.divider()

    st.markdown("### Impacto financeiro na Matriz (Cliente × Território)")
    if "VALOR_TOTAL_ABERTO" in df_f.columns and len(df_f) > 0:
        df_tmp = df_f.copy()
        df_tmp["VALOR_TOTAL_ABERTO"] = pd.to_numeric(df_tmp["VALOR_TOTAL_ABERTO"], errors="coerce").fillna(0)

        impacto_matriz = (
            df_tmp.groupby(["cluster_nome", "territorio_nome"])
            .agg(
                clientes=("CD_SETOR", "count"),
                impacto_total=("VALOR_TOTAL_ABERTO", "sum"),
                impacto_medio=("VALOR_TOTAL_ABERTO", "mean"),
            )
            .reset_index()
        )

        pivot_total = (
            impacto_matriz.pivot(
                index="cluster_nome",
                columns="territorio_nome",
                values="impacto_total"
            ).fillna(0)
        )
        st.caption("Impacto total (R$) por combinação.")
        st.dataframe(pivot_total, use_container_width=True)

        pivot_medio = (
            impacto_matriz.pivot(
                index="cluster_nome",
                columns="territorio_nome",
                values="impacto_medio"
            ).fillna(0)
        )
        st.caption("Impacto médio por cliente (R$) por combinação.")
        st.dataframe(pivot_medio, use_container_width=True)
    else:
        st.info("Coluna VALOR_TOTAL_ABERTO não disponível para calcular impacto financeiro.")

    st.divider()

    st.markdown("### Prioridades sugeridas (automático)")
    if len(df_f) > 0:
        for terr_int, terr_name in sorted(TERR_NAMES.items()):
            df_t = df_f[df_f["territorio_int"] == terr_int]
            if len(df_t) == 0:
                continue

            top = df_t["cluster_nome"].value_counts(normalize=True).head(3) * 100
            st.markdown(f"**{terr_name}** — Top 3 perfis no filtro atual:")
            for name, pct in top.items():
                st.write(f"- {name}: **{pct:.1f}%**")
    else:
        st.info("Sem dados nos filtros atuais.")

    st.divider()

    st.markdown("### Estratégia combinada (selecione cluster de cliente e território)")
    sel_col_a, sel_col_b = st.columns(2)

    with sel_col_a:
        cluster_opts = sorted([to_int_safe(c) for c in df_f["cluster"].dropna().unique() if to_int_safe(c) is not None])
        cluster_pick = st.selectbox(
            "Cluster de cliente",
            cluster_opts if cluster_opts else [0],
            format_func=lambda x: f"{x} — {CLUSTER_NAMES.get(int(x), str(x))}",
            key="mat_cluster_pick",
        ) if cluster_opts else None

    with sel_col_b:
        terr_opts = sorted([to_int_safe(t) for t in df_f["cluster_territorial"].dropna().unique() if to_int_safe(t) is not None])
        terr_pick = st.selectbox(
            "Cluster territorial",
            terr_opts if terr_opts else [0],
            format_func=lambda x: f"{x} — {TERR_NAMES.get(int(x), str(x))}",
            key="mat_terr_pick",
        ) if terr_opts else None

    if cluster_pick is not None and terr_pick is not None:
        strat = compute_strategy(int(terr_pick), int(cluster_pick))
        st.markdown(f"**Território:** {strat['territorio']}")
        st.markdown(f"**Diretriz territorial:** {strat['diretriz_territorial']}")
        st.markdown(f"**Tom de comunicação:** {strat['tom_de_comunicacao']}")
        st.markdown("**Canais sugeridos:** " + ", ".join(strat["canais_sugeridos"]))

        info = CLUSTER_ACTIONS.get(int(cluster_pick))
        if info:
            st.divider()
            st.markdown(f"**Perfil do cliente:** {CLUSTER_NAMES.get(int(cluster_pick), '—')}")
            st.markdown(f"**Descrição do perfil:** {info['descricao']}")
            st.markdown("**Ações recomendadas (perfil):**")
            for a in info["acoes"]:
                st.write(f"- {a}")

        st.divider()
        st.markdown("**Ações reforçadas (Cliente × Território):**")
        for a in strat["acoes_reforcadas"]:
            st.write(f"- {a}")

    st.divider()
    st.markdown(
        """
### Framework resumido
- **Território 0 (alta pressão estrutural)**: ações coletivas, territorialização da negociação, integração socioassistencial.
- **Território 1 (mais consolidado)**: ações individualizadas, prevenção digital, cobrança segmentada.
- **Clusters 0 e 7**: prioridade por volume/recorrência (impacto).
- **Clusters 4, 5 e 6**: casos especiais (alto impacto unitário / outliers / necessidade técnica).
        """
    )


# -------------------------
# Page: Metodologia
# -------------------------
elif page == "Metodologia":
    st.subheader("Metodologia (resumo)")

    st.markdown(
        """
### Objetivo
Segmentar perfis de clientes e tipos de território em Paraisópolis para apoiar estratégias de redução da inadimplência,
integrando dados operacionais e variáveis socioeconômicas do IBGE.

### Modelos
**1) Cluster por cliente (KMeans, K=8)**  
Segmentação comportamental a partir de consumo, débitos, irregularidades, tempo de ligação e variáveis categóricas (ex.: tarifa social).

**2) Agregação por setor censitário**  
Construção de indicadores territoriais: inadimplência média, consumo médio, débito médio, valor médio e tempo médio de ligação.

**3) Cluster territorial (KMeans, K=2)**  
Segmentação estrutural do território integrando indicadores operacionais agregados e variáveis do IBGE (densidade, pessoas/domicílio, alfabetização).

### Seleção de K
Utilizou-se o método da silhueta, priorizando interpretabilidade e acionabilidade.

### Uso operacional
A matriz Cliente × Território orienta abordagens diferenciadas:
- territórios de alta pressão estrutural → ações coletivas e integração social
- territórios mais consolidados → estratégias individualizadas e digitais

### Metodologia: Clusterização em Duas Etapas e Matriz Estratégica Cliente × Território

A análise adotou uma abordagem metodológica em duas etapas, com o objetivo de respeitar a natureza distinta das informações
referentes aos **clientes** e ao **território**, evitando distorções analíticas e assegurando maior interpretabilidade
dos resultados.

Na primeira etapa, realizou-se a **clusterização dos clientes**, utilizando variáveis associadas ao perfil de consumo
e à situação financeira, tais como consumo médio, número e valor de débitos, irregularidades e tipo de economia.
Essa etapa teve como finalidade identificar **padrões homogêneos de comportamento dos clientes**, permitindo a
construção de tipologias baseadas exclusivamente em características individuais e financeiras.

Na segunda etapa, procedeu-se à **clusterização territorial**, a partir da agregação dos dados por setor censitário
e da incorporação de variáveis estruturais, operacionais e socioeconômicas (incluindo indicadores do IBGE).
Essas variáveis representam condições do território que influenciam diretamente a viabilidade e o custo das ações,
mas que não correspondem a comportamentos individuais dos clientes.

Após a definição das tipologias de clientes e de territórios, realizou-se o **cruzamento entre essas duas dimensões**
por meio de uma **Matriz Estratégica Cliente × Território**. Essa matriz permite avaliar simultaneamente o
**potencial financeiro associado aos perfis de clientes** e a **complexidade de atuação imposta pelas condições
territoriais**, orientando a priorização de ações e a definição de estratégias diferenciadas de intervenção.

A opção por não realizar uma única clusterização integrada deve-se ao fato de que a combinação direta de variáveis
individuais e territoriais tende a gerar agrupamentos estatisticamente válidos, porém de difícil interpretação
e com menor utilidade operacional. Dessa forma, a abordagem em duas etapas assegura maior robustez metodológica,
transparência analítica e aderência à realidade operacional e social do território analisado.

        """
    )


# Sidebar footer
st.sidebar.divider()
st.sidebar.caption("Dica: se der erro de arquivo, use o modo 'upload' na barra lateral.")
