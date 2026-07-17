
from bs4 import BeautifulSoup
import logging
import time

def scrape(driver, url):
    """Realiza o scraping de um único produto do site da Americanas."""
    try:
        driver.get(url)
        time.sleep(2)  # Aguarda o JS renderizar o conteúdo (ajustado conforme solicitação do usuário)
            
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # --- Seletores específicos para o site da Americanas ---
        name_element = soup.find("h1", class_="ProductInfoCenter_title__hdTX_")
        
        # Tenta extrair o preço da meta tag Open Graph
        price_meta = soup.find("meta", property="product:price:amount")
        price = price_meta["content"] if price_meta else "Price not found"

        # --- Lógica de fallback para o preço ---
        if price in ("0.00", "0,00", "Price not found"):
            logging.info(f"Meta price was '{price}'. Attempting fallback for URL: {url}")
            price_element = soup.select_one("div[class*='ProductPrice_productPrice']")
            if price_element:
                price_text = price_element.get_text(strip=True)
                price = price_text.replace("R$", "").replace("\xa0", "").replace(".", "").replace(",", ".").strip()
                logging.info(f"Found fallback price: {price}")
            else:
                logging.warning(f"Fallback price selector 'div[class*=\"ProductPrice_productPrice\"]' not found for URL: {url}")

        # --- Validação final do preço ---
        # Se o preço final for 0 ou inválido, ignore o produto
        try:
            # Tenta converter o preço para um float. Se for 0 ou menor, ou se a conversão falhar, ignora.
            if float(price) <= 0:
                logging.warning(f"Price for {url} is '{price}' (<= 0), ignoring item.")
                return None
        except (ValueError, TypeError):
            # A conversão para float falhou, significa que o preço é uma string inválida (ex: "Price not found", "", " ")
            logging.warning(f"Price for {url} is '{price}' (invalid), ignoring item.")
            return None

        # --- Extração dos Dados ---
        name = name_element.text.strip() if name_element else "Name not found"
        
        # Preço por unidade não é um campo comum na Americanas
        unit_price = ""

        # Se o nome não for encontrado, é um bom indicador de que a página não carregou como esperado
        if name == "Name not found":
            logging.warning(f"Could not find product name for URL: {url}. A estrutura da página pode ter mudado.")
            return None

        return {
            "name": name,
            "price": price,
            "unit_price": unit_price,
        }
    except Exception as e:
        logging.error(f"Error scraping Americanas URL {url}: {e}")
        return None
