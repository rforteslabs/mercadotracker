# Importa as bibliotecas BeautifulSoup para parsear HTML, logging para registrar eventos e time para pausas.
from bs4 import BeautifulSoup
import logging
import time
import re

def scrape(driver, url):
    """Realiza o scraping de um único produto do site do Atacadao."""
    try:
        # Navega até a URL fornecida.
        driver.get(url)
        # Aguarda 5 segundos para garantir que o conteúdo dinâmico (JavaScript) seja renderizado.
        time.sleep(5)
        # Cria um objeto BeautifulSoup para parsear o HTML da página.
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # --- Seletores de CSS específicos para o site do Atacadao ---
        # Encontra o elemento que contém o nome do produto.
        name_element = soup.find("h1", {"data-test": "product-details-title"})
        # Encontra o elemento <p> que contém o preço de venda.
        price_element = soup.find("p", class_="text-2xl")
        # Encontra o elemento <p> que contém o preço por unidade (ex: R$ 10,00/kg).
        unit_price_element = soup.find("p", class_="text-base leading-[1rem] text-neutral-500")
        # ---------------------------------------------------------

        # Extrai o texto do elemento do nome, se encontrado.
        name = name_element.text.strip() if name_element else "Name not found"

        # Verifica se o elemento de preço foi encontrado.
        if price_element:
            price = price_element.text.strip()
        else:
            price = "Price not found"
            
        # Extrai o texto do preço por unidade, se encontrado.
        unit_price = unit_price_element.text.strip() if unit_price_element else "Unit Price not found"

        # Se o nome do produto não for encontrado, registra um aviso e retorna None.
        if name == "Name not found":
            logging.warning(f"Could not find product name for URL: {url}")
            return None

        unit_price_value = 0.0
        if unit_price and unit_price != "Unit Price not found":
            # Tenta encontrar o valor numérico na string do preço por unidade.
            match = re.search(r"([0-9]+(?:[.,][0-9]{1,3})?)", unit_price)
            if match:
                # Converte o valor encontrado para float, substituindo vírgula por ponto.
                try:
                    unit_price_value = float(match.group(1).replace(",", "."))
                except (ValueError, IndexError):
                    unit_price_value = 0.0

        # Retorna um dicionário com os dados extraídos.
        return {
            "name": name,
            "price": price,
            "unit_price": unit_price,
            "unit_price_value": unit_price_value,
        }
    except Exception as e:
        # Em caso de qualquer erro durante o scraping, registra a exceção e retorna None.
        logging.error(f"Error scraping Atacadao URL {url}: {e}")
        return None
