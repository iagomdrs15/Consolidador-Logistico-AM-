# 📊 Consolidador Logístico de Tomada de Decisão

Este projeto foi desenvolvido para automatizar a consolidação de relatórios operacionais (TXT/TSV) e transformar dados brutos em inteligência logística, com foco em monitoramento de **SLA** e **Aging**.

## 🚀 Funcionalidades

- **Consolidação Automática**: Une as bases de *Forward* (Saída) e *Return* (Reversa) em um único fluxo.
- **Cruzamento de Dados (Merge)**: Integra informações da aba *Parcel* para identificar operadores e tempos de triagem.
- **Cálculo de Macro Aging**: Classifica automaticamente os pacotes por nível de criticidade:
    - 🟢 **0-24h**: Fluxo Normal.
    - 🟡 **24-48h**: Atenção (Próximo ao limite).
    - 🔴 **+48h**: Crítico (Risco de estouro de SLA).
- **Filtros Dinâmicos**: Visualização por Status, Operador e Estação Atual.

## 📂 Estrutura de Arquivos Esperada

Para o correto funcionamento, o sistema espera três arquivos `.txt` com os cabeçalhos padrão:

1. `parcel.txt`: Dados de triagem e operador.
2. `forward.txt`: Dados de saída e fluxo de entrega (Last Mile).
3. `return.txt`: Dados de logística reversa.

## 🛠️ Tecnologias Utilizadas

- **Python 3.x**
- **Pandas**: Para processamento de dados e merges complexos.
- **Streamlit**: Para a interface de usuário e dashboards interativos.

## ⚙️ Como Executar

1. Clone o repositório:
   ```bash
   git clone [https://github.com/seu-usuario/nome-do-repositorio.git](https://github.com/seu-usuario/nome-do-repositorio.git)
