from bs4 import BeautifulSoup
import logging
import time
import re

def scrape(driver, url):
    """Realiza o scraping de um único produto do site do Rissul."""
    try:
        driver.get(url)
        time.sleep(4)  # Tempo de espera
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # --- Seletores de CSS específicos para o Rissul ---
        name_element = soup.find("h1", class_="vtex-store-components-3-x-productNameContainer")
        
        # Usando uma função lambda para encontrar a classe que contém a palavra-chave, tornando a busca mais robusta
        price_element = soup.find("p", class_=lambda c: c and "lowPrice" in c)
        wholesale_price_element = soup.find("p", class_=lambda c: c and "customPriceValue" in c)
        unit_price_element = soup.find("span", class_=lambda c: c and "calculationByWeightText" in c)

        # --- Extração dos Dados ---
        name = name_element.text.strip() if name_element else "Name not found"

        # Extrai o preço principal
        if price_element:
            price_strong = price_element.find("strong")
            price = price_strong.text.strip().replace(u'\xa0', u' ') if price_strong else "Price not found"
        else:
            price = "Price not found"

        # Extrai o preço "Clube Rissul"
        if wholesale_price_element:
            wholesale_price_strong = wholesale_price_element.find("strong")
            wholesale_price = wholesale_price_strong.text.strip().replace(u'\xa0', u' ') if wholesale_price_strong else ""
            wholesale_condition = "Clube Rissul" if wholesale_price else ""
        else:
            wholesale_price = ""
            wholesale_condition = ""
            
        # Extrai o preço por unidade
        unit_price = unit_price_element.text.strip() if unit_price_element else ""

        if name == "Name not found":
            logging.warning(f"Could not find product name for URL: {url}")
            return None

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

        return {
            "name": name,
            "price": price,
            "unit_price": unit_price,
            "unit_price_value": unit_price_value,
            "wholesale_price": wholesale_price,
            "wholesale_condition": wholesale_condition,
        }
    except Exception as e:
        logging.error(f"Error scraping Rissul URL {url}: {e}")
        return None
