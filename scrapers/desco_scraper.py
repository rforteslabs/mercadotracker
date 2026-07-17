# Importa as bibliotecas BeautifulSoup para parsear HTML, logging para registrar eventos e time para pausas.
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import logging
import time
import re


def scrape(driver, url):

    """Realiza o scraping de um único produto do site Desco Atacado."""

    try:

        # Navega até a URL fornecida.

        driver.get(url)

        # Aguarda um pouco para a página carregar completamente

        # Aceita os cookies
        try:
            cookie_button = driver.find_element(By.XPATH, "//button[contains(text(), 'continuar e fechar')]")
            cookie_button.click()
            time.sleep(2) # Espera um pouco para o banner de cookies desaparecer
        except Exception as e:
            # logging.info(f"Could not find or click cookie button: {e}")
            pass # Se o botão de cookies não for encontrado, continua

        time.sleep(3) # Espera a página carregar



        # Cria um objeto BeautifulSoup para parsear o HTML da página.

        soup = BeautifulSoup(driver.page_source, "html.parser")



        # Verifica se o produto está indisponível
        aviseme_button = soup.find("button", title="Avise-me quando chegar")
        unavailable_text = soup.find(lambda tag: tag.name in ['p', 'div', 'span'] and 'Produto indisponível' in tag.get_text())
        
        if aviseme_button or unavailable_text:
            logging.warning(f"Product unavailable at Desco URL: {url}. Skipping.")
            return "UNAVAILABLE"


        # --- Seletores de CSS específicos para o site do Desco ---
        # Encontra o elemento que contém o nome do produto.
        name_element = soup.find("div", class_="text-lg font-normal mx-3 ng-star-inserted")
        # Encontra todos os elementos de preço (pode haver preço de varejo e atacado).

        price_elements = soup.find_all("span", {"data-cy": "preco"})

        # Encontra a condição para o preço de atacado (ex: "A partir de 3 unidades").

        condition_element = soup.find("div", class_="vip-oferta-tag")

        # Encontra o preço por unidade (ex: R$ 10,00/kg).

        unit_price_element = soup.find("div", {"data-cy": "preco-unidade"})

        # ---------------------------------------------------------



        # Extrai o texto do elemento do nome, se encontrado.

        name = name_element.text.strip() if name_element else "Name not found"

        

        # Inicializa as variáveis de preço.

        price_str = "Price not found"

        wholesale_price_str = ""

        

        # Processa os elementos de preço encontrados.

        if len(price_elements) > 0:

            # O primeiro preço é geralmente o preço de varejo.

            price_str = price_elements[0].text.strip()

        if len(price_elements) > 1:

            # O segundo preço, se existir, é o de atacado.

            wholesale_price_str = price_elements[1].text.strip()



        # Extrai o texto da condição de atacado e do preço unitário, se encontrados.

        condition_str = condition_element.text.strip() if condition_element else ""

        unit_price = unit_price_element.text.strip() if unit_price_element else ""



        # Se o nome do produto não for encontrado, registra um aviso e retorna None.

        if name == "Name not found":

            logging.warning(f"Could not find product name for Desco URL: {url}")

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

        # Retorna um dicionário com os dados extraídos.

        return {

            "name": name,

            "price": price_str,

            "unit_price": unit_price,

            "unit_price_value": unit_price_value,

            "wholesale_price": wholesale_price_str,

            "wholesale_condition": condition_str

        }

    except Exception as e:

        # Em caso de qualquer erro durante o scraping, registra a exceção e retorna None.

        logging.error(f"Error scraping Desco URL {url}: {e}")

        return None