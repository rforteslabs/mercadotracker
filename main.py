import pyperclip # Biblioteca para automação de área de transferência
import pywhatkit # Biblioteca para automação de WhatsApp
import smtplib  # Envio de emails
from email.mime.text import MIMEText  # Criação de corpo de email em texto
from email.mime.multipart import MIMEMultipart  # Criação de emails com múltiplas partes (HTML)
import pyautogui
import webbrowser
from urllib.parse import quote
from scrapers import zaffari_scraper, desco_scraper, bistek_scraper, supermago_scraper, rissul_scraper, amazon_scraper, americanas_scraper, atacadao_scraper  # Módulos locais de scraping
import config # Importa o módulo de configuração
from concurrent.futures import ThreadPoolExecutor, as_completed
import data_processor # Módulo local para processamento de dados
import logging # Importa o módulo logging
import argparse # Importa o módulo argparse
import subprocess # Importa o módulo subprocess
import os # Importa o módulo os
import sys # Importa o módulo sys

# Silencia os logs detalhados do webdriver-manager.
# Esta linha deve vir antes da importação do webdriver_manager para ter efeito.
os.environ['WDM_LOG_LEVEL'] = '0'

import gspread # Importa o módulo gspread
from google.oauth2 import service_account # Importa service_account do google.oauth2
from datetime import date # Importa date do módulo datetime
from collections import defaultdict # Importa defaultdict do módulo collections
import time # Importa o módulo time
from selenium import webdriver # Importa webdriver do módulo selenium
from selenium.webdriver.chrome.service import Service # Importa Service do módulo selenium.webdriver.chrome.service
from webdriver_manager.chrome import ChromeDriverManager # Importa ChromeDriverManager do módulo webdriver_manager.chrome


# --- Configurações Globais para o Google Sheets ---
SPREADSHEET_NAME = "MercadoTracker"  # Nome da planilha
WORKSHEET_NAME = "RegistroMercado"  # Nome da aba na planilha
CREDENTIALS_FILE = "credentials.json"  # Arquivo de credenciais da API do Google
# ----------------------------------------------------

def send_bulk_whatsapp_message(products):
    """Envia uma única mensagem via WhatsApp para um grupo configurado usando a área de transferência."""
    
    group_id = getattr(config, 'WHATSAPP_GROUP_ID', None)

    if not group_id:
        logging.warning("No WhatsApp Group ID configured in config.WHATSAPP_GROUP_ID. Skipping notification.")
        return
    
    if not products:
        logging.info("No significant discounts to notify via WhatsApp.")
        return

    # Monta a mensagem uma única vez.
    message = "🔥 ALERTA DE DESCONTOS SIGNIFICATIVOS! 🔥\n\n"
    
    # Classifica os produtos por nome do mercado em ordem alfabética
    products.sort(key=lambda p: p.get('Mercado', ''))

    for product in products:
        product_name = product.get('Nome', 'N/A')
        discount = product.get('Variacao em relacao a Media', 'N/A')
        price = product.get('Preco', 'N/A')
        market = product.get('Mercado', 'N/A')
        url = product.get('Link', '')
        is_cheapest = product.get("Menor Preco na Sub-categoria") == "Sim"

        message += (
            f"Produto: *{product_name}*\n"
            f"Mercado: *{market}*\n"
            f"Preço: *{price}*\n"
            f"Desconto: *{discount}* abaixo da media!\n"
        )
        if is_cheapest:
            message += f"⭐ *MAIS BARATO DA SUBCATEGORIA {product.get('Sub-categoria', 'N/A').upper()}*\n"
        
        message += (
            f"Link: {url}\n"
            f"--------------------------------------\n\n"
        )
    
    logging.info(f"WhatsApp message content prepared. Attempting to send to group ID: {group_id[:10]}...")

    try:
        # 1. Copia a mensagem para a área de transferência
        pyperclip.copy(message)
        logging.info("Message copied to clipboard.")

        # 2. Abre o WhatsApp Web diretamente no grupo
        # O link com /accept?code= é a forma como o pywhatkit e outros abrem grupos
        webbrowser.open(f'https://web.whatsapp.com/accept?code={group_id}')
        
        # 3. Espera o WhatsApp carregar
        wait_time = 25
        logging.info(f"Waiting {wait_time} seconds for WhatsApp Web to open and load the group chat...")
        time.sleep(wait_time)

        # 4. Cola a mensagem e envia
        logging.info("Pasting message from clipboard...")
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(1) # Pequena pausa antes de pressionar Enter
        
        logging.info("Pressing Enter to send...")
        pyautogui.press('enter')
        
        # 5. Espera e fecha a aba
        close_wait_time = 5
        logging.info(f"Waiting {close_wait_time} seconds before closing the tab...")
        time.sleep(close_wait_time)
        pyautogui.hotkey('ctrl', 'w')
        
        logging.info(f"Successfully sent notification to WhatsApp group {group_id[:10]}.")

    except Exception as e:
        logging.error(f"Failed to send WhatsApp message to group {group_id[:10]}: {e}", exc_info=True)


