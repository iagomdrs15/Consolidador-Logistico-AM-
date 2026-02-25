import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, timezone

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Tomada de Decisão - Manaus V1", layout="wide", page_icon="📊")

# --- DEFINIÇÃO DE FUSO HORÁRIO (MESMO PADRÃO DO SEU APP DE ALOCAÇÃO) ---
def get_now_br():
    fuso_br = timezone(timedelta(hours=-3))
    return datetime.now(fuso_br)

# --- CONEXÃO COM GOOGLE SHEETS API ---
def conectar_google_sheets():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        # Prioriza st.secrets para deploy no Streamlit Cloud
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    except Exception:
        # Fallback para arquivo local durante desenvolvimento
        creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
    return gspread.authorize(creds)

# ID da Planilha "STUCK ORDERS MANAUS V1"
SPREADSHEET_ID = "1YHgMyjTzMwi3SgDG-FEpeEhzRCnX3p1NU_QAJMm_3QM"

# --- FRAGMENTO DE ATUALIZAÇÃO AUTOMÁTICA (5 MINUTOS PARA NÃO SOBRECARREGAR API) ---
@st.fragment(run_every=300.0)
def processamento_dados():
    st.cache_data.clear()
    
    try:
        client = conectar_google_sheets()
        sh = client.open_by_key(SPREADSHEET_ID)
        
        # Extração Direta das Abas
        df_p = pd.DataFrame(sh.worksheet("Parcel").get_all_records())
        df_f = pd.DataFrame(sh.worksheet("Forward Order").get_all_records())
        df_r = pd.DataFrame(sh.worksheet("Return Order").get_all_records())

        # 1. CONSOLIDAÇÃO (Forward + Return)
        df_pedidos = pd.concat([df_f, df_r], ignore_index=True)

        # 2. CRUZAMENTO (Merge) COM ABA PARCEL
        # Relaciona Operador e Aging aos Pedidos via Tracking
        df_final = pd.merge(
            df_pedidos,
            df_p[['SPX Tracking Number', 'Operator', 'Aging Time', 'Next Step Action']],
            left_on='SLS Tracking Number',
            right_on='SPX Tracking Number',
            how='left'
        )

        # 3. TRATAMENTO DE INTELIGÊNCIA (Aging)
        df_final['Aging_Num'] = pd.to_numeric(df_final['Aging Time'], errors='coerce').fillna(0)
        
        def classificar_risco(x):
            if x <= 1: return "🟢 Normal"
            elif x <= 2: return "🟡 Atenção"
            else: return "🔴 CRÍTICO"
        
        df_final['Risco'] = df_final['Aging_Num'].apply(classificar_risco)

        # --- INTERFACE DE EXIBIÇÃO ---
        st.subheader("💡 Indicadores de Pronta Resposta")
        kpi1, kpi2, kpi3 = st.columns(3)
        
        total_criticos = len(df_final[df_final['Aging_Num'] > 2])
        
        kpi1.metric("Volume de Carga", len(df_final))
        kpi2.metric("Stuck Orders (+48h)", total_criticos, delta=total_criticos, delta_color="inverse")
        kpi3.metric("Última Sincronização", get_now_br().strftime("%H:%M:%S"))

        st.markdown("---")
        
        # Filtros de Operação
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filtro_r = st.multiselect("Nível de Risco:", df_final['Risco'].unique(), default=df_final['Risco'].unique())
        with col_f2:
            filtro_s = st.multiselect("Status Atual:", df_final['Status'].unique())

        # Aplicação dos Filtros
        df_view = df_final[df_final['Risco'].isin(filtro_r)]
        if filtro_s:
            df_view = df_view[df_view['Status'].isin(filtro_s)]

        # Colunas Estratégicas para Tomada de Decisão
        cols_decisao = [
            'Order ID', 'LM Hub Receive time', 'Status', 'Current Station', 
            'OnHoldReason', 'Aging Time', 'Risco', 'Operator'
        ]
        
        st.dataframe(df_view[cols_decisao], use_container_width=True, hide_index=True)

        # Download do Relatório Consolidado
        st.sidebar.download_button(
            "📥 Baixar Base Consolidada (CSV)",
            df_final.to_csv(index=False).encode('utf-8'),
            "consolidado_manaus.csv",
            "text/csv"
        )

    except Exception as e:
        st.error(f"Erro na integração de dados: {e}")
        st.info("Verifique se o e-mail da Conta de Serviço está compartilhado na planilha como Leitor.")

# --- EXECUÇÃO DO APP ---
st.title("🚀 Painel de Decisão Logística - Manaus")

# Link para acesso direto à edição
st.markdown(f"""
    <div style="background-color: #1e1e1e; padding: 10px; border-radius: 5px; border-left: 5px solid #007bff; margin-bottom: 20px;">
        <a href="https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit" target="_blank" style="color: white; text-decoration: none; font-weight: bold;">
            🖋️ Acessar Base STUCK ORDERS MANAUS V1 no Google Sheets
        </a>
    </div>
""", unsafe_allow_html=True)

# Chamada da função fragmentada
processamento_dados()
