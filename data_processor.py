import logging
import re
import json
import os
from datetime import datetime
from collections import Counter

def parse_price(price_str):
    """Converte uma string de preço (ex: 'R$ 1.234,56' ou '1234.56') para um número float (ex: 1234.56)."""
    if not price_str or price_str == "Price not found":
        return 0.0
    
    cleaned_price = price_str.replace("R$", "").strip()

    if "," in cleaned_price and "." in cleaned_price:
        if cleaned_price.find(".") < cleaned_price.find(","):
            cleaned_price = cleaned_price.replace(".", "").replace(",", ".")
        else:
            cleaned_price = cleaned_price.replace(",", "")
    elif "," in cleaned_price:
        cleaned_price = cleaned_price.replace(",", ".")
    
    try:
        return float(cleaned_price)
    except ValueError:
        logging.error(f"Could not parse price: {price_str} (cleaned: {cleaned_price})")
        return 0.0

def load_category_maps():
    """Carrega os mapeamentos de categoria do arquivo categories.json."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "categories.json")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            maps = json.load(f)
        
        keywords_to_product = maps.get("keywords_to_product", {})
        classification_to_subcategory = maps.get("classification_to_subcategory", {})
        classification_to_group = maps.get("classification_to_group", {})
        group_to_area = maps.get("group_to_area", {})
        subcategory_to_main_category = maps.get("subcategory_to_main_category", {})
        
        return keywords_to_product, classification_to_subcategory, classification_to_group, group_to_area, subcategory_to_main_category
        
    except FileNotFoundError:
        logging.error("Error: categories.json not found. Please create it.")
        return {}, {}, {}, {}, {}
    except json.JSONDecodeError:
        logging.error("Error: Could not decode categories.json. Please check its format.")
        return {}, {}, {}, {}, {}

def get_standardized_product(product_name, keywords_to_product_map):
    """Encontra o nome padronizado do produto com base em palavras-chave ou expressões regulares."""
    product_name_lower = product_name.lower()
    sorted_keywords = sorted(keywords_to_product_map.keys(), key=len, reverse=True)
    
    for keyword in sorted_keywords:
        try:
            # A flag (?i) no padrão de regex já lida com a insensibilidade a maiúsculas/minúsculas.
            # A busca deve ser feita no nome original do produto, sem usar .lower() no padrão.
            if re.search(keyword, product_name):
                return keywords_to_product_map[keyword]
        except re.error:
            # O fallback para palavras-chave que não são regex continua usando a versão em minúsculas.
            keyword_parts = keyword.lower().split()
            if all(part in product_name_lower for part in keyword_parts):
                return keywords_to_product_map[keyword]
            
    return "Produto Não Classificado"

def get_subcategory_from_product(standardized_product, classification_to_subcategory_map):
    """Encontra a sub-categoria para um produto padronizado."""
    return classification_to_subcategory_map.get(standardized_product, "Subcategoria Não Classificada")

def get_full_category_path(subcategory, classification_to_group, group_to_area, subcategory_to_main_category):
    """Navega pela hierarquia de categorias para encontrar o caminho completo."""
    default_path = {
        "Categoria Grupo": "Outros",
        "Categoria Área": "Outros",
        "Categoria Principal": "Outros"
    }
    
    if subcategory == "Subcategoria Não Classificada":
        return default_path

    group = classification_to_group.get(subcategory)
    if not group: return default_path
        
    area = group_to_area.get(group)
    if not area: return default_path

    main_category = subcategory_to_main_category.get(area)
    if not main_category: return default_path

    return {
        "Categoria Grupo": group,
        "Categoria Área": area,
        "Categoria Principal": main_category
    }

def calculate_best_buy_days(all_records):
    """Analisa todos os registros históricos para determinar o melhor dia da semana para comprar cada produto."""
    products_data = {}
    for record in all_records:
        name = record.get("Nome")
        if not name: continue
        if name not in products_data:
            products_data[name] = []
        products_data[name].append(record)

    best_day_map = {}
    dias_semana = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]

    for name, records in products_data.items():
        if not records: continue

        valid_records = []
        for record in records:
            price = parse_price(record.get("Preco"))
            if price > 0:
                try:
                    datetime.fromisoformat(record.get("Data")).date()
                    valid_records.append(record)
                except (ValueError, TypeError):
                    continue
        
        if not valid_records: continue

        distinct_prices = set(parse_price(r.get("Preco")) for r in valid_records)
        if len(distinct_prices) <= 1:
            best_day_map[name] = "Indefinido"
            continue

        min_price = min(parse_price(r.get("Preco")) for r in valid_records)
        
        min_price_days = []
        for record in valid_records:
            if parse_price(record.get("Preco")) == min_price:
                date_obj = datetime.fromisoformat(record.get("Data")).date()
                min_price_days.append(dias_semana[date_obj.weekday()])

        if min_price_days:
            day_counts = Counter(min_price_days)
            most_common_items = day_counts.most_common(2)
            
            if len(most_common_items) > 1 and most_common_items[0][1] == most_common_items[1][1]:
                best_day_map[name] = "Indefinido"
            else:
                best_day_map[name] = most_common_items[0][0]

    return best_day_map

def calculate_best_market_per_subcategory(all_records):
    """Analisa todos os registros históricos para determinar o melhor mercado para comprar produtos de cada subcategoria."""
    subcategory_market_prices = {}
    for record in all_records:
        subcategory = record.get("Sub-categoria")
        market = record.get("Mercado")
        price = parse_price(record.get("Preco"))

        if not all([subcategory, market, price > 0]): continue

        if subcategory not in subcategory_market_prices:
            subcategory_market_prices[subcategory] = {}
        
        if market not in subcategory_market_prices[subcategory]:
            subcategory_market_prices[subcategory][market] = []
        
        subcategory_market_prices[subcategory][market].append(price)

    best_market_map = {}
    for subcategory, markets in subcategory_market_prices.items():
        market_median_prices = {}
        for market, prices in markets.items():
            if prices:
                sorted_prices = sorted(prices)
                n = len(sorted_prices)
                median = sorted_prices[n // 2] if n % 2 == 1 else (sorted_prices[n // 2 - 1] + sorted_prices[n // 2]) / 2
                market_median_prices[market] = median
        
        if market_median_prices:
            best_market = min(market_median_prices, key=market_median_prices.get)
            best_market_map[subcategory] = best_market

    return best_market_map

def process_daily_data(new_products_data):
    """Executa o pós-processamento nos dados coletados no dia."""
    if not new_products_data:
        return []

    logging.info("Post-processing subcategory prices...")
    products_by_subcategory = {}
    for product in new_products_data:
        subcat = product["Sub-categoria"]
        if subcat not in products_by_subcategory:
            products_by_subcategory[subcat] = []
        products_by_subcategory[subcat].append(product)

    for subcat, products_in_subcat in products_by_subcategory.items():
        if not products_in_subcat:
            continue
        
        min_price_in_subcat = float('inf')
        for p in products_in_subcat:
            price = parse_price(p["Preco"])
            if 0 < price < min_price_in_subcat:
                min_price_in_subcat = price

        best_markets = []
        for p in products_in_subcat:
            if parse_price(p["Preco"]) == min_price_in_subcat:
                p["Menor Preco na Sub-categoria"] = "Sim"
                if p["Mercado"] not in best_markets:
                    best_markets.append(p["Mercado"])

        best_markets_str = ", ".join(best_markets)
        for p in products_in_subcat:
            p["Melhor Mercado na Sub-categoria (Atual)"] = best_markets_str
            if min_price_in_subcat != float('inf'):
                p["Menor Preco Sub-categoria (Valor)"] = f"R$ {min_price_in_subcat:.2f}".replace(".", ",")
            else:
                p["Menor Preco Sub-categoria (Valor)"] = "N/A"

    # Itera novamente para encontrar o melhor preço por unidade
    for subcat, products_in_subcat in products_by_subcategory.items():
        if not products_in_subcat:
            continue

        # Encontra o menor preço por unidade na subcategoria, ignorando valores não positivos
        min_unit_price_in_subcat = float('inf')
        for p in products_in_subcat:
            unit_price = p.get("Preco por Unidade (Valor)", 0.0)
            if 0 < unit_price < min_unit_price_in_subcat:
                min_unit_price_in_subcat = unit_price
        
        best_unit_price_markets_str = "Indefinido" # Inicializa como "Indefinido"
        # Se um menor preço unitário foi encontrado, marca os produtos correspondentes
        if min_unit_price_in_subcat != float('inf'):
            best_unit_price_markets = []
            for p in products_in_subcat:
                if p.get("Preco por Unidade (Valor)") == min_unit_price_in_subcat:
                    p["Menor Preco por Unidade na Sub-categoria"] = "Sim"
                    if p["Mercado"] not in best_unit_price_markets:
                        best_unit_price_markets.append(p["Mercado"])

            # Define a string dos melhores mercados para o preço por unidade
            if best_unit_price_markets: # Só atualiza se houver mercados válidos
                best_unit_price_markets_str = ", ".join(best_unit_price_markets)
        
        # Atribui o resultado a todos os produtos da subcategoria
        for p in products_in_subcat:
            p["Melhor Mercado por Unidade na Sub-categoria (Atual)"] = best_unit_price_markets_str
            
    return new_products_data

def enrich_product_data(product_data, products_history, category_maps, analysis_maps):
    """Enriches a single product's data with historical analysis and categorization."""
    
    (keywords_to_product, 
     classification_to_subcategory, 
     classification_to_group, 
     group_to_area, 
     subcategory_to_main_category) = category_maps
    
    best_buy_day_map, best_market_map = analysis_maps

    name = product_data["name"]
    market = product_data["market"]
    url = product_data["url"]
    current_price = parse_price(product_data["price"])

    # Disregard products with 0.0 price
    if current_price == 0.0:
        logging.info(f"Ignoring product with 0.0 price: {name} from {market}")
        return "IGNORED"
    
    current_unit_price = product_data.get("unit_price", "")
    unit_price_value = product_data.get("unit_price_value", 0.0)
    
    today_obj = datetime.now().date()
    today_str = today_obj.isoformat()
    dias_semana = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    dia_semana_str = dias_semana[today_obj.weekday()]

    # Categorization
    standardized_product = get_standardized_product(name, keywords_to_product)
    subcategory = get_subcategory_from_product(standardized_product, classification_to_subcategory)
    category_path = get_full_category_path(subcategory, classification_to_group, group_to_area, subcategory_to_main_category)

    # Historical analysis
    history = products_history.get(name, [])
    
    if not history:
        status_preco_mediano = "Adicionado recentemente"
        all_prices = [current_price] if current_price > 0 else []
        maior_preco = current_price
        menor_preco = current_price
        preco_mediano = current_price
    else:
        historical_prices = sorted([p["price"] for p in history if p["price"] > 0])
        all_prices = historical_prices + ([current_price] if current_price > 0 else [])
        
        maior_preco = max(all_prices) if all_prices else 0
        
        menor_preco_historico = historical_prices[0] if historical_prices else float('inf')
        menor_preco = min(all_prices) if all_prices else 0

        preco_mediano = 0
        if historical_prices:
            n = len(historical_prices)
            preco_mediano = historical_prices[n // 2] if n % 2 == 1 else (historical_prices[n // 2 - 1] + historical_prices[n // 2]) / 2

        if current_price > 0 and current_price <= menor_preco_historico:
            status_preco_mediano = "Menor Preço Histórico"
        elif preco_mediano > 0 and current_price > preco_mediano:
            status_preco_mediano = "Acima da média"
        elif preco_mediano > 0 and current_price < preco_mediano:
            status_preco_mediano = "Abaixo da média"
        else:
            status_preco_mediano = "Preço Médio"

    variacao_mediana_percent = 0.0
    if preco_mediano > 0 and history:
        variacao_mediana_percent = ((current_price - preco_mediano) / preco_mediano) * 100

    # Desco specific logic
    if market == "Desco" and abs(variacao_mediana_percent) > 100:
        logging.info(f"Ignoring Desco product with price variation > 100%: {name}")
        return "IGNORED"

    variacao = "Manteve"
    variacao_percent = 0.0
    if history:
        history.sort(key=lambda x: x['date'], reverse=True)
        last_price = history[0]["price"]
        if current_price > last_price:
            variacao = "Aumentou"
            if last_price > 0:
                variacao_percent = ((current_price - last_price) / last_price) * 100
        elif current_price < last_price:
            variacao = "Baixou"
            if last_price > 0:
                variacao_percent = ((current_price - last_price) / last_price) * 100
    else:
        variacao = "Novo"

    melhor_dia_compra = best_buy_day_map.get(name, "Indefinido")
    melhor_mercado_subcategoria = best_market_map.get(subcategory, "Indefinido")
    
    new_product_entry = {
        "Nome": name,
        "Preco": f"R$ {current_price:.2f}".replace(".", ","),
        "Preco por Unidade": current_unit_price,
        "Preco por Unidade (Valor)": unit_price_value,
        "Data": today_str,
        "Dia da Semana": dia_semana_str,
        "Melhor dia para compra": melhor_dia_compra,
        "Mercado": market,
        "Link": url,
        "Produto": standardized_product,
        "Sub-categoria": subcategory,
        "Categoria Grupo": category_path["Categoria Grupo"],
        "Categoria Área": category_path["Categoria Área"],
        "Categoria Principal": category_path["Categoria Principal"],
        "Maior Preco": f"R$ {maior_preco:.2f}".replace(".", ","),
        "Menor Preco": f"R$ {menor_preco:.2f}".replace(".", ","),
        "Preco Media": f"R$ {preco_mediano:.2f}".replace(".", ","),
        "Status Preco Media": status_preco_mediano,
        "Variacao em relacao a Media": f"{variacao_mediana_percent:.2f}%",
        "Preco Atacado": product_data.get("wholesale_price", ""),
        "Condicao Atacado": product_data.get("wholesale_condition", ""),
        "Variacao do preco": variacao,
        "Variacao em %": f"{variacao_percent:.2f}%",
        "Menor Preco na Sub-categoria": "Não",
        "Melhor Mercado na Sub-categoria (Atual)": "",
        "Menor Preco por Unidade na Sub-categoria": "Não",
        "Melhor Mercado por Unidade na Sub-categoria (Atual)": "",
        "Melhor Mercado na Média da Sub-categoria": melhor_mercado_subcategoria
    }
    
    return new_product_entry
