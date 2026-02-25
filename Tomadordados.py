import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURAÇÃO DA INTERFACE ---
st.set_page_config(page_title="Gestão Logística Manaus V1", layout="wide")

# --- CONEXÃO COM A API DO GOOGLE ---
def conectar_google_sheets():
    """Realiza a autenticação com a API do Google utilizando Secrets ou arquivo JSON local."""
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        # Tenta carregar das Secrets do Streamlit Cloud (Recomendado para produção)
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    except Exception:
        # Fallback para arquivo local durante o desenvolvimento
        creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
    
    return gspread.authorize(creds)

# ID da planilha extraído da URL fornecida
SPREADSHEET_ID = "1YHgMyjTzMwi3SgDG-FEpeEhzRCnX3p1NU_QAJMm_3QM"

st.title("📊 Painel de Decisão Logística - Manaus")
st.markdown("---")

@st.cache_data(ttl=300)
def extrair_dados_aba(nome_aba):
    """Busca os dados de uma aba específica via API e retorna um DataFrame."""
    try:
        client = conectar_google_sheets()
        sh = client.open_by_key(SPREADSHEET_ID)
        worksheet = sh.worksheet(nome_aba)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Erro ao acessar a aba '{nome_aba}': {e}")
        return None

# --- PROCESSAMENTO DE DADOS ---
with st.spinner("Sincronizando com a base de dados Manaus V1..."):
    # Carregamento das abas mapeadas
    df_p = extrair_dados_aba("Parcel")
    df_f = extrair_dados_aba("Forward Order")
    df_r = extrair_dados_aba("Return Order")

# Verificação se todas as abas foram carregadas com sucesso
if all(df is not None for df in [df_p, df_f, df_r]):
    
    # 1. Consolidação de Pedidos (Forward + Return)
    df_total_pedidos = pd.concat([df_f, df_r], ignore_index=True)
    
    # 2. Cruzamento de Dados (Merge)
    # Vincula informações de triagem (Parcel) aos pedidos via Tracking Number
    df_final = pd.merge(
        df_total_pedidos,
        df_p[['SPX Tracking Number', 'Operator', 'Aging Time', 'Next Step Action']],
        left_on='SLS Tracking Number',
        right_on='SPX Tracking Number',
        how='left'
    )

    # 3. Tratamento de Aging e Classificação de Risco
    df_final['Aging_Num'] = pd.to_numeric(df_final['Aging Time'], errors='coerce').fillna(0)
    
    def definir_prioridade(valor):
        if valor <= 1: return "🟢 Normal (0-24h)"
        elif valor <= 2: return "🟡 Atenção (24-48h)"
        else: return "🔴 Crítico (+48h)"

    df_final['Nível de Aging'] = df_final['Aging_Num'].apply(definir_prioridade)

    # --- EXIBIÇÃO DE INDICADORES (KPIs) ---
    kpi_vol, kpi_stuck, kpi_sync = st.columns(3)
    
    kpi_vol.metric("Volume de Carga", len(df_final))
    kpi_stuck.metric("Stuck Orders (+48h)", len(df_final[df_final['Aging_Num'] > 2]))
    kpi_sync.metric("Status Sincronismo", "Conectado via API")

    # --- TABELA DE TOMADA DE DECISÃO ---
    st.subheader("📋 Relatório Consolidado para Operação")
    
    # Filtros Rápidos
    opcoes_aging = df_final['Nível de Aging'].unique()
    filtro_aging = st.multiselect("Filtrar por Gravidade:", opcoes_aging, default=opcoes_aging)
    
    # Colunas Estratégicas para Visualização
    colunas_exibicao = [
        'Order ID', 'LM Hub Receive time', 'Status', 'Current Station', 
        'OnHoldReason', 'Aging Time', 'Nível de Aging', 'Operator'
    ]
    
    # Aplicação do Filtro e Exibição
    df_filtrado = df_final[df_final['Nível de Aging'].isin(filtro_aging)]
    st.dataframe(df_filtrado[colunas_exibicao], use_container_width=True, hide_index=True)

    # Botão para exportação do resultado consolidado
    csv_data = df_final.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Baixar Base Consolidada (CSV)", csv_data, "consolidado_manaus.csv", "text/csv")

else:
    st.warning("⚠️ O sistema aguarda a configuração das credenciais e permissões na planilha.")
    st.info("Certifique-se de que o e-mail da conta de serviço possui permissão de 'Leitor' na planilha STUCK ORDERS MANAUS V1.")
