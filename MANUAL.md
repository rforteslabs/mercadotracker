# Manual de Uso - Mercado Tracker

Este script foi desenvolvido para automatizar a coleta de preços de produtos do site Zaffari e registrar os dados em uma planilha do Google.

## Execução Padrão

Para executar o script em seu modo padrão (coletando todos os produtos novos do arquivo `config.py`), utilize o comando:

```bash
python3 scraper.py
```

O script irá pular automaticamente os produtos que já foram coletados na data atual.

## Argumentos de Linha de Comando

O script aceita argumentos para modificar seu comportamento padrão, tornando-o mais flexível.

### 1. `--force`

Força a coleta de **todos** os produtos, mesmo que já tenham sido registrados na data de hoje. É útil para garantir que todos os dados sejam atualizados, independentemente do histórico do dia.

**Exemplo:**
```bash
python3 scraper.py --force
```

### 2. `--file <caminho_do_arquivo>`

Executa a coleta apenas para uma lista de URLs especificada em um arquivo de texto. As URLs devem estar uma por linha. Este comando é especialmente útil para tentar novamente a coleta de produtos que falharam, utilizando o arquivo `failed_urls.txt` gerado pelo próprio script.

**Exemplo:**
```bash
python3 scraper.py --file failed_urls.txt
```

### 3. `--url "<URL_do_produto>"`

Executa a coleta para um **único produto**. Ideal para testes rápidos ou para verificar um item específico sem rodar o script completo. A URL deve estar entre aspas.

**Exemplo:**
```bash
python3 scraper.py --url "https://www.zaffari.com.br/arroz-branco-namorado-1kg-1014575/p"
```

---

## Arquivos Gerados

- **`mercado_tracker.log`**: Contém o registro detalhado de toda a execução do script, incluindo informações, avisos e erros. Essencial para depuração.
- **`failed_urls.txt`**: Se alguma coleta de URL falhar, este arquivo será criado com a lista de URLs que não puderam ser processadas.
- **`categories.json`**: Arquivo de configuração para o mapeamento de categorias e subcategorias. Para adicionar ou alterar categorias, edite este arquivo.