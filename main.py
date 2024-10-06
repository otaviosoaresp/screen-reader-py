import mss
import pytesseract
from PIL import Image
import numpy as np
import cv2
import subprocess
import re
import time
import threading

from PyQt5 import QtWidgets, QtGui, QtCore
import markdown
from markdown.extensions import codehilite, fenced_code
from pygments.formatters import HtmlFormatter
from pynput import keyboard

# Função para capturar a tela
def capture_screen(monitor_number=1):
    with mss.mss() as sct:
        monitor = sct.monitors[monitor_number]
        screenshot = sct.grab(monitor)
        img = np.array(screenshot)
        return img

# Função para melhorar o pré-processamento da imagem para OCR
def preprocess_image(img):
    # Converte a imagem para escala de cinza
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Aplica uma limiarização adaptativa para melhorar o contraste
    processed_img = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

    return processed_img

# Função para extrair texto da imagem usando OCR, após pré-processamento
def extract_text_from_image(img):
    # Pré-processar a imagem antes de passar para o OCR
    processed_img = preprocess_image(img)

    image = Image.fromarray(processed_img)
    text = pytesseract.image_to_string(image)
    return text

# Função para detectar se o texto capturado é um problema algorítmico
def is_alg_problem(text):
    keywords = ['input', 'output', 'example', 'prices', 'maximum', 'integer', 'array']
    for keyword in keywords:
        if re.search(rf'\b{keyword}\b', text, re.IGNORECASE):
            return True
    return False

# Função para enviar texto para o modelo local do Ollama e obter resposta
def query_ollama(prompt):
    try:
        # Executa o comando do Ollama e passa o prompt via stdin
        process = subprocess.Popen(
            ['ollama', 'run', 'deepseek-coder-v2:latest'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=prompt)

        if process.returncode == 0:
            return stdout.strip()
        else:
            print(f"Erro no Ollama: {stderr}")
            return None
    except subprocess.TimeoutExpired:
        print("Ollama não respondeu a tempo.")
        return None

# Classe da interface gráfica
class AIResponseViewer(QtWidgets.QWidget):
    # Definição do sinal personalizado
    ai_response_ready = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.monitor_number = 1  # Número do monitor a ser capturado

        # Conecta o sinal ao slot
        self.ai_response_ready.connect(self.display_ai_response)

        # Inicia o listener de teclado em uma thread separada
        self.listener_thread = threading.Thread(target=self.start_keyboard_listener, daemon=True)
        self.listener_thread.start()

    def init_ui(self):
        self.setWindowTitle("Visualizador de Resposta da IA")
        self.setGeometry(100, 100, 800, 600)

        # Cria um QTextEdit para exibir a resposta da IA
        self.text_edit = QtWidgets.QTextEdit(self)
        self.text_edit.setReadOnly(True)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.text_edit)
        self.setLayout(layout)

        # Mensagem inicial
        self.text_edit.setHtml("<h2>Pressione F8 para gerar a resposta da IA.</h2>")

    def start_keyboard_listener(self):
        # Cria o listener e inicia
        self.listener = keyboard.GlobalHotKeys({'<f8>': self.on_hotkey})
        self.listener.start()
        self.listener.join()

    def on_hotkey(self):
        print("Tecla de atalho pressionada!")
        # Executa o processamento em uma thread separada
        threading.Thread(target=self.process_screen).start()

    def process_screen(self):
        print("Capturando a tela...")

        img = capture_screen(self.monitor_number)
        extracted_text = extract_text_from_image(img)

        if is_alg_problem(extracted_text):
            print("Problema algorítmico detectado! Enviando para IA...")
            prompt = """
                Você é um especialista em algoritmos e estrutura de dados.

                Dado o problema abaixo, escreva um código que resolva o problema.

                Retorne apenas o código com comentários em cada linha, explicando o propósito de cada instrução.

                Problema:
            """

            ai_response = query_ollama(f'{prompt}\n{extracted_text}')
            if ai_response:
                print("Resposta da IA recebida.")
                # Emite o sinal com a resposta da IA
                self.ai_response_ready.emit(ai_response)
            else:
                print("Nenhuma resposta da IA.")
        else:
            print("Nenhum problema algorítmico detectado.")

    # Este método será executado no thread principal
    @QtCore.pyqtSlot(str)
    def display_ai_response(self, ai_response):
        # Converte Markdown para HTML com realce de sintaxe
        html_content = markdown.markdown(
            ai_response,
            extensions=['fenced_code', 'codehilite']
        )

        # Obtém o CSS do Pygments para o realce de sintaxe
        formatter = HtmlFormatter(style='default', full=True, cssclass='codehilite')
        css_string = formatter.get_style_defs('.codehilite')

        # Embute o CSS no HTML
        full_html = f"<style>{css_string}</style>{html_content}"

        # Atualiza o QTextEdit com o conteúdo HTML
        self.text_edit.setHtml(full_html)

    def closeEvent(self, event):
        # Para o listener de teclado quando a janela é fechada
        self.listener.stop()
        event.accept()

def main():
    import sys
    app = QtWidgets.QApplication(sys.argv)
    viewer = AIResponseViewer()
    viewer.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
