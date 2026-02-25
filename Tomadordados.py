import streamlit as st
import pandas as pd

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Consolidador Manaus V1", layout="wide")

st.title("📊 Painel de Decisão Logística - Manaus")

# Link fixo configurado para exportação total (XLSX)
# Isso permite que o Pandas leia todas as abas pelo nome, sem precisar de GIDs
LINK_PLANILHA = "https://docs.google.com/spreadsheets/d/1YHgMyjTzMwi3SgDG-FEpeEhzRCnX3p1NU_QAJMm_3QM/export?format=xlsx"

@st.cache_data(ttl=300)
def carregar_dados_completos():
    try:
        # Baixa e lê o arquivo Excel completo
        with pd.ExcelFile(LINK_PLANILHA) as xls:
            # Acessa as abas diretamente pelos nomes conforme sua planilha
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
    # Vincula o operador e o aging aos pedidos usando os códigos de rastreio
    df_final = pd.merge(
        df_pedidos,
        df_p[['SPX Tracking Number', 'Operator', 'Aging Time']],
        left_on='SLS Tracking Number',
        right_on='SPX Tracking Number',
        how='left'
    )

    # 3. Tratamento de Aging Numérico
    df_final['Aging_Num'] = pd.to_numeric(df_final['Aging Time'], errors='coerce').fillna(0)
    
    # Exibição de Métricas
    c1, c2, c3 = st.columns(3)
    c1.metric("Volume Total", len(df_final))
    c2.metric("Críticos (+48h)", len(df_final[df_final['Aging_Num'] > 2]))
    c3.metric("Atualização", "Automática (XLSX)")

    # --- TABELA DE DECISÃO ---
    st.markdown("---")
    st.subheader("📋 Relatório Consolidado")
    
    # Seleção de colunas estratégicas para visualização
    colunas_view = ['Order ID', 'Status', 'Current Station', 'Aging Time', 'Operator']
    st.dataframe(df_final[colunas_view], use_container_width=True, hide_index=True)

else:
    st.info("Verifique se a planilha está com o acesso liberado para 'Qualquer pessoa com o link'.")
