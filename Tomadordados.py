import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Gestão Stuck Orders - Porto Velho", layout="wide")

st.title("🚀 Painel de Decisão - Consolidação por Status")

LINK_PLANILHA = "https://docs.google.com/spreadsheets/d/1YHgMyjTzMwi3SgDG-FEpeEhzRCnX3p1NU_QAJMm_3QM/export?format=xlsx"

@st.cache_data(ttl=60)
def carregar_dados_completos():
    try:
        with pd.ExcelFile(LINK_PLANILHA) as xls:
            # Padronização de colunas na leitura
            df_parcel = pd.read_excel(xls, "Parcel").rename(columns=lambda x: str(x).strip())
            df_forward = pd.read_excel(xls, "Forward Order").rename(columns=lambda x: str(x).strip())
            df_return = pd.read_excel(xls, "Return Order").rename(columns=lambda x: str(x).strip())
        return df_parcel, df_forward, df_return
    except Exception as e:
        st.error(f"Erro ao acessar a planilha: {e}")
        return None, None, None

def categorizar_macro_aging(dias):
    if dias == 0: return "0 Dias"
    elif dias <= 2: return "1 a 2 Dias"
    elif dias <= 7: return "3 a 7 Dias"
    elif dias <= 14: return "8 a 14 Dias"
    else: return "Mais de 15 Dias"

# --- PROCESSAMENTO ---
with st.spinner("Consolidando status e calculando aging..."):
    df_p, df_f, df_r = carregar_dados_completos()

if df_p is not None:
    # 1. Unificar Bases de Pedidos (Forward + Return)
    df_pedidos = pd.concat([df_f, df_r], ignore_index=True)

    # 2. Cruzamento (Merge)
    # Trazemos o 'Final Status' da Parcel para comparar com o 'Status' das ordens
    df_final = pd.merge(
        df_pedidos,
        df_p[['SPX Tracking Number', 'Operator', 'Final Status', 'Next Step Action']],
        left_on='SLS Tracking Number',
        right_on='SPX Tracking Number',
        how='left'
    )

    # 3. Lógica de Consolidação de Status
    # Priorizamos o 'Final Status' da Parcel. Se estiver vazio, usamos o 'Status' da ordem.
    df_final['Status_Consolidado'] = df_final['Final Status'].fillna(df_final['Status'])
    df_final['Status_Consolidado'] = df_final['Status_Consolidado'].replace("", "Sem Status")

    # 4. Cálculo de Aging (Baseado em LM Hub Receive time)
    agora = datetime.now()
    df_final['Received_Date'] = pd.to_datetime(df_final['LM Hub Receive time'], errors='coerce', dayfirst=True)
    df_final['Aging_Calculado'] = (agora - df_final['Received_Date']).dt.days.fillna(0).astype(int)
    df_final['Macro Aging'] = df_final['Aging_Calculado'].apply(categorizar_macro_aging)

    # --- BLOCO 1: MATRIZ RESUMO OPERACIONAL ---
    st.subheader("📊 Resumo Consolidado: Status vs Aging")
    
    faixas_ordem = ["0 Dias", "1 a 2 Dias", "3 a 7 Dias", "8 a 14 Dias", "Mais de 15 Dias"]
    
    # Criando a Pivot Table usando o Status Consolidado
    matriz = pd.crosstab(
        df_final['Status_Consolidado'], 
        df_final['Macro Aging'], 
        margins=True, 
        margins_name="TOTAL"
    ).reindex(columns=faixas_ordem + ["TOTAL"], fill_value=0)

    # Estilização Heatmap (Cores para destacar volumes)
    st.dataframe(matriz.style.background_gradient(cmap='YlOrRd', axis=None), use_container_width=True)

    # --- BLOCO 2: LISTA PARA AÇÃO ---
    st.markdown("---")
    st.subheader("📋 Lista de Trabalho (Ação Imediata)")
    
    col_view = ['Order ID', 'Status_Consolidado', 'Aging_Calculado', 'Macro Aging', 'Operator', 'Next Step Action']
    
    # Filtro por Status
    lista_status = df_final['Status_Consolidado'].unique().tolist()
    status_selecionado = st.multiselect("Filtrar por Status:", lista_status, default=lista_status)
    
    df_exibicao = df_final[df_final['Status_Consolidado'].isin(status_selecionado)]
    
    st.dataframe(
        df_exibicao[col_view].sort_values(by='Aging_Calculado', ascending=False),
        use_container_width=True,
        hide_index=True
    )

else:
    st.info("Aguardando leitura da planilha...")
