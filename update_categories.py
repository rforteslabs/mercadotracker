import logging
import re
import json
import os
import gspread
from google.oauth2 import service_account
from collections import Counter

# --- Configurações Globais ---
# Copiadas de main.py para manter a independência do script
SPREADSHEET_NAME = "MercadoTracker"
WORKSHEET_NAME = "RegistroMercado"
CREDENTIALS_FILE = "credentials.json"
# ----------------------------------------------------

# --- Funções de Conexão com a Planilha (copiado de main.py) ---
def get_google_sheet_client():
    """Autentica-se na API do Google Sheets e retorna um cliente gspread."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    creds_path = os.path.join(script_dir, CREDENTIALS_FILE)
    
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scope)
        client = gspread.authorize(creds)
        return client
    except FileNotFoundError:
        logging.critical(f"Arquivo de credenciais '{CREDENTIALS_FILE}' não encontrado. Verifique o caminho.")
        return None
    except Exception as e:
        logging.critical(f"Falha ao autenticar com o Google Sheets: {e}")
        return None

# --- Funções de Categorização (copiadas de data_processor.py) ---
def load_category_maps():
    """Carrega os mapeamentos de categoria do arquivo categories.json."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "categories.json")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            maps = json.load(f)
        
        return (
            maps.get("keywords_to_product", {}),
            maps.get("classification_to_subcategory", {}),
            maps.get("classification_to_group", {}),
            maps.get("group_to_area", {}),
            maps.get("subcategory_to_main_category", {})
        )
    except FileNotFoundError:
        logging.error("Erro: categories.json não encontrado.")
        return {}, {}, {}, {}, {}
    except json.JSONDecodeError:
        logging.error("Erro: Falha ao decodificar categories.json.")
        return {}, {}, {}, {}, {}

def get_standardized_product(product_name, keywords_to_product_map):
    """Encontra o nome padronizado do produto com base em palavras-chave ou expressões regulares."""
    product_name_lower = product_name.lower()
    sorted_keywords = sorted(keywords_to_product_map.keys(), key=len, reverse=True)
    
    for keyword in sorted_keywords:
        try:
            if re.search(keyword, product_name, re.IGNORECASE):
                return keywords_to_product_map[keyword]
        except re.error:
            keyword_parts = keyword.lower().split()
            if all(part in product_name_lower for part in keyword_parts):
                return keywords_to_product_map[keyword]
    return "Produto Não Classificado"

def get_subcategory_from_product(standardized_product, classification_to_subcategory_map):
    """Encontra a sub-categoria para um produto padronizado."""
    return classification_to_subcategory_map.get(standardized_product, "Subcategoria Não Classificada")

def get_full_category_path(subcategory, classification_to_group, group_to_area, subcategory_to_main_category):
    """Navega pela hierarquia de categorias para encontrar o caminho completo."""
    default_path = {"Categoria Grupo": "Outros", "Categoria Área": "Outros", "Categoria Principal": "Outros"}
    if subcategory == "Subcategoria Não Classificada": return default_path
    group = classification_to_group.get(subcategory)
    if not group: return default_path
    area = group_to_area.get(group)
    if not area: return default_path
    main_category = subcategory_to_main_category.get(area)
    if not main_category: return default_path
    return {"Categoria Grupo": group, "Categoria Área": area, "Categoria Principal": main_category}

def get_product_categorization(product_name, category_maps):
    """Orquestra a categorização completa de um produto."""
    (keywords_to_product, classification_to_subcategory, classification_to_group, 
     group_to_area, subcategory_to_main_category) = category_maps
    
    standardized_product = get_standardized_product(product_name, keywords_to_product)
    subcategory = get_subcategory_from_product(standardized_product, classification_to_subcategory)
    category_path = get_full_category_path(subcategory, classification_to_group, group_to_area, subcategory_to_main_category)
    
    return {
        "Produto": standardized_product,
        "Sub-categoria": subcategory,
        "Categoria Grupo": category_path.get("Categoria Grupo", "Outros"),
        "Categoria Área": category_path.get("Categoria Área", "Outros"),
        "Categoria Principal": category_path.get("Categoria Principal", "Outros"),
    }

