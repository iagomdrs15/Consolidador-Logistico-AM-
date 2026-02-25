import streamlit as st
import pandas as pd

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Consolidador Manaus V1", layout="wide")

st.title("📊 Painel de Decisão Logística - Manaus")

LINK_PLANILHA = "https://docs.google.com/spreadsheets/d/1YHgMyjTzMwi3SgDG-FEpeEhzRCnX3p1NU_QAJMm_3QM/export?format=xlsx"

@st.cache_data(ttl=60)
def carregar_dados_completos():
    try:
        with pd.ExcelFile(LINK_PLANILHA) as xls:
            df_parcel = pd.read_excel(xls, "Parcel").rename(columns=lambda x: x.strip())
            df_forward = pd.read_excel(xls, "Forward Order").rename(columns=lambda x: x.strip())
            df_return = pd.read_excel(xls, "Return Order").rename(columns=lambda x: x.strip())
        return df_parcel, df_forward, df_return
    except Exception as e:
        st.error(f"Erro ao acessar a planilha: {e}")
        return None, None, None

# --- LÓGICA DA FÓRMULA (MACRO AGING) ---
def categorizar_aging(dias):
    if dias == 0:
        return "0 Dias"
    elif dias <= 2:
        return "1 a 2 Dias"
    elif dias <= 7:
        return "3 a 7 Dias"
    elif dias <= 14:
        return "8 a 14 Dias"
    else:
        return "Mais de 15 Dias"

# --- PROCESSAMENTO ---
with st.spinner("Sincronizando dados..."):
    df_p, df_f, df_r = carregar_dados_completos()

if df_p is not None:
    df_pedidos = pd.concat([df_f, df_r], ignore_index=True)

    df_final = pd.merge(
        df_pedidos,
        df_p[['SPX Tracking Number', 'Operator', 'Aging Time']],
        left_on='SLS Tracking Number',
        right_on='SPX Tracking Number',
        how='left'
    )

    # 1. Tratamento numérico (Convertendo para dias)
    df_final['Aging_Num'] = pd.to_numeric(df_final['Aging Time'], errors='coerce').fillna(0)
    
    # 2. Aplicação da sua Fórmula Macro Aging
    df_final['Macro Aging'] = df_final['Aging_Num'].apply(categorizar_aging)

    # --- INTERFACE DE FILTROS ---
    st.sidebar.header("Filtros de Operação")
    
    # Filtro baseado na sua fórmula
    opcoes_macro = ["Todos", "0 Dias", "1 a 2 Dias", "3 a 7 Dias", "8 a 14 Dias", "Mais de 15 Dias"]
    filtro_macro = st.sidebar.selectbox("Filtrar por Faixa de Atraso:", opcoes_macro)

    df_filtrado = df_final
    if filtro_macro != "Todos":
        df_filtrado = df_final[df_final['Macro Aging'] == filtro_macro]

    # --- EXIBIÇÃO ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Volume Exibido", len(df_filtrado))
    c2.metric("Média de Aging", f"{df_filtrado['Aging_Num'].mean():.1f} dias")
    c3.metric("Status", "Sincronizado")

    st.markdown("---")
    st.subheader(f"📋 Lista de Pedidos: {filtro_macro}")
    
    # Colunas de visualização incluindo a nova classificação
    colunas_view = ['Order ID', 'Status', 'Current Station', 'Aging Time', 'Macro Aging', 'Operator']
    
    st.dataframe(
        df_filtrado[colunas_view].sort_values(by='Aging_Num', ascending=False), 
        use_container_width=True, 
        hide_index=True
    )

else:
    st.info("Aguardando sincronização com a planilha Google.")
