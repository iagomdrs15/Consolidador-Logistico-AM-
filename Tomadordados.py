import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Consolidador de Decisão - Milorde", layout="wide")

st.title("📊 Inteligência de Dados & Tomada de Decisão")
st.markdown("---")

# 1. UPLOAD DOS ARQUIVOS
st.sidebar.header("Upload de Dados")
uploaded_file = st.sidebar.file_uploader("Selecione o arquivo Excel com as 3 abas", type=["xlsx"])

if uploaded_file:
    try:
        # Lendo as abas
        df_parcel = pd.read_excel(uploaded_file, sheet_name="Parcel")
        df_forward = pd.read_excel(uploaded_file, sheet_name="Forward Order")
        df_return = pd.read_excel(uploaded_file, sheet_name="Return Order")

        st.success("✅ Abas 'Parcel', 'Forward' e 'Return' carregadas com sucesso!")

        # 2. CONSOLIDAÇÃO (MERGE)
        # Unimos Forward e Return (empilhando uma abaixo da outra)
        df_orders = pd.concat([df_forward, df_return], ignore_index=True)

        # Cruzamos com a aba Parcel usando o Tracking Number
        # Nota: Ajuste os nomes das colunas se houver espaços extras
        df_consolidado = pd.merge(
            df_orders, 
            df_parcel[['SPX Tracking Number', 'Scanned Status', 'Operator', 'Aging Time', 'Next Step Action']], 
            left_on='SLS Tracking Number', 
            right_on='SPX Tracking Number', 
            how='left'
        )

        # 3. CRIAÇÃO DAS COLUNAS DE DECISÃO
        # Exemplo de Macro Aging (Tratando como numérico)
        df_consolidado['Aging Days'] = pd.to_numeric(df_consolidado['Aging Time'], errors='coerce')
        
        def definir_macro_aging(days):
            if days <= 1: return "🟢 0-24h"
            elif days <= 2: return "🟡 24-48h"
            else: return "🔴 +48h"

        df_consolidado['Macro Aging'] = df_consolidado['Aging Days'].apply(definir_macro_aging)

        # 4. EXIBIÇÃO DOS RESULTADOS
        st.subheader("📋 Visão Consolidada para Decisão")
        
        # Filtros rápidos
        col1, col2 = st.columns(2)
        with col1:
            filtro_status = st.multiselect("Filtrar por Status", df_consolidado['Status'].unique())
        with col2:
            filtro_macro = st.multiselect("Filtrar por Macro Aging", df_consolidado['Macro Aging'].unique())

        # Aplicando filtros
        df_final = df_consolidado.copy()
        if filtro_status:
            df_final = df_final[df_final['Status'].isin(filtro_status)]
        if filtro_macro:
            df_final = df_final[df_final['Macro Aging'].isin(filtro_macro)]

        # Seleção das colunas que o senhor pediu
        colunas_exibicao = [
            'Order ID', 'LM Hub Receive time', 'Status', 'Current Station', 
            'Destination Hub', 'OnHoldReason', 'Aging Time', 'Macro Aging', 'Operator'
        ]
        
        st.dataframe(df_final[colunas_exibicao], use_container_width=True)

        # Botão para baixar o resultado
        csv = df_final.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar Base Consolidada (CSV)", csv, "consolidado.csv", "text/csv")

    except Exception as e:
        st.error(f"Erro ao processar: {e}")
        st.info("Certifique-se de que os nomes das abas e colunas estão idênticos aos descritos.")
else:
    st.info("Aguardando upload do arquivo Excel para processar os dados...")