# --- Lógica Principal do Script ---
def main():
    """
    Script principal para ler a planilha, re-categorizar todos os produtos
    e atualizar as células que foram modificadas.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logging.info("Iniciando script de atualização de categorias...")
    
    client = get_google_sheet_client()
    if not client:
        return

    try:
        spreadsheet = client.open(SPREADSHEET_NAME)
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
    except gspread.exceptions.SpreadsheetNotFound:
        logging.critical(f"Planilha '{SPREADSHEET_NAME}' não encontrada.")
        return
    except gspread.exceptions.WorksheetNotFound:
        logging.critical(f"Aba '{WORKSHEET_NAME}' não encontrada na planilha.")
        return
        
    logging.info("Lendo todos os dados da planilha...")
    all_data = worksheet.get_all_values()
    headers = all_data[0]
    records = all_data[1:]
    
    logging.info(f"{len(records)} registros encontrados.")

    try:
        # Mapeia os nomes dos cabeçalhos para seus índices (coluna 1 = índice 0)
        header_map = {header: i for i, header in enumerate(headers)}
        required_cols = ["Nome", "Produto", "Sub-categoria", "Categoria Grupo", "Categoria Área", "Categoria Principal"]
        for col in required_cols:
            if col not in header_map:
                logging.critical(f"Coluna obrigatória '{col}' não encontrada na planilha. Saindo.")
                return
    except IndexError:
        logging.critical("A planilha parece estar vazia ou sem cabeçalhos. Saindo.")
        return

    logging.info("Carregando mapas de categoria do arquivo 'categories.json'...")
    category_maps = load_category_maps()
    if not category_maps[0]: # Se o mapa de keywords estiver vazio
        logging.critical("Os mapas de categoria não puderam ser carregados. Verifique o 'categories.json'. Saindo.")
        return

    cell_updates = []
    updated_rows_count = 0
    
    logging.info("Processando e comparando categorias de cada registro...")
    for i, row in enumerate(records):
        row_num = i + 2  # +1 porque o índice é 0-based, +1 porque pulamos o cabeçalho
        
        product_name = row[header_map["Nome"]]
        if not product_name:
            continue
            
        # Pega as categorias atuais da linha
        current_categories = {
            "Produto": row[header_map["Produto"]],
            "Sub-categoria": row[header_map["Sub-categoria"]],
            "Categoria Grupo": row[header_map["Categoria Grupo"]],
            "Categoria Área": row[header_map["Categoria Área"]],
            "Categoria Principal": row[header_map["Categoria Principal"]],
        }
        
        # Obtém as novas categorias
        new_categories = get_product_categorization(product_name, category_maps)
        
        # Compara para ver se algo mudou
        if new_categories != current_categories:
            updated_rows_count += 1
            logging.info(f"Diferença encontrada na linha {row_num} para o produto '{product_name}'. Agendando atualização.")
            
            # Adiciona as células a serem atualizadas à lista
            for cat_name, cat_value in new_categories.items():
                col_index = header_map[cat_name] + 1 # gspread usa colunas 1-based
                cell_updates.append(gspread.Cell(row_num, col_index, cat_value))

    if not cell_updates:
        logging.info("Nenhuma categoria precisou ser atualizada. Tudo em dia!")
        return
        
    logging.info(f"Total de {updated_rows_count} linhas para atualizar. Enviando {len(cell_updates)} atualizações de célula para o Google Sheets...")
    
    try:
        # gspread lida com a divisão em lotes (batches) por padrão
        worksheet.update_cells(cell_updates)
        logging.info("Planilha atualizada com sucesso!")
    except Exception as e:
        logging.error(f"Ocorreu um erro ao atualizar a planilha: {e}")

if __name__ == "__main__":
    main()
