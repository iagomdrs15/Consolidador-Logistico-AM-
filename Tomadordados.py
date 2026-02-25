import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Gestão Stuck Orders - Porto Velho", layout="wide")

st.title("🚀 Painel de Decisão em Tempo Real")

# Link fixo configurado para exportação total (XLSX)
LINK_PLANILHA = "https://docs.google.com/spreadsheets/d/1YHgMyjTzMwi3SgDG-FEpeEhzRCnX3p1NU_QAJMm_3QM/export?format=xlsx"

@st.cache_data(ttl=60)
def carregar_dados_completos():
    try:
        with pd.ExcelFile(LINK_PLANILHA) as xls:
            # Carrega as abas e limpa nomes de colunas
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
with st.spinner("Sincronizando dados e calculando indicadores..."):
    df_p, df_f, df_r = carregar_dados_completos()

if df_p is not None:
    # 1. Unificar Bases (Forward + Return)
    df_pedidos = pd.concat([df_f, df_r], ignore_index=True)

    # 2. Cruzamento (Merge) para trazer o Operator e Reason (se houver)
    df_final = pd.merge(
        df_pedidos,
        df_p[['SPX Tracking Number', 'Operator', 'Next Step Action']],
        left_on='SLS Tracking Number',
        right_on='SPX Tracking Number',
        how='left'
    )

    # 3. Cálculo Dinâmico de Aging (Baseado em Current Station Received Time)
    agora = datetime.now()
    # Converte para data, forçando o formato dia/mês/ano
    df_final['Received_Date'] = pd.to_datetime(df_final['LM Hub Receive time'], errors='coerce', dayfirst=True)
    
    # Diferença em dias
    df_final['Aging_Calculado'] = (agora - df_final['Received_Date']).dt.days.fillna(0).astype(int)
    
    # Aplicação do Macro Aging (Sua Fórmula)
    df_final['Macro Aging'] = df_final['Aging_Calculado'].apply(categorizar_macro_aging)

    # 4. Tratamento da Coluna "Reason" (Baseado na sua imagem do dashboard)
    # Se a coluna Reason não vier da aba, usamos OnHoldReason ou Status como fallback
    df_final['Reason_Final'] = df_final['OnHoldReason'].fillna("Justificar!")
    df_final.loc[df_final['Reason_Final'] == "", 'Reason_Final'] = "Justificar!"

    # --- BLOCO 1: MATRIZ RESUMO (Igual à imagem da aba Consolidado) ---
    st.subheader("📊 Resumo Operacional (Matriz de Aging)")
    
    faixas_ordem = ["0 Dias", "1 a 2 Dias", "3 a 7 Dias", "8 a 14 Dias", "Mais de 15 Dias"]
    
    # Criando a Pivot Table para simular o dashboard
    matriz = pd.crosstab(
        df_final['Reason_Final'], 
        df_final['Macro Aging'], 
        margins=True, 
        margins_name="TOTAL"
    ).reindex(columns=faixas_ordem + ["TOTAL"], fill_value=0)

    # Estilização para destacar o "Justificar!" e cores críticas
    def style_matrix(v):
        if v > 0: return 'color: red; font-weight: bold;'
        return 'color: #888;'

    st.table(matriz.style.applymap(style_matrix))

    # --- BLOCO 2: LISTA DETALHADA ---
    st.markdown("---")
    st.subheader("📋 Detalhamento Stuck Orders")
    
    col_view = ['Order ID', 'LM Hub Receive time', 'Status', 'Reason_Final', 'Aging_Calculado', 'Macro Aging', 'Operator']
    
    # Filtro rápido
    filtro = st.multiselect("Filtrar por Faixa:", faixas_ordem, default=faixas_ordem[1:])
    df_view = df_final[df_final['Macro Aging'].isin(filtro)]
    
    st.dataframe(
        df_view[col_view].sort_values(by='Aging_Calculado', ascending=False),
        use_container_width=True,
        hide_index=True
    )

else:
    st.info("Conecte a planilha para visualizar o dashboard.")
