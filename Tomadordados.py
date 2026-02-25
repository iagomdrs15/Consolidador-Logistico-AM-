import streamlit as st
import pandas as pd

# --- CONFIGURAÇÃO DA INTERFACE ---
st.set_page_config(page_title="Consolidador Manaus V1", layout="wide")

st.title("📊 Painel de Decisão Logística - Manaus")

# Link fixo da sua planilha (ajustado para exportação total)
# O Pandas usará este link para tentar ler as abas pelo nome
LINK_PLANILHA = "https://docs.google.com/spreadsheets/d/1YHgMyjTzMwi3SgDG-FEpeEhzRCnX3p1NU_QAJMm_3QM/edit?gid=0#gid=0"

@st.cache_data(ttl=300)
def carregar_dados_completos():
    try:
        # Lendo o arquivo Excel (XLSX) que contém todas as abas
        with pd.ExcelFile(LINK_PLANILHA) as xls:
            # Busca as abas pelos nomes exatos que estão na planilha
            df_parcel = pd.read_excel(xls, "Parcel")
            df_forward = pd.read_excel(xls, "Forward Order")
            df_return = pd.read_excel(xls, "Return Order")
        return df_parcel, df_forward, df_return
    except Exception as e:
        st.error(f"Erro ao acessar a planilha: {e}")
        return None, None, None

# --- PROCESSAMENTO ---
with st.spinner("Sincronizando dados de Manaus..."):
    df_p, df_f, df_r = carregar_dados_completos()

if df_p is not None:
    # 1. Consolidação (União de Forward e Return)
    df_pedidos = pd.concat([df_f, df_r], ignore_index=True)

    # 2. Cruzamento de Dados (Merge)
    # Aqui o sistema une as informações usando os códigos de rastreio
    df_final = pd.merge(
        df_pedidos,
        df_p[['SPX Tracking Number', 'Operator', 'Aging Time']],
        left_on='SLS Tracking Number',
        right_on='SPX Tracking Number',
        how='left'
    )

    # 3. Métricas Rápidas
    df_final['Aging_Num'] = pd.to_numeric(df_final['Aging Time'], errors='coerce').fillna(0)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Volume Total", len(df_final))
    c2.metric("Críticos (+48h)", len(df_final[df_final['Aging_Num'] > 2]))
    c3.metric("Atualização", "Tempo Real")

    # --- EXIBIÇÃO ---
    st.markdown("---")
    st.subheader("📋 Relatório Consolidado")
    
    # Seleção de colunas estratégicas
    colunas_view = ['Order ID', 'Status', 'Current Station', 'Aging Time', 'Operator']
    st.dataframe(df_final[colunas_view], use_container_width=True, hide_index=True)

else:
    st.info("Por favor, verifique se a planilha está com o acesso liberado para 'Qualquer pessoa com o link'.")
