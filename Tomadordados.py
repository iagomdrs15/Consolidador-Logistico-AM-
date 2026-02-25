import streamlit as st
import pandas as pd

# --- CONFIGURAÇÃO DA INTERFACE ---
st.set_page_config(page_title="Consolidador Logístico - Manaus", layout="wide")

st.title("📊 Painel de Decisão Logística - Manaus V1")

# Entrada do link único conforme solicitado
url_input = st.text_input(
    "Insira o link da planilha Google Sheets:", 
    placeholder="https://docs.google.com/spreadsheets/d/1YHgMyjTzMwi3SgDG-FEpeEhzRCnX3p1NU_QAJMm_3QM/edit..."
)

if url_input:
    try:
        # Extração do ID da planilha (Sheet ID)
        sheet_id = url_input.split("/d/")[1].split("/")[0]
        
        # Mapeamento fixo dos GIDs das abas do seu projeto
        GIDS = {
            "Parcel": "240810884",
            "Forward": "663185324",
            "Return": "1119561081"
        }

        def carregar_aba(gid):
            # Formata a URL para exportação direta em CSV para o Pandas
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
            return pd.read_csv(url)

        with st.spinner("Processando dados das abas..."):
            # Leitura individual de cada aba
            df_p = carregar_aba(GIDS["Parcel"])
            df_f = carregar_aba(GIDS["Forward"])
            df_r = carregar_aba(GIDS["Return"])

            # 1. Consolidação (União de Forward e Return)
            df_pedidos = pd.concat([df_f, df_r], ignore_index=True)

            # 2. Cruzamento (Merge) entre pedidos e triagem
            # Usando SLS Tracking Number como chave de ligação
            df_final = pd.merge(
                df_pedidos,
                df_p[['SPX Tracking Number', 'Operator', 'Aging Time']],
                left_on='SLS Tracking Number',
                right_on='SPX Tracking Number',
                how='left'
            )

            # 3. Tratamento de Aging (Numérico para cálculos)
            df_final['Aging_Num'] = pd.to_numeric(df_final['Aging Time'], errors='coerce').fillna(0)

            # --- EXIBIÇÃO DE RESULTADOS ---
            m1, m2, m3 = st.columns(3)
            m1.metric("Volume de Carga", len(df_final))
            m2.metric("Stuck Orders (+48h)", len(df_final[df_final['Aging_Num'] > 2]))
            m3.metric("Status", "Sincronizado ✅")

            st.markdown("---")
            
            # Filtro por Operador para facilitar a gestão
            operadores = df_final['Operator'].unique().tolist()
            filtro_op = st.multiselect("Filtrar por Operador:", operadores)

            df_tabela = df_final
            if filtro_op:
                df_tabela = df_final[df_final['Operator'].isin(filtro_op)]

            # Visualização das colunas estratégicas
            cols = ['Order ID', 'Status', 'Current Station', 'Aging Time', 'Operator']
            st.subheader("📋 Relatório Consolidado para Decisão")
            st.dataframe(df_tabela[cols], use_container_width=True, hide_index=True)

            # Exportação
            csv = df_final.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Baixar Relatório Completo (CSV)", csv, "relatorio_manaus.csv", "text/csv")

    except Exception:
        st.error("⚠️ Erro de leitura. Certifique-se de que o acesso está como 'Qualquer pessoa com o link' (Leitor).")
else:
    st.info("Aguardando a inserção do link para consolidar os dados.")
