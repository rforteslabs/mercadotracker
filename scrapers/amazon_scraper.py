# Importa as bibliotecas BeautifulSoup para parsear HTML, logging para registrar eventos e time para pausas.
from bs4 import BeautifulSoup
import logging
import time
import re

def scrape(driver, url):
    """Realiza o scraping de um único produto do site da Amazon."""
    try:
        # Navega até a URL fornecida.
        driver.get(url)
        # Aguarda 5 segundos para garantir que o conteúdo dinâmico (JavaScript) seja renderizado.
        time.sleep(5)
        # Cria um objeto BeautifulSoup para parsear o HTML da página.
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Check for "Nenhuma opção de compra em destaque"
        unavailable_message = soup.find(string=lambda text: text and "Nenhuma opção de compra em destaque" in text)
        if unavailable_message:
            logging.info(f"Product unavailable for purchase (no featured option) for URL: {url}. Skipping.")
            return "UNAVAILABLE"

        # --- Seletores de CSS específicos para o site da Amazon ---
        # Encontra o elemento que contém o nome do produto.
        name_element = soup.find("span", id="productTitle")
        # Encontra o elemento <span> que contém o preço de venda.
        price_element = soup.find("span", class_="a-price aok-align-center reinventPricePriceToPayMargin priceToPay")
        # Encontra o elemento que contém o preço por unidade (ex: R$ 10,00/kg).
        unit_price_container = soup.find("span", class_="a-size-mini a-color-base aok-align-center pricePerUnit")
        # ---------------------------------------------------------

        # Extrai o texto do elemento do nome, se encontrado.
        name = name_element.text.strip() if name_element else "Name not found"

        # Verifica se o elemento de preço foi encontrado.
        if price_element:
            # O preço principal está dentro de um span com a classe a-offscreen, ou diretamente no texto do elemento.
            # Vamos tentar pegar o texto completo do elemento principal.
            price = price_element.text.strip()
        else:
            price = "Price not found"
            
        # Extrai o texto do preço por unidade, se encontrado.
        unit_price = "Unit Price not found"
        if unit_price_container:
            full_text = unit_price_container.text.strip()
            # Regex para encontrar "R$X,XX / unidade" ou "R$X,XX / kg" etc.
            match = re.search(r"(R\$\d{1,3}(?:\.\d{3})*,\d{2}\s*/\s*\w+)", full_text)
            if match:
                unit_price = match.group(1)
            else:
                # Fallback para pegar apenas a parte numérica se o regex falhar
                numerical_price_span = unit_price_container.find("span", class_="a-offscreen")
                if numerical_price_span:
                    unit_price = numerical_price_span.text.strip()

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
        logging.error(f"Error scraping Amazon URL {url}: {e}")
        return None