def send_notification(title, message):
    """Envia uma notificação para o desktop do usuário (apenas Linux)."""
    try:
        # Tenta executar o comando 'notify-send' do sistema.
        subprocess.run(['notify-send', title, message, '--icon=info-symbolic'], check=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        # Se o comando não for encontrado ou falhar, registra um aviso.
        logging.warning(f"Could not send notification: {e}. Please ensure 'notify-send' is installed.")


def send_email_notification(products_on_sale, best_buys_by_market, significant_discounts):
    """Envia uma notificação por email com um resumo dos preços do dia."""
    
    # Verifica se há conteúdo para enviar antes de qualquer outra coisa
    if not products_on_sale and not best_buys_by_market and not significant_discounts:
        logging.info("No new deals to report, skipping email notification.")
        return

    # Carrega as credenciais de email do arquivo de configuração.
    sender_email = config.EMAIL_SENDER
    password = config.EMAIL_PASSWORD
    recipient_email = config.EMAIL_RECIPIENT
    smtp_server = config.SMTP_SERVER
    smtp_port = config.SMTP_PORT

    # Verifica se todas as configurações de email estão presentes.
    if not all([sender_email, password, recipient_email, smtp_server, smtp_port]):
        logging.warning("Email configuration is incomplete. Skipping email notification.")
        return

    # Cria a estrutura do email.
    message = MIMEMultipart("alternative")
    message["Subject"] = "Mercado Tracker - Resumo de Preços do Dia"
    message["From"] = sender_email
    message["To"] = ", ".join(recipient_email) if isinstance(recipient_email, (list, tuple)) else recipient_email

    # Monta o corpo do email em HTML.
    html = "<html><body>"
    has_content = False

    if significant_discounts:
        has_content = True
        # Sort significant_discounts by 'Mercado' (alphabetical) and then by 'Economia (%)' (largest discount first)
        significant_discounts.sort(key=lambda p: (p['Mercado'], float(p.get("Variacao em relacao a Media", "0%").replace('%', ''))))
        html += '''
        <h2>Maiores Descontos</h2>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
          <tr style="background-color: #f2f2f2;">
            <th style="padding: 8px; text-align: left;">Nome</th>
            <th style="padding: 8px; text-align: left;">Produto</th>
            <th style="padding: 8px; text-align: left;">Preco</th>
            <th style="padding: 8px; text-align: left;">Preço Médio</th>
            <th style="padding: 8px; text-align: left;">Menor Preço na Sub-Categoria</th>
            <th style="padding: 8px; text-align: left;">Mercado</th>
            <th style="padding: 8px; text-align: left;">Economia (%)</th>
            <th style="padding: 8px; text-align: left;">Link</th>
          </tr>
        '''
        for product in significant_discounts:
            html += f'''
              <tr>
                <td style="padding: 8px;">{product['Nome']}</td>
                <td style="padding: 8px;">{product['Sub-categoria']}</td>
                <td style="padding: 8px;">{product['Preco']}</td>
                <td style="padding: 8px;">{product.get('Preco Media', 'N/A')}</td>
                <td style="padding: 8px;">{product.get('Menor Preco Sub-categoria (Valor)', 'N/A')}</td>
                <td style="padding: 8px;">{product['Mercado']}</td>
                <td style="padding: 8px;">{product['Variacao em relacao a Media']}</td>
                <td style="padding: 8px;"><a href="{product['Link']}">Ver Produto</a></td>
              </tr>
            '''
        html += "</table><br><hr><br>"
    
    # Adicione aqui seções para products_on_sale e best_buys_by_market se desejar no futuro

    html += "</body></html>"

    # Se não houver conteúdo, não envie o e-mail
    if not has_content:
        logging.info("Email body is empty after processing. Skipping email notification.")
        return

    # Anexa a parte HTML ao email.
    part = MIMEText(html, "html")
    message.attach(part)

    # Tenta enviar o email usando o servidor SMTP configurado.
    try:
        logging.info(f"Sending email notification to {recipient_email}...")
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Inicia a criptografia TLS.
            server.login(sender_email, password)  # Faz login no servidor.
            recipients = recipient_email if isinstance(recipient_email, (list, tuple)) else [recipient_email]
            server.sendmail(sender_email, recipients, message.as_string())  # Envia o email.
        logging.info("Email sent successfully!")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")


def scrape_product(driver, url):
    """
    Função despachante: chama o scraper apropriado com base na URL do produto.
    """
    if "zaffari.com.br" in url:
        return zaffari_scraper.scrape(driver, url)

    elif "desco.com.br" in url:
        return desco_scraper.scrape(driver, url)
    elif "rissul.com.br" in url:
        return rissul_scraper.scrape(driver, url)
    elif "supermago.com.br" in url:
        return supermago_scraper.scrape(driver, url)
    elif "bistek.com.br" in url:
        return bistek_scraper.scrape(driver, url)
    elif "amazon.com.br" in url or "a.co" in url:
        return amazon_scraper.scrape(driver, url)
    elif "americanas.com.br" in url:
        return americanas_scraper.scrape(driver, url)
    elif "atacadao.com.br" in url:
        return atacadao_scraper.scrape(driver, url)
    else:
        logging.warning(f"No scraper available for URL: {url}")
        return None

def get_google_sheet_client():
    """Autentica-se na API do Google Sheets e retorna um cliente gspread."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    creds_path = os.path.join(script_dir, CREDENTIALS_FILE)
    
    # Define os escopos de permissão necessários.
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Cria as credenciais a partir do arquivo de conta de serviço.
    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scope)
    # Autoriza e retorna o cliente.
    client = gspread.authorize(creds)
    return client

def write_to_google_sheet(data):
    """Escreve uma lista de dicionários na planilha do Google especificada."""
    # Obtém o cliente autenticado.
    client = get_google_sheet_client()
    spreadsheet = client.open(SPREADSHEET_NAME)
    worksheet = spreadsheet.worksheet(WORKSHEET_NAME)

    # Lê os cabeçalhos existentes na planilha.
    existing_headers = worksheet.row_values(1)
    
    fieldnames = ["Nome", "Preco", "Preco por Unidade", "Preco por Unidade (Valor)", "Data", "Dia da Semana", "Melhor dia para compra", "Mercado", "Link", "Produto", "Sub-categoria", "Categoria Grupo", "Categoria Área", "Categoria Principal", "Maior Preco", "Menor Preco", "Preco Media", "Status Preco Media", "Variacao em relacao a Media", "Variacao do preco", "Variacao em %", "Menor Preco na Sub-categoria", "Melhor Mercado na Sub-categoria (Atual)", "Menor Preco Sub-categoria (Valor)", "Menor Preco por Unidade na Sub-categoria", "Melhor Mercado por Unidade na Sub-categoria (Atual)", "Melhor Mercado na Média da Sub-categoria", "Preco Atacado", "Condicao Atacado"]

    # Se a planilha estiver vazia, escreve os cabeçalhos.
    if not existing_headers:
        worksheet.append_row(fieldnames)
        logging.info("Headers written to Google Sheet.")
    else:
        # Verifica se há novas colunas a serem adicionadas.
        new_columns_to_add = [field for field in fieldnames if field not in existing_headers]
        if new_columns_to_add:
            current_header_row = worksheet.row_values(1)
            current_header_row.extend(new_columns_to_add)
            worksheet.update('1:1', [current_header_row]) # Atualiza a primeira linha com os novos cabeçalhos.
            logging.info(f"Added new headers to Google Sheet: {new_columns_to_add}")

    # Prepara as linhas para serem escritas na planilha.
    rows_to_write = []
    for entry in data:
        # Garante que a ordem das colunas corresponda aos cabeçalhos.
        row = [entry.get(field, "") for field in fieldnames]
        rows_to_write.append(row)
    
    # Escreve todas as novas linhas de uma vez para otimizar as chamadas de API.
    if rows_to_write:
        worksheet.append_rows(rows_to_write)
        logging.info(f"{len(rows_to_write)} rows written to Google Sheet.")
    else:
        logging.info("No new data to write to Google Sheet.")


def read_historical_data_from_sheet():
    """Lê todos os dados históricos da planilha do Google e os retorna."""
    client = get_google_sheet_client()
    spreadsheet = client.open(SPREADSHEET_NAME)
    worksheet = spreadsheet.worksheet(WORKSHEET_NAME)

    # Obtém todos os registros da planilha como uma lista de dicionários.
    records = worksheet.get_all_records()

    # Processa os registros para criar um dicionário de histórico de preços por produto.
    products_history = {}
    for row in records:
        name = row.get("Nome")
        price_str = row.get("Preco")
        date_str = row.get("Data")

        if name and price_str and date_str:
            if name not in products_history:
                products_history[name] = []
            products_history[name].append({
                "price": data_processor.parse_price(price_str),
                "date": date_str
            })
    return products_history, records


def get_progress_bar(current, total, bar_length=40):
    """Gera uma string de barra de progresso formatada."""
    fraction = current / total
    filled_length = int(fraction * bar_length)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    percentage = f"{(fraction * 100):.2f}%"
    return f"|{bar}| {current}/{total} ({percentage})"


def main():
    # --- 1. Configuração Inicial ---
    # Configura o sistema de logging para ser verboso no arquivo e limpo no console.
    log_formatter = logging.Formatter('%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')

    # Handler para o arquivo de log (INFO e acima)
    file_handler = logging.FileHandler("mercado_tracker.log", mode='a', encoding='utf-8')
    file_handler.setFormatter(log_formatter)
    
    # Handler para o console (WARNING e acima) para uma saída mais limpa
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(log_formatter)

    # Configura o logger raiz
    logging.basicConfig(
        level=logging.INFO, # O nível do logger principal deve ser o mais baixo (INFO aqui)
        handlers=[
            file_handler,
            console_handler
        ]
    )
    logging.getLogger('webdriver_manager').setLevel(logging.WARNING)

    # Configura o parser de argumentos da linha de comando.
    parser = argparse.ArgumentParser(description="Scrape product prices.")
    parser.add_argument('--force', action='store_true', help='Force scraping all URLs, ignoring previous scrapes on the same day.')
    parser.add_argument('--file', type=str, help='Path to a file containing a list of URLs to scrape (one URL per line).')
    parser.add_argument('--url', type=str, help='A single URL to scrape.')
    parser.add_argument('--mkt', type=str, help='Scrape URLs only from a specific market (e.g., zaffari).')
    args = parser.parse_args()

    # Envia uma notificação de início.
    send_notification("Mercado Tracker", "Iniciando a coleta de preços...")

    # --- 2. Carregamento das URLs ---
    # Determina quais URLs serão processadas com base nos argumentos fornecidos.
    urls_with_market = []
    if args.url: # Se uma única URL for fornecida.
        market = "Unknown"
        if "zaffari.com.br" in args.url: market = "Zaffari"
        elif "desco.com.br" in args.url: market = "Desco"
        elif "bistek.com.br" in args.url: market = "Bistek"
        elif "rissul.com.br" in args.url: market = "Rissul"
        elif "amazon.com.br" in args.url or "a.co" in args.url: market = "Amazon"
        elif "americanas.com.br" in args.url: market = "Americanas"
        elif "supermago.com.br" in args.url: market = "Super Mago"
        elif "atacadao.com.br" in args.url: market = "Atacadao"
        elif "carrefour.com.br" in args.url: market = "Carrefour"
        urls_with_market.append((args.url, market))
        logging.info(f"Processing single URL from command line: {args.url}")
    elif args.file: # Se um arquivo de URLs for fornecido.
        try:
            with open(args.file, 'r') as f:
                for line in f:
                    url = line.strip()
                    if url:
                        market = "Unknown"
                        if "zaffari.com.br" in url: market = "Zaffari"
                        elif "desco.com.br" in url: market = "Desco"
                        elif "bistek.com.br" in url: market = "Bistek"
                        elif "rissul.com.br" in url: market = "Rissul"
                        elif "amazon.com.br" in url or "a.co" in url: market = "Amazon"
                        elif "americanas.com.br" in url: market = "Americanas"
                        elif "supermago.com.br" in url: market = "Super Mago"
                        elif "atacadao.com.br" in url: market = "Atacadao"
                        elif "carrefour.com.br" in url: market = "Carrefour"
                        urls_with_market.append((url, market))
            logging.info(f"Processing {len(urls_with_market)} URLs from file: {args.file}")
        except FileNotFoundError:
            logging.error(f"Error: The file {args.file} was not found. Exiting.")
            return
    else: # Caso contrário, usa as URLs do arquivo de configuração.
        logging.info("Processing all URLs from config.py")
        for market, url_list in config.URLS_BY_MARKET.items():
            for url in url_list:
                urls_with_market.append((url, market))

    # Filtra por mercado se o argumento --mkt for fornecido.
    if args.mkt:
        market_arg = args.mkt.lower().replace(" ", "")
        urls_with_market = [
            (url, market) for url, market in urls_with_market
            if market.lower().replace(" ", "") == market_arg
        ]
        if not urls_with_market:
            logging.warning(f"No URLs found for market '{args.mkt}'. Check the market name. Exiting.")
            return
        logging.info(f"Filtering to scrape only the '{args.mkt}' market, {len(urls_with_market)} URLs found.")

    # --- 3. Preparação do Ambiente ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    failed_urls_file = "failed_urls.txt"
    
    logging.info("Loading category maps...")
    category_maps = data_processor.load_category_maps()
    if not category_maps[0]: # Check if keywords_to_product is empty
        logging.critical("Could not load category maps. Exiting.")
        return

    logging.info("Reading historical data from Google Sheet...")
    products_history, all_records = read_historical_data_from_sheet()

    # Analisa os dados históricos para encontrar o melhor dia de compra para cada produto.
    logging.info("Analyzing historical data to determine best buy days...")
    best_buy_day_map = data_processor.calculate_best_buy_days(all_records)

    logging.info("Analyzing historical data to determine best market per subcategory...")
    best_market_map = data_processor.calculate_best_market_per_subcategory(all_records)
    
    analysis_maps = (best_buy_day_map, best_market_map)

    # --- 4. Filtragem de URLs ---
    # Filtra URLs que já foram coletadas no dia de hoje, a menos que --force seja usado.
    urls_to_scrape_with_market = urls_with_market
    if not args.force:
        today_str = date.today().isoformat()
        # Cria um conjunto de URLs já coletadas hoje para uma verificação rápida.
        scraped_urls_today = {rec.get("Link") for rec in all_records if rec.get("Data") == today_str and rec.get("Link")}
        
        # Mantém apenas as URLs que não estão no conjunto de URLs já coletadas.
        urls_to_scrape_with_market = [(url, market) for url, market in urls_with_market if url not in scraped_urls_today]
        
        skipped_count = len(urls_with_market) - len(urls_to_scrape_with_market)
        if skipped_count > 0:
            logging.info(f"Skipping {skipped_count} URLs already scraped today.")

    # Se não houver novas URLs para coletar, encerra o script.
    if not urls_to_scrape_with_market:
        logging.info("No new URLs to scrape. Exiting.")
        return

    # --- 5. Definição da Tarefa de Scraping e Enriquecimento ---
    def scrape_url(url, market):
        driver = None
        start_time = time.time()
        duration = 0
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

            scraped_data = scrape_product(driver, url)

            if scraped_data == "UNAVAILABLE":
                return (url, "UNAVAILABLE", None, 0) # Não conta tempo para indisponíveis
            
            if not scraped_data or scraped_data["name"] == "Name not found":
                return (url, "FAILURE", None, 0) # Não conta tempo para falhas

            # Adiciona url e market ao dicionário scraped_data para uso posterior no enriquecimento
            scraped_data['url'] = url
            scraped_data['market'] = market
            
            return (url, "SUCCESS", scraped_data, time.time() - start_time)

        except Exception as e:
            logging.error(f"Exception in thread for {url}: {e}", exc_info=True)
            return (url, "FAILURE", None, time.time() - start_time)
        finally:
            duration = time.time() - start_time
            if driver:
                driver.quit()

    def process_scraped_item(url, market, products_history, category_maps, analysis_maps):
        # Primeiro, coleta os dados brutos
        url_res, status, scraped_data, duration = scrape_url(url, market)

        if status != "SUCCESS":
            return (url_res, status, None, duration) # Retorna cedo se a coleta falhou ou o produto está indisponível

        # Em seguida, enriquece os dados
        enriched_data = data_processor.enrich_product_data(scraped_data, products_history, category_maps, analysis_maps)

        if enriched_data == "IGNORED":
            return (url_res, "IGNORED", None, 0) # Ignorados não contam no tempo de coleta

        logging.info(f"Scraped: {enriched_data['Nome']} - Price: {enriched_data['Preco']} - Unit Price: {enriched_data['Preco por Unidade']} ({enriched_data['Preco por Unidade (Valor)']}) - Variacao: {enriched_data['Variacao do preco']}")
        return (url_res, "SUCCESS", enriched_data, duration)

    new_products_data = []
    failed_urls = []
    ignored_urls = []
    market_times = defaultdict(float)


    logging.info(f"Starting parallel scraping with 3 workers for {len(urls_to_scrape_with_market)} URLs...")

    total_urls = len(urls_to_scrape_with_market)
    processed_count = 0
    total_start_time = time.time()

    with ThreadPoolExecutor(max_workers=3, thread_name_prefix='Scraper') as executor:
        future_to_url = {executor.submit(process_scraped_item, url, market, products_history, category_maps, analysis_maps): (url, market) for url, market in urls_to_scrape_with_market}

        for future in as_completed(future_to_url):
            processed_count += 1
            url_info = future_to_url[future]
            market_name = url_info[1]
            
            # Exibe o progresso em uma única linha no console.
#            progress_message = f"Processing {processed_count}/{total_urls} ({(processed_count/total_urls)*100:.2f}%) products..."
#            sys.stdout.write(f"\r{progress_message.ljust(80)}")

            # Exibe a barra de progresso em uma única linha no console.
            progress_bar = get_progress_bar(processed_count, total_urls)
            sys.stdout.write(f"\r{progress_bar.ljust(80)}")
            sys.stdout.flush()

            try:
                url_res, status, data, duration = future.result()
                if duration:
                    market_times[market_name] += duration

                if status == "SUCCESS":
                    new_products_data.append(data)
                elif status == "FAILURE":
                    failed_urls.append(url_res)
                elif status == "UNAVAILABLE" or status == "IGNORED":
                    ignored_urls.append(url_res)
            except Exception as exc:
                
                logging.error(f"URL {url_info[0]} generated an exception in future: {exc}", exc_info=True)
                failed_urls.append(url_info[0])

    total_duration = time.time() - total_start_time
    total_minutes = int(total_duration // 60)
    total_seconds_remaining = total_duration % 60
    sys.stdout.write("\n") # Garante que a próxima saída comece em uma nova linha
    logging.info("Parallel scraping finished.")

    # --- Resumo dos Tempos de Coleta ---
    logging.info(f"--- Tempo Total da Coleta: {total_minutes} minutos e {total_seconds_remaining:.2f} segundos ---")
    if market_times:
        logging.info("--- Tempo de Coleta por Mercado ---")
        # Ordena os mercados pelo tempo total de coleta, do maior para o menor
        sorted_market_times = sorted(market_times.items(), key=lambda item: item[1], reverse=True)
        for market, total_time_seconds in sorted_market_times:
            market_minutes = int(total_time_seconds // 60)
            market_seconds_remaining = total_time_seconds % 60
            logging.info(f"- {market}: {market_minutes} minutos e {market_seconds_remaining:.2f} segundos")
    # -----------------------------------


    # --- 10. Pós-processamento ---
    if new_products_data:
        new_products_data = data_processor.process_daily_data(new_products_data)

    # --- 11. Finalização e Escrita de Dados ---
    if failed_urls:
        logging.info(f"Writing {len(failed_urls)} failed URLs to {failed_urls_file}")
        with open(failed_urls_file, 'w', encoding='utf-8') as f:
            for url in failed_urls:
                f.write(f"{url}\n")

    if ignored_urls:
        logging.info(f"Writing {len(ignored_urls)} ignored URLs to ignored_urls.txt")
        with open("ignored_urls.txt", 'w', encoding='utf-8') as f:
            for url in ignored_urls:
                f.write(f"{url}\n")

    if new_products_data:
        logging.info("Writing new data to Google Sheet...")
        write_to_google_sheet(new_products_data)

    # --- 12. Notificação por Email ---
    products_on_sale = [
        p for p in new_products_data 
        if p.get("Status Preco Mediano") == "Menor Preço Histórico"
    ]

    best_buys_today = [
        p for p in new_products_data
        if p.get("Menor Preco na Sub-categoria") == "Sim"
    ]

    best_buys_by_market = {}
    if best_buys_today:
        for product in best_buys_today:
            market = product["Mercado"]
            if market not in best_buys_by_market:
                best_buys_by_market[market] = []
            best_buys_by_market[market].append(product)

    significant_discounts = []
    logging.info("--- Start processing significant discounts ---")
    for p in new_products_data:
        variation_str = p.get("Variacao em relacao a Media", "0%").strip()
        product_name = p.get("Nome", "Unknown")
        
        # Ignorar variações não numéricas ou vazias
        if not variation_str or not variation_str.replace('%', '').replace('-', '').replace('.', '').isdigit():
            logging.warning(f"Skipping product '{product_name}' due to invalid variation string: '{variation_str}'")
            continue

        logging.info(f"Processing product: {product_name}, Variation string: '{variation_str}'")
        try:
            variation_float = float(variation_str.replace('%', ''))
            logging.info(f"Parsed float: {variation_float}")
            if variation_float <= -20:
                logging.info(f"Product '{product_name}' meets criteria (<= -20). Adding to list.")
                significant_discounts.append(p)
            else:
                logging.info(f"Product '{product_name}' does NOT meet criteria. Value is > -20.")
        except (ValueError, TypeError) as e:
            logging.error(f"Could not parse 'Variacao em relacao a Média' for product '{product_name}': '{variation_str}'. Error: {e}")

    # Filtra os descontos significativos para incluir apenas os que são o melhor preço na sub-categoria
    best_price_discounts = [
        p for p in significant_discounts 
        if p.get("Menor Preco na Sub-categoria") == "Sim"
    ]

    # Envia a notificação em massa do WhatsApp se houver descontos significativos com o melhor preço
    if best_price_discounts:
        send_bulk_whatsapp_message(best_price_discounts)

    logging.info(f"--- Finished processing significant discounts. Found {len(significant_discounts)} items. ---")

    if significant_discounts:
        should_send_email = not (args.url or args.file or args.mkt)
        if should_send_email:
            send_email_notification(products_on_sale, best_buys_by_market, significant_discounts)
        else:
            logging.info("Email notification skipped due to command-line arguments (--url, --file, or --mkt).")

    # --- 13. Resumo Final ---
    summary_message = f"Coleta finalizada! {len(new_products_data)} produtos coletados, {len(failed_urls)} falhas, {len(ignored_urls)} ignorados."
    logging.info(summary_message)
    send_notification("Mercado Tracker", summary_message)

# Ponto de entrada do script: executa a função main se o arquivo for chamado diretamente.
if __name__ == "__main__":
    main()
