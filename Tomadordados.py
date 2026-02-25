import streamlit as st
import pandas as pd

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Consolidador Online - Milorde", layout="wide")

# --- LINKS DAS PLANILHAS (Substitua pelos seus links de publicação CSV) ---
# Dica: No Google Sheets: Arquivo > Compartilhar > Publicar na Web > Escolha a Aba > Formato CSV
LINKS_PLANILHAS = {
    "Parcel": "URL_AQUI_ABA_PARCEL_CSV",
    "Forward": "URL_AQUI_ABA_FORWARD_CSV",
    "Return": "URL_AQUI_ABA_RETURN_CSV"
}

# Link direto para edição humana (O link normal da planilha)
LINK_EDICAO = "https://docs.google.com/spreadsheets/d/1YHgMyjTzMwi3SgDG-FEpeEhzRCnX3p1NU_QAJMm_3QM/edit?gid=240810884#gid=240810884"

st.title("📊 Painel de Decisão em Tempo Real")

# Botão centralizado para acesso rápido à edição
st.markdown(f"""
    <div style="text-align: center; background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 1px solid #ff4b4b; margin-bottom: 25px;">
        <h3 style="color: white; margin-bottom: 15px;">🛠️ Precisa ajustar os dados?</h3>
        <a href="{LINK_EDICAO}" target="_blank" style="background-color: #ff4b4b; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">
            ABRIR PLANILHA NO GOOGLE SHEETS
        </a>
    </div>
""", unsafe_allow_html=True)

@st.cache_data(ttl=600) # Atualiza os dados a cada 10 minutos
def carregar_dados_online(url):
    try:
        return pd.read_csv(url)
    except Exception as e:
        return None

# --- PROCESSAMENTO ---
with st.spinner("Sincronizando com o Google Sheets..."):
    df_p = carregar_dados_online(LINKS_PLANILHAS["Parcel"])
    df_f = carregar_dados_online(LINKS_PLANILHAS["Forward"])
    df_r = carregar_dados_online(LINKS_PLANILHAS["Return"])

if df_p is not None and df_f is not None and df_r is not None:
    # Unificar bases
    df_pedidos = pd.concat([df_f, df_r], ignore_index=True)
    
    # Merge com Parcel
    base_final = pd.merge(
        df_pedidos,
        df_p[['SPX Tracking Number', 'Operator', 'Aging Time', 'Next Step Action']],
        left_on='SLS Tracking Number',
        right_on='SPX Tracking Number',
        how='left'
    )

    # Lógica de Aging
    base_final['Aging_Num'] = pd.to_numeric(base_final['Aging Time'], errors='coerce').fillna(0)
    base_final['Macro Aging'] = base_final['Aging_Num'].apply(
        lambda x: "🟢 0-24h" if x <= 1 else ("🟡 24-48h" if x <= 2 else "🔴 +48h")
    )

    # --- EXIBIÇÃO ---
    st.subheader("📋 Relatório Consolidado")
    
    cols_exibicao = [
        'Order ID', 'LM Hub Receive time', 'Status', 'Current Station', 
        'OnHoldReason', 'Aging Time', 'Macro Aging', 'Operator'
    ]
    
    st.dataframe(base_final[cols_exibicao], use_container_width=True)
    st.success(f"Dados sincronizados com sucesso às {pd.Timestamp.now().strftime('%H:%M:%S')}")

else:
    st.error("Erro ao conectar com as planilhas. Verifique se os links de 'Publicar na Web' estão corretos.")
