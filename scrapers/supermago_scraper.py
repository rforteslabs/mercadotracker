from bs4 import BeautifulSoup
import logging

def scrape(driver, url):
    """
    Scrapes product information from a Super Mago product page.

    Args:
        driver: The Selenium WebDriver instance.
        url: The URL of the product page.

    Returns:
        A dictionary containing the scraped product information (name, price, unit_price),
        or None if scraping fails.
    """
    try:
        driver.get(url)
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Encontrar o nome do produto
        name_element = soup.select_one('div.information h3')
        name = name_element.contents[0].strip() if name_element else "Name not found"

        # Encontrar o preço do produto
        price_element = soup.select_one('strong.sale-price span')
        price = price_element.text.strip() if price_element else "Price not found"

        # O preço por unidade não parece estar disponível de forma consistente
        unit_price = ""

        if name == "Name not found" or price == "Price not found":
            logging.warning(f"Could not find name or price for {url}")
            return None

        return {
            "name": name,
            "price": price,
            "unit_price": unit_price,
            "unit_price_value": 0.0
        }

    except Exception as e:
        logging.error(f"Error scraping {url}: {e}")
        return None