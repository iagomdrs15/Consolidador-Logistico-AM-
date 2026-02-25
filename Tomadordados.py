import streamlit as st
import pandas as pd

# --- CONFIGURAÇÃO DA INTERFACE ---
st.set_page_config(page_title="Consolidador Logístico - Gestão de Operações", layout="wide")

# Configuração dos links das planilhas (Substitua pelas URLs de publicação CSV)
# Importante: O link deve terminar com 'output=csv'
LINKS_PLANILHAS = {
    "Parcel": "COLE_AQUI_O_LINK_CSV_DA_ABA_PARCEL",
    "Forward": "COLE_AQUI_O_LINK_CSV_DA_ABA_FORWARD",
    "Return": "COLE_AQUI_O_LINK_CSV_DA_ABA_RETURN"
}

# Link para edição manual dos dados
LINK_PLANILHA_EDITAVEL = "https://docs.google.com/spreadsheets/d/SEU_ID_AQUI/edit"

st.title("📊 Painel de Decisão Logística")
st.markdown("---")

# Seção de Acesso à Fonte de Dados
st.info("💡 Este painel está conectado diretamente ao Google Sheets. As alterações feitas na planilha serão refletidas aqui após a atualização.")

st.markdown(f"""
    <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #0068c9; margin-bottom: 25px;">
        <span style="color: #31333f; font-weight: bold;">Gerenciamento de Dados:</span>
        <a href="{LINK_PLANILHA_EDITAVEL}" target="_blank" style="margin-left: 15px; color: #0068c9; text-decoration: underline;">
            Acessar Planilha de Origem para Edição
        </a>
    </div>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)  # Cache de 5 minutos para performance
def buscar_dados_v3(url):
    try:
        # User-agent adicionado para evitar bloqueios de requisição automática
        return pd.read_csv(url, storage_options={'User-Agent': 'Mozilla/5.0'})
    except Exception as e:
        return None

# --- PROCESSAMENTO DOS DADOS ---
with st.spinner("Sincronizando base de dados..."):
    df_parcel = buscar_dados_v3(LINKS_PLANILHAS["Parcel"])
    df_forward = buscar_dados_v3(LINKS_PLANILHAS["Forward"])
    df_return = buscar_dados_v3(LINKS_PLANILHAS["Return"])

if all(df is not None for df in [df_parcel, df_forward, df_return]):
    
    # 1. Consolidação de Pedidos (Forward + Return)
    df_consolidado_pedidos = pd.concat([df_forward, df_return], ignore_index=True)
    
    # 2. Enriquecimento com Dados de Triagem (Aba Parcel)
    # Cruzamento via SLS Tracking Number (Forward/Return) e SPX Tracking Number (Parcel)
    base_final = pd.merge(
        df_consolidado_pedidos,
        df_parcel[['SPX Tracking Number', 'Operator', 'Aging Time', 'Next Step Action', 'Scanned Status']],
        left_on='SLS Tracking Number',
        right_on='SPX Tracking Number',
        how='left'
    )

    # 3. Tratamento de Aging e Classificação de Risco
    base_final['Aging_Num'] = pd.to_numeric(base_final['Aging Time'], errors='coerce').fillna(0)
    
    def classificar_prioridade(valor):
        if valor <= 1: return "🟢 Normal (0-24h)"
        elif valor <= 2: return "🟡 Atenção (24-48h)"
        else: return "🔴 Crítico (+48h)"

    base_final['Nível de Aging'] = base_final['Aging_Num'].apply(classificar_prioridade)

    # --- INDICADORES ---
    kpi_total, kpi_critico, kpi_pendente = st.columns(3)
    total_pedidos = len(base_final)
    total_criticos = len(base_final[base_final['Aging_Num'] > 2])
    
    kpi_total.metric("Total de Pedidos", total_pedidos)
    kpi_critico.metric("Pendências Críticas (+48h)", total_criticos, delta=total_criticos, delta_color="inverse")
    kpi_pendente.metric("Aguardando Ação", base_final['Next Step Action'].notna().sum())

    # --- FILTROS E TABELA ---
    st.subheader("📋 Detalhamento para Tomada de Decisão")
    
    col_filtro_1, col_filtro_2 = st.columns(2)
    with col_filtro_1:
        filtro_aging = st.multiselect("Filtrar por Gravidade", base_final['Nível de Aging'].unique(), default=base_final['Nível de Aging'].unique())
    with col_filtro_2:
        filtro_status = st.multiselect("Filtrar por Status", base_final['Status'].unique())

    # Aplicação dos Filtros
    df_view = base_final[base_final['Nível de Aging'].isin(filtro_aging)]
    if filtro_status:
        df_view = df_view[df_view['Status'].isin(filtro_status)]

    # Colunas Estratégicas Selecionadas
    colunas_finais = [
        'Order ID', 'LM Hub Receive time', 'Status', 'Current Station', 
        'Destination Hub', 'OnHoldReason', 'Aging Time', 'Nível de Aging', 'Operator'
    ]
    
    st.dataframe(df_view[colunas_finais], use_container_width=True, hide_index=True)

    # Exportação de Relatório Consolidado
    csv = base_final.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Exportar Relatório Consolidado (CSV)", csv, "relatorio_logistico.csv", "text/csv")

else:
    st.error("Falha na conexão com os dados. Verifique se as abas da planilha estão 'Publicadas na Web' como CSV.")
    st.warning("Certifique-se de que os links inseridos no código são as URLs de publicação direta e não os links de visualização do navegador.")
