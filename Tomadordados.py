import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURAÇÃO DA INTERFACE ---
st.set_page_config(page_title="Gestão Logística Manaus V1", layout="wide")

# --- CONEXÃO COM A API DO GOOGLE ---
# Certifique-se de que o arquivo credentials.json está na mesma pasta
def conectar_google_sheets():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    # No Streamlit Cloud, use st.secrets. No local, use o arquivo json.
    try:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    except:
        creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
    
    return gspread.authorize(creds)

# ID da sua planilha (extraído do link que você enviou)
SPREADSHEET_ID = "1YHgMyjTzMwi3SgDG-FEpeEhzRCnX3p1NU_QAJMm_3QM"

st.title("📊 Painel de Decisão Logística - Manaus")
st.markdown("---")

@st.cache_data(ttl=300)
def extrair_aba(aba_nome):
    try:
        client = conectar_google_sheets()
        sh = client.open_by_key(SPREADSHEET_ID)
        worksheet = sh.worksheet(aba_nome)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Erro ao acessar aba '{aba_nome}': {e}")
        return None

# --- PROCESSAMENTO ---
with st.spinner("Sincronizando dados via API oficial..."):
    # IMPORTANTE: Os nomes das abas devem ser EXATAMENTE iguais aos da planilha
    df_p = extrair_aba("Parcel")
    df_f = extrair_aba("Forward Order")
    df_r = extrair_aba("Return Order")

if all(df is not None for df in [df_p, df_f, df_r]):
    
    # 1. União das bases de pedidos
    df_total_pedidos = pd.concat([df_f, df_r], ignore_index=True)
    
    # 2. Cruzamento (Merge)
    # Ajustado para os nomes de colunas que você utiliza
    df_final = pd.merge(
        df_total_pedidos,
        df_p[['SPX Tracking Number', 'Operator', 'Aging Time', 'Next Step Action']],
        left_on='SLS Tracking Number',
        right_on='SPX Tracking Number',
        how='left'
    )

    # 3. Lógica de Aging e KPIs
    df_final['Aging_Num'] = pd.to_numeric(df_final['Aging Time'], errors='coerce').fillna(0)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Volume de Carga", len(base_final))
    c2.metric("Críticos (+48h)", len(df_final[df_final['Aging_Num'] > 2]))
    c3.metric("Status API", "Conectado ✅")

    st.subheader("📋 Relatório Consolidado")
    
    # Exibição da tabela final filtrável
    exibicao = ['Order ID', 'LM Hub Receive time', 'Status', 'Current Station', 'OnHoldReason', 'Aging Time', 'Operator']
    st.dataframe(df_final[exibicao], use_container_width=True, hide_index=True)

else:
    st.warning("⚠️ Aguardando configuração das credenciais de API para acesso direto.")
