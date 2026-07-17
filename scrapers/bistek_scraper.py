# Importa as bibliotecas BeautifulSoup para parsear HTML, logging para registrar eventos e time para pausas.
from bs4 import BeautifulSoup
import logging
import time
import re

def scrape(driver, url):
    """Realiza o scraping de um único produto do site do Bistek."""
    try:
        # Navega até a URL fornecida.
        driver.get(url)
        # Aguarda 5 segundos para garantir que o conteúdo dinâmico (JavaScript) seja renderizado.
        time.sleep(5)
        # Cria um objeto BeautifulSoup para parsear o HTML da página.
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Check for "Produto indisponível"
        # Look for a div or span that contains the text "Produto indisponível"
        unavailable_element = soup.find(lambda tag: tag.name in ["div", "span"] and "Produto indisponível" in tag.get_text())
        if unavailable_element:
            return "UNAVAILABLE"
        # Encontra o elemento que contém o nome do produto.
        name_element = soup.find("h1", class_="vtex-store-components-3-x-productNameContainer")
        # Encontra o elemento <span> que contém o preço de venda.
        price_element = soup.find("span", class_="vtex-product-price-1-x-currencyContainer--pdp")
        # Encontra o elemento que contém o preço por unidade (ex: R$ 10,00/kg).
        # Encontra o elemento que contém o preço por unidade (ex: R$ 10,00/kg).
        unit_price_element = soup.find("div", class_="bistek-custom-apps-0-x-pricePerKiloLiter")
        # ---------------------------------------------------------

        # Extrai o texto do elemento do nome, se encontrado.
        name = name_element.text.strip() if name_element else "Name not found"

        # Verifica se o elemento de preço foi encontrado.
        if price_element:
            price = price_element.text.strip()
        else:
            price = "Price not found"
            
        # Extrai o texto do preço por unidade, se encontrado.
        if unit_price_element:
            unit_price = unit_price_element.text.strip()
        else:
            unit_price = ""

        unit_price_value = 0.0
        if unit_price:
            # Tenta encontrar o valor numérico na string do preço por unidade.
            match = re.search(r"([0-9]+(?:[.,][0-9]{1,3})?)", unit_price)
            if match:
                # Converte o valor encontrado para float, substituindo vírgula por ponto.
                try:
                    unit_price_value = float(match.group(1).replace(",", "."))
                except (ValueError, IndexError):
                    unit_price_value = 0.0
        
        # Se o nome do produto não for encontrado, registra um aviso e retorna None.
        if name == "Name not found":
            logging.warning(f"Could not find product name for URL: {url}")
            return None

        # Retorna um dicionário com os dados extraídos.
        return {
            "name": name,
            "price": price,
            "unit_price": unit_price,
            "unit_price_value": unit_price_value,
        }
    except Exception as e:
        # Em caso de qualquer erro durante o scraping, registra a exceção e retorna None.
        logging.error(f"Error scraping Bistek URL {url}: {e}")
        return None