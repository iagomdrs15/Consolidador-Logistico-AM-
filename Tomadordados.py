import streamlit as st
import pandas as pd

# --- CONFIGURAÇÃO DA INTERFACE ---
st.set_page_config(page_title="Consolidador Manaus V1 - Gestão Corporativa", layout="wide")

# IDs extraídos do seu link (GID) e o ID da planilha
SHEET_ID = "1YHgMyjTzMwi3SgDG-FEpeEhzRCnX3p1NU_QAJMm_3QM"

# Mapeamento técnico das abas para exportação CSV direta
LINKS_PLANILHAS = {
    "Parcel": f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=240810884",
    "Forward": f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=663185324",
    "Return": f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=1119561081"
}

# Link de edição para o botão de acesso rápido
LINK_EDITAVEL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"

st.title("📊 Painel de Monitoramento: Stuck Orders Manaus")
st.markdown("---")

# Seção de Gerenciamento da Fonte de Dados
st.markdown(f"""
    <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #0068c9; margin-bottom: 25px;">
        <span style="color: #31333f; font-weight: bold;">Gerenciamento de Dados (Manaus V1):</span>
        <a href="{LINK_EDITAVEL}" target="_blank" style="margin-left: 15px; color: #0068c9; text-decoration: underline; font-weight: bold;">
            Abrir Planilha no Google Sheets para Substituição de Dados
        </a>
    </div>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300) # Cache de 5 minutos
def buscar_dados_v1(url):
    try:
        # storage_options={'User-Agent': 'Mozilla/5.0'} evita bloqueios de leitura automática
        return pd.read_csv(url, storage_options={'User-Agent': 'Mozilla/5.0'})
    except Exception as e:
        return None

# --- PROCESSAMENTO ---
with st.spinner("Sincronizando com a base Manaus..."):
    df_p = buscar_dados_v1(LINKS_PLANILHAS["Parcel"])
    df_f = buscar_dados_v1(LINKS_PLANILHAS["Forward"])
    df_r = buscar_dados_v1(LINKS_PLANILHAS["Return"])

# Validação e Cruzamento
if all(df is not None for df in [df_p, df_f, df_r]):
    
    # 1. Unificar pedidos (Forward + Return)
    df_pedidos = pd.concat([df_f, df_r], ignore_index=True)
    
    # 2. Merge com a aba Parcel usando os Tracking Numbers
    # Nota: No seu arquivo, a aba Parcel usa 'SPX Tracking Number' 
    base_final = pd.merge(
        df_pedidos,
        df_p[['SPX Tracking Number', 'Operator', 'Aging Time', 'Next Step Action', 'Scanned Status']],
        left_on='SLS Tracking Number',
        right_on='SPX Tracking Number',
        how='left'
    )

    # 3. Lógica de Aging (Transformação em numérico para classificação)
    base_final['Aging_Num'] = pd.to_numeric(base_final['Aging Time'], errors='coerce').fillna(0)
    
    def definir_gravidade(valor):
        if valor <= 1: return "🟢 Normal (0-24h)"
        elif valor <= 2: return "🟡 Atenção (24-48h)"
        else: return "🔴 Crítico (+48h)"

    base_final['Status de Aging'] = base_final['Aging_Num'].apply(definir_gravidade)

    # --- DASHBOARD ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Volume de Carga", len(base_final))
    c2.metric("Stuck Orders (+48h)", len(base_final[base_final['Aging_Num'] > 2]))
    c3.metric("Aguardando Operador", base_final['Operator'].isna().sum())

    st.subheader("📋 Relatório Consolidado de Manaus")
    
    # Filtro Dinâmico
    opcoes = base_final['Status de Aging'].unique()
    filtro = st.multiselect("Filtrar por Criticidade:", opcoes, default=opcoes)
    
    df_filtrado = base_final[base_final['Status de Aging'].isin(filtro)]

    # Colunas Estratégicas para exibição
    cols = ['Order ID', 'LM Hub Receive time', 'Status', 'Current Station', 'OnHoldReason', 'Aging Time', 'Status de Aging', 'Operator']
    
    st.dataframe(df_filtrado[cols], use_container_width=True, hide_index=True)

else:
    st.error("❌ Não foi possível carregar as abas. Verifique se os GIDs (IDs das abas) na URL permanecem os mesmos.")
