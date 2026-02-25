import streamlit as st
import pandas as pd

# --- CONFIGURAÇÃO PROFISSIONAL ---
st.set_page_config(page_title="Gestão Logística Manaus V1", layout="wide")

# Link base fornecido por você
BASE_URL = "https://docs.google.com/spreadsheets/d/1YHgMyjTzMwi3SgDG-FEpeEhzRCnX3p1NU_QAJMm_3QM"

# IDs das abas (GIDs) identificados no seu link e estrutura
GIDS = {
    "Parcel": "240810884",
    "Forward": "663185324",
    "Return": "1119561081"
}

st.title("📊 Painel de Decisão Logística - Manaus")

# Cabeçalho de Gestão com Link Direto para Edição
st.markdown(f"""
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 5px solid #007bff; margin-bottom: 20px;">
        <h4 style="margin:0; color: #343a40;">Fonte de Dados: STUCK ORDERS MANAUS V1</h4>
        <p style="margin:5px 0; color: #6c757d;">O sistema está lendo as abas diretamente. Para alterar os dados, utilize o link abaixo:</p>
        <a href="{BASE_URL}/edit" target="_blank" style="text-decoration: none;">
            <button style="background-color: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: bold;">
                🔗 Abrir Planilha Original
            </button>
        </a>
    </div>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def leitura_direta_sheets(gid):
    # Esta URL "hackeia" o link de edição e o transforma em um link de exportação direta
    url_export = f"{BASE_URL}/export?format=csv&gid={gid}"
    try:
        # User-Agent necessário para evitar que o Google identifique como robô e bloqueie
        return pd.read_csv(url_export, storage_options={'User-Agent': 'Mozilla/5.0'})
    except Exception as e:
        st.error(f"Erro ao ler aba (GID {gid}): {e}")
        return None

# --- PROCESSAMENTO ---
with st.spinner("Sincronizando dados diretamente do Sheets..."):
    df_p = leitura_direta_sheets(GIDS["Parcel"])
    df_f = leitura_direta_sheets(GIDS["Forward"])
    df_r = leitura_direta_sheets(GIDS["Return"])

if all(df is not None for df in [df_p, df_f, df_r]):
    
    # 1. União das abas de pedidos
    df_total_pedidos = pd.concat([df_f, df_r], ignore_index=True)
    
    # 2. Cruzamento (Merge) usando os nomes de colunas do seu projeto
    # Verificamos se as colunas existem antes do merge para evitar erros
    colunas_necessarias = ['SPX Tracking Number', 'Operator', 'Aging Time', 'Next Step Action']
    df_p_clean = df_p[[c for c in colunas_necessarias if c in df_p.columns]]

    df_final = pd.merge(
        df_total_pedidos,
        df_p_clean,
        left_on='SLS Tracking Number',
        right_on='SPX Tracking Number',
        how='left'
    )

    # 3. Tratamento de Aging
    if 'Aging Time' in df_final.columns:
        df_final['Aging_Numeric'] = pd.to_numeric(df_final['Aging Time'], errors='coerce').fillna(0)
        df_final['Prioridade'] = df_final['Aging_Numeric'].apply(
            lambda x: "🟢 Normal" if x <= 1 else ("🟡 Atenção" if x <= 2 else "🔴 CRÍTICA")
        )
    else:
        df_final['Prioridade'] = "N/A"

    # --- EXIBIÇÃO ---
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Volume Total", len(df_final))
    if 'Aging_Numeric' in df_final.columns:
        kpi2.metric("Críticos (+48h)", len(df_final[df_final['Aging_Numeric'] > 2]))
    kpi3.metric("Status Sincronismo", "Conectado ✅")

    st.subheader("📋 Relatório Consolidado")
    
    # Seleção de colunas para a tabela (ajustado para suas colunas)
    colunas_view = [c for c in ['Order ID', 'LM Hub Receive time', 'Status', 'Current Station', 'OnHoldReason', 'Aging Time', 'Prioridade', 'Operator'] if c in df_final.columns]
    
    st.dataframe(df_final[colunas_view], use_container_width=True, hide_index=True)

else:
    st.error("⚠️ Falha na comunicação direta. Verifique se a planilha está com acesso liberado para 'Qualquer pessoa com o link'.")
