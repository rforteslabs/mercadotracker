# mercadotracker

# 🛒 Mercado Tracker - Automação e Análise de Preços

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Google Sheets API](https://img.shields.io/badge/Google_Sheets_API-34A853?style=for-the-badge&logo=google-sheets&logoColor=white)
![Looker Studio](https://img.shields.io/badge/Looker_Studio-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Cron](https://img.shields.io/badge/Cron-000000?style=for-the-badge&logo=linux&logoColor=white)

## 📌 Sobre o Projeto
O **Mercado Tracker** é uma solução automatizada de engenharia de dados e web scraping desenvolvida para monitorar, comparar e analisar preços de produtos em diferentes supermercados. 

O objetivo do projeto é economizar no mercado, além de facilitar a tomada de decisão no momento das compras, garantindo acesso rápido às informações de variação de preços diretamente pelo celular através de um dashboard interativo, alimentado por dados coletados diariamente.

Este projeto foi desenvolvido utilizando a metodologia de *AI-Assisted Development* (Vibe Coding), focando em entrega rápida de valor e arquitetura funcional.

## ⚙️ Arquitetura e Fluxo de Dados

O sistema opera em um pipeline de 4 etapas contínuas:

1. **Coleta (Scraping):** Scripts em Python acessam os portais dos mercados alvo para coletar dados brutos dos produtos e preços.
2. **Higienização (Data Cleaning):** Utilização de Expressões Regulares (**Regex**) para tratar strings complexas, limpar caracteres especiais e padronizar os dados financeiros.
3. **Armazenamento (Integração de API):** Os dados processados são enviados via API para uma base na nuvem (Google Sheets), servindo como um banco de dados leve e acessível.
4. **Visualização (B.I.):** Um dashboard construído no **Google Looker Studio** consome os dados da planilha em tempo real, permitindo filtros por produto, mercado e histórico de variação.

## 🚀 Tecnologias Utilizadas
* **Linguagem:** Python
* **Tratamento de Dados:** Regex (Expressões Regulares)
* **Integrações:** Google Sheets API
* **Automação de Infraestrutura:** CRON (Linux/Unix) para execução diária agendada
* **Data Visualization:** Google Looker Studio

## 📊 Dashboard Interativo
*Print do dashboard no Looker Studio - dashboard_mercadotracker.png*
> `[Dashboard Looker Studio](https://github.com/rforteslabs/mercadotracker/blob/main/dashboard_mercadotracker.png)`

O painel permite visualizar:
- Produtos com Menor Preço Histórico já registrado
- Compara preços do mesmo produto em mercados diferentes.
- Filtros rápidos para uso mobile (durante as compras).

## 🛠️ Como executar o projeto localmente

### Pré-requisitos
* Python 3.8+ instalado.
* Credenciais da API do Google Cloud (Arquivo exemplo `credentials_example.json`).

### Instalação

1. Clone este repositório:
```bash
git clone https://github.com/rforteslabs/mercadotracker.git
cd mercado-tracker
```
2. Crie um ambiente virtual e instale as dependências:
```bash
python -m venv venv
source venv/bin/activate  # No Windows use: venv\Scripts\activate
pip install -r requirements.txt
```
Adicione suas credenciais do Google Cloud na raiz do projeto:

3. Adicione suas credenciais do Google Cloud na raiz do projeto:
Certifique-se de que o arquivo credentials.json esteja na pasta raiz.

4. Execute o script de coleta:
```bash
python main.py
```

5. ⏱️  Automação (Job Scheduling):

Para garantir que os dados estejam sempre atualizados sem intervenção manual, o script deve ser configurado para rodar através de uma tarefa CRON no sistema operacional.
0 6 * * * /caminho/absoluto/para/o/venv/bin/python /caminho/absoluto/para/o/projeto/main.py

👨‍💻 Autor
Rodrigo Fortes dos Santos
Profissional de Tecnologia em transição para Engenharia de Software / Desenvolvimento.
