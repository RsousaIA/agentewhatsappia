import os
import json
import time
from datetime import datetime
import re
from typing import Dict, Any, List, Optional
from loguru import logger
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import threading

# Carrega variáveis de ambiente
load_dotenv()

class WhatsAppWebClient:
    """
    Cliente para WhatsApp Web usando Selenium.
    """
    
    def __init__(self):
        self.qr_callback = None
        self.message_callback = None
        self.driver = None
        self.is_authenticated = False
        self.is_running = False
        self.monitoring_thread = None
        
        # Configurações do Chrome
        self.chrome_data_dir = os.getenv("CHROME_DATA_DIR", "./chrome_data")
        self.headless = os.getenv("HEADLESS", "false").lower() == "true"
        
        # Seletores XPath mais robustos (usar classes parciais e identificadores mais estáveis)
        self.selectors = {
            # Elementos principais
            "side_panel": "//div[@id='side' or @data-testid='side-panel']",
            "chat_list": "//div[@id='pane-side' or @data-testid='chat-list']",
            "main_panel": "//div[@id='main' or @data-testid='conversation-panel']",
            
            # Elementos de autenticação
            "qr_canvas": "//canvas[contains(@aria-label,'Scan me') or contains(@aria-label,'Escaneie-me')]",
            
            # Elementos de chat
            "search_box": "//div[@id='side']//div[contains(@contenteditable,'true') or @data-testid='chat-list-search']",
            "chat_row": ".//div[@role='row' or @data-testid='chat-item']",
            "unread_badge": ".//span[contains(@aria-label,'não lida') or contains(@aria-label,'unread') or contains(@data-testid,'unread')]",
            
            # Elementos de mensagem
            "message_in": "//div[contains(@class,'message-in') or contains(@data-testid,'msg-container') and contains(@data-testid,'in')]",
            "message_content": ".//div[contains(@class,'selectable-text') or contains(@data-testid,'msg-text')]//span",
            "message_time": ".//div[contains(@data-testid,'msg-meta') or contains(@class,'copyable-text')]//span[@data-testid='msg-time']",
            
            # Elementos de input
            "message_input": "//div[@id='main']//div[contains(@contenteditable,'true') or @data-testid='conversation-compose-box-input']",
            "send_button": "//div[@id='main']//span[@data-testid='send' or @data-icon='send']",
            
            # Elementos de header
            "chat_header_title": "//div[@id='main']//header//div[contains(@class,'text-title') or contains(@data-testid,'conversation-info-header-chat-title')]//span",
        }
        
        logger.info("Cliente WhatsApp Web inicializado")
    
    def start(self, qr_callback=None, message_callback=None):
        """
        Inicia o cliente WhatsApp Web.
        
        Args:
            qr_callback: Função para processar o código QR (para autenticação)
            message_callback: Função para processar mensagens recebidas
        """
        if self.is_running:
            logger.warning("Cliente WhatsApp Web já está em execução")
            return
        
        self.qr_callback = qr_callback
        self.message_callback = message_callback
        
        try:
            # Configurar o driver do Chrome
            options = Options()
            
            # Usar diretório de dados para persistir a sessão
            options.add_argument(f"user-data-dir={self.chrome_data_dir}")
            
            # Modo headless opcional
            if self.headless:
                options.add_argument("--headless=new")  # Usar a nova API headless (mais estável)
                options.add_argument("--disable-gpu")
                options.add_argument("--no-sandbox")
                options.add_argument("--window-size=1280,900")
                
                # Permitir uso de mídia em modo headless
                options.add_argument("--use-fake-ui-for-media-stream")
                options.add_argument("--use-fake-device-for-media-stream")
            
            # Configurações comuns
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-infobars")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            
            # Iniciar o driver
            self.driver = webdriver.Chrome(options=options)
            self.driver.get("https://web.whatsapp.com/")
            
            # Aguardar carregamento da página
            logger.info("Aguardando carregamento do WhatsApp Web...")
            
            # Iniciar thread de monitoramento
            self.is_running = True
            self.monitoring_thread = threading.Thread(target=self._monitor_whatsapp, daemon=True)
            self.monitoring_thread.start()
            
            logger.info("Cliente WhatsApp Web iniciado")
            
        except Exception as e:
            logger.error(f"Erro ao iniciar cliente WhatsApp Web: {e}")
            if self.driver:
                self.driver.quit()
                self.driver = None
            self.is_running = False
            raise
    
    def stop(self):
        """
        Para o cliente WhatsApp Web.
        """
        if not self.is_running:
            logger.warning("Cliente WhatsApp Web não está em execução")
            return
        
        self.is_running = False
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10)
        
        if self.driver:
            self.driver.quit()
            self.driver = None
        
        logger.info("Cliente WhatsApp Web parado")
    
    def _monitor_whatsapp(self):
        """
        Monitora o WhatsApp Web em segundo plano.
        """
        qr_detected = False
        auth_checked = False
        last_check_time = 0
        
        while self.is_running:
            try:
                # Verificar se há código QR na tela
                if not self.is_authenticated and not qr_detected:
                    try:
                        qr_canvas = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, self.selectors["qr_canvas"]))
                        )
                        
                        if self.qr_callback and qr_canvas:
                            # Aqui normalmente processaríamos a imagem do QR code
                            # No momento, apenas notificamos para escanear manualmente
                            self.qr_callback("Por favor, escaneie o código QR exibido no navegador.")
                            qr_detected = True
                    except TimeoutException:
                        pass
                
                # Verificar se está autenticado
                if not auth_checked or not self.is_authenticated:
                    try:
                        # Verificar se o WhatsApp Web está carregado (verificando elementos típicos)
                        WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, self.selectors["side_panel"]))
                        )
                        
                        # Autenticado com sucesso
                        self.is_authenticated = True
                        auth_checked = True
                        logger.info("Autenticado com sucesso no WhatsApp Web")
                    except TimeoutException:
                        if not auth_checked:
                            # Ainda aguardando autenticação
                            auth_checked = True
                            logger.info("Aguardando autenticação no WhatsApp Web...")
                
                # Verificar novas mensagens a cada 5 segundos
                current_time = time.time()
                if self.is_authenticated and current_time - last_check_time > 5:
                    last_check_time = current_time
                    self._check_new_messages()
                
                time.sleep(1)
            except Exception as e:
                logger.error(f"Erro no monitoramento do WhatsApp Web: {e}")
                time.sleep(5)
    
    def _check_new_messages(self):
        """
        Verifica se há novas mensagens recebidas.
        """
        try:
            # Verificar conversas não lidas (bolhas de notificação)
            try:
                chat_list = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, self.selectors["chat_list"]))
                )
                
                # Buscar todos os chats com mensagens não lidas
                unread_chats = chat_list.find_elements(By.XPATH, self.selectors["unread_badge"])
                
                if not unread_chats:
                    return  # Nenhuma mensagem não lida
                
                for chat in unread_chats:
                    try:
                        # Encontrar o elemento pai que contém a linha do chat
                        chat_row = chat.find_element(By.XPATH, "./ancestor::div[@role='row' or @data-testid='chat-item']")
                        
                        # Clicar na conversa não lida
                        chat_row.click()
                        time.sleep(1)  # Aguardar carregamento do chat
                        
                        # Extrair informações da conversa
                        contact_name = self._get_contact_name()
                        phone_number = self._extract_phone_number(contact_name)
                        messages = self._extract_messages()
                        
                        # Processar as mensagens recebidas
                        if self.message_callback and messages:
                            for message in messages:
                                # Gerar ID único usando hash de conteúdo e timestamp
                                unique_id = f"{phone_number}_{message['timestamp']}_{hash(message['content'])}"
                                
                                self.message_callback({
                                    "message_id": unique_id,
                                    "timestamp": message["timestamp"],
                                    "from": phone_number,
                                    "type": message["type"],
                                    "content": message["content"],
                                    "contact_name": contact_name
                                })
                    except Exception as e:
                        logger.error(f"Erro ao processar conversa não lida: {e}")
            except TimeoutException:
                logger.debug("Nenhuma conversa não lida encontrada")
                
        except Exception as e:
            logger.error(f"Erro ao verificar mensagens não lidas: {e}")
    
    def _get_contact_name(self) -> str:
        """
        Obtém o nome do contato da conversa ativa.
        
        Returns:
            str: Nome do contato
        """
        try:
            header = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, self.selectors["chat_header_title"]))
            )
            return header.text.strip()
        except Exception as e:
            logger.error(f"Erro ao obter nome do contato: {e}")
            return "Desconhecido"
    
    def _extract_phone_number(self, contact_name: str) -> str:
        """
        Extrai o número de telefone da conversa ativa ou cria um identificador único.
        
        Args:
            contact_name: Nome do contato para usar como fallback
            
        Returns:
            str: Número de telefone ou identificador
        """
        try:
            # Tentar extrair das informações do contato
            # Primeiro clicar no nome do contato para abrir informações
            header_title = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, self.selectors["chat_header_title"]))
            )
            header_title.click()
            time.sleep(1)
            
            # Buscar elementos que podem conter informações de telefone
            page_content = self.driver.page_source
            
            # Padrão de regex para números de telefone internacionais
            # Formato: +XX XX XXXXX-XXXX ou variações
            phone_pattern = r"(\+\d{1,3}\s?)?\(?\d{2,3}\)?[\s.-]?\d{4,5}[\s.-]?\d{4}"
            matches = re.findall(phone_pattern, page_content)
            
            if matches:
                # Limpar o número encontrado, removendo caracteres não numéricos
                phone = re.sub(r'[^0-9+]', '', matches[0])
                
                # Voltar para a conversa
                self.driver.find_element(By.XPATH, "//button[@aria-label='Voltar' or @aria-label='Back' or @data-testid='back']").click()
                time.sleep(0.5)
                
                return f"whatsapp:{phone}"
            
            # Se não encontrou, tentar voltar para a conversa
            try:
                self.driver.find_element(By.XPATH, "//button[@aria-label='Voltar' or @aria-label='Back' or @data-testid='back']").click()
                time.sleep(0.5)
            except:
                pass
            
            # Se não conseguiu extrair, usar um placeholder baseado no nome do contato
            return f"whatsapp:{contact_name.replace(' ', '').lower()}"
        except Exception as e:
            logger.error(f"Erro ao extrair número de telefone: {e}")
            # Fallback para um identificador baseado no nome do contato
            return f"whatsapp:{contact_name.replace(' ', '').lower()}"
    
    def _extract_messages(self) -> List[Dict[str, Any]]:
        """
        Extrai mensagens da conversa ativa.
        
        Returns:
            List[Dict[str, Any]]: Lista de mensagens
        """
        messages = []
        
        try:
            # Obter painel principal onde estão as mensagens
            main_panel = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, self.selectors["main_panel"]))
            )
            
            # Obter todas as mensagens recebidas (message-in)
            message_elements = main_panel.find_elements(By.XPATH, ".//div[contains(@class,'message-in') or contains(@data-testid,'msg-container') and contains(@data-testid,'in')]")
            
            # Se não houver nenhuma mensagem, retornar lista vazia
            if not message_elements:
                return []
                
            # Considerar apenas as últimas mensagens não lidas
            # Como já filtramos por chats não lidos, presumimos que as mensagens mais recentes
            # são as que precisamos processar
            for element in message_elements[-10:]:  # Últimas 10 mensagens para limitar o processamento
                try:
                    # Extrair o texto da mensagem usando seletores mais robustos
                    content_element = element.find_element(By.XPATH, ".//div[contains(@class,'selectable-text') or contains(@data-testid,'msg-text')]//span")
                    content = content_element.text.strip() if content_element else ""
                    
                    if not content:
                        continue  # Pular mensagens vazias
                    
                    # Extrair a data/hora da mensagem
                    try:
                        timestamp_element = element.find_element(By.XPATH, ".//span[@data-testid='msg-time']")
                        timestamp_str = timestamp_element.get_attribute("aria-label") or timestamp_element.text
                        
                        # Tentar extrair data e hora do formato do WhatsApp
                        # Exemplo: "14:30" ou "14:30, 01/01/2023"
                        current_date = datetime.now()
                        
                        if "," in timestamp_str:
                            # Formato com data
                            time_part, date_part = timestamp_str.split(",", 1)
                            # Processar partes para criar um datetime
                            timestamp = int(current_date.timestamp())
                        else:
                            # Apenas horário, assumir data atual
                            hour, minute = map(int, timestamp_str.strip().split(":"))
                            message_datetime = current_date.replace(hour=hour, minute=minute)
                            timestamp = int(message_datetime.timestamp())
                    except Exception as e:
                        logger.error(f"Erro ao extrair timestamp: {e}")
                        # Fallback para timestamp atual
                        timestamp = int(datetime.now().timestamp())
                    
                    # Tratar diferentes tipos de mensagem
                    message_type = "text"
                    
                    # Verificar se contém imagem
                    if element.find_elements(By.XPATH, ".//img") or element.find_elements(By.XPATH, ".//div[contains(@data-testid,'image-thumb')]"):
                        message_type = "image"
                    # Verificar se contém áudio
                    elif element.find_elements(By.XPATH, ".//span[contains(@data-testid,'audio-play')]"):
                        message_type = "audio"
                    # Verificar se contém vídeo
                    elif element.find_elements(By.XPATH, ".//span[contains(@data-testid,'video-play')]"):
                        message_type = "video"
                    # Verificar se contém documento
                    elif element.find_elements(By.XPATH, ".//div[contains(@data-testid,'document-thumb')]"):
                        message_type = "document"
                    
                    messages.append({
                        "content": content,
                        "timestamp": timestamp,
                        "type": message_type
                    })
                except Exception as e:
                    logger.error(f"Erro ao extrair dados de uma mensagem: {e}")
            
            return messages
        except Exception as e:
            logger.error(f"Erro ao extrair mensagens: {e}")
            return []
    
    def send_message(self, to: str, message: str) -> bool:
        """
        Envia uma mensagem de texto para um contato ou grupo.
        
        Args:
            to: Nome do contato ou grupo (deve estar visível nos chats recentes)
            message: Conteúdo da mensagem
            
        Returns:
            bool: True se a mensagem foi enviada com sucesso
        """
        if not self.is_authenticated or not self.driver:
            logger.error("Cliente não está autenticado ou inicializado")
            return False
        
        try:
            # Garantir que estamos na tela principal
            try:
                side_panel = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, self.selectors["side_panel"]))
                )
            except TimeoutException:
                # Se não estiver na tela principal, tentar voltar 
                back_button = self.driver.find_element(By.XPATH, "//button[@aria-label='Voltar' or @aria-label='Back' or @data-testid='back']")
                back_button.click()
                time.sleep(1)
            
            # Abrir a caixa de pesquisa
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, self.selectors["search_box"]))
            )
            search_box.clear()
            search_box.send_keys(to)
            time.sleep(2)  # Aguardar pesquisa
            
            # Clicar no primeiro resultado
            chat_result = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, self.selectors["chat_row"]))
            )
            chat_result.click()
            time.sleep(1)
            
            # Digitar a mensagem
            message_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, self.selectors["message_input"]))
            )
            message_box.clear()
            message_box.send_keys(message)
            
            # Enviar a mensagem
            send_button = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, self.selectors["send_button"]))
            )
            send_button.click()
            time.sleep(0.5)  # Aguardar envio
            
            logger.info(f"Mensagem enviada para {to}")
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para {to}: {e}")
            return False
    
    def process_webhook_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mantido para compatibilidade com a interface anterior.
        No caso do WhatsApp Web, não usamos webhooks, mas sim monitoramento ativo.
        
        Args:
            event_data: Dados do evento
            
        Returns:
            Dict[str, Any]: Dados processados (vazio neste caso)
        """
        logger.warning("O método process_webhook_event não é usado com WhatsApp Web")
        return {"messages": []} 