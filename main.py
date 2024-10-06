from PyQt5 import QtWidgets, QtGui, QtCore
import threading
import markdown
from markdown.extensions import codehilite, fenced_code
from pygments.formatters import HtmlFormatter
from PIL import Image
import numpy as np
import mss
import pytesseract
import cv2
import re
import json

# Função para converter array NumPy para QImage
def numpy_to_qimage(img):
    height, width, channel = img.shape
    if channel == 4:  # Verifica se a imagem tem 4 canais (RGBA)
        qimg = QtGui.QImage(img.data, width, height, QtGui.QImage.Format_RGBA8888)
    else:  # Assume 3 canais (RGB)
        qimg = QtGui.QImage(img.data, width, height, QtGui.QImage.Format_RGB888)
    return qimg

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
        self.setWindowTitle("AI Response Viewer")
        self.setGeometry(100, 100, 1200, 700)

        # Configurar estilo escuro e melhorar a formatação
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Segoe UI', 'Arial', sans-serif;
            }
            QTextEdit {
                background-color: #252526;
                border: 1px solid #3c3c3c;
                border-radius: 5px;
                padding: 10px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 14px;
                line-height: 1.4;
            }
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #569cd6;
                padding: 5px 0;
            }
            QProgressBar {
                border: none;
                background-color: #3c3c3c;
                text-align: center;
                height: 10px;
                border-radius: 5px;
            }
            QProgressBar::chunk {
                background-color: #569cd6;
                border-radius: 5px;
            }
            #status_label {
                font-size: 14px;
                color: #9cdcfe;
            }
        """)

        main_layout = QtWidgets.QHBoxLayout()

        # Coluna da esquerda (Código)
        left_layout = QtWidgets.QVBoxLayout()
        left_label = QtWidgets.QLabel("Generated Code", self)
        left_label.setAlignment(QtCore.Qt.AlignCenter)
        self.code_edit = QtWidgets.QTextEdit(self)
        self.code_edit.setReadOnly(True)
        self.code_edit.setObjectName("code_edit")

        # Coluna da direita (Explicação)
        right_layout = QtWidgets.QVBoxLayout()
        right_label = QtWidgets.QLabel("Explanation", self)
        right_label.setAlignment(QtCore.Qt.AlignCenter)
        self.explanation_edit = QtWidgets.QTextEdit(self)
        self.explanation_edit.setReadOnly(True)
        self.explanation_edit.setObjectName("explanation_edit")

        # Barra de progresso e status
        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setValue(0)
        self.status_label = QtWidgets.QLabel("Press F8 to generate AI response.", self)
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label.setObjectName("status_label")

        # Adicionar widgets aos layouts
        left_layout.addWidget(left_label)
        left_layout.addWidget(self.code_edit)
        right_layout.addWidget(right_label)
        right_layout.addWidget(self.explanation_edit)

        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)

        bottom_layout = QtWidgets.QVBoxLayout()
        bottom_layout.addWidget(self.progress_bar)
        bottom_layout.addWidget(self.status_label)

        overall_layout = QtWidgets.QVBoxLayout()
        overall_layout.addLayout(main_layout, 1)
        overall_layout.addLayout(bottom_layout)

        self.setLayout(overall_layout)

    def start_keyboard_listener(self):
        from pynput import keyboard
        # Cria o listener e inicia
        self.listener = keyboard.GlobalHotKeys({'<f8>': self.on_hotkey})
        self.listener.start()
        self.listener.join()

    def on_hotkey(self):
        print("Tecla de atalho pressionada!")
        # Atualiza o status
        self.status_label.setText("Capturando a tela...")
        self.progress_bar.setValue(20)
        # Executa o processamento em uma thread separada
        threading.Thread(target=self.process_screen).start()

    def process_screen(self):
        # Função para capturar a tela
        def capture_screen(monitor_number=1):
            with mss.mss() as sct:
                monitor = sct.monitors[monitor_number]
                screenshot = sct.grab(monitor)
                img = np.array(screenshot)
                return img

        # Função para melhorar o pré-processamento da imagem para OCR
        def preprocess_image(img):
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            processed_img = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            return processed_img

        # Função para extrair texto da imagem usando OCR
        def extract_text_from_image(img):
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

        # Captura a tela
        img = capture_screen(self.monitor_number)
        print("Tela capturada.")

        self.status_label.setText("Processando a imagem...")
        self.progress_bar.setValue(40)

        extracted_text = extract_text_from_image(img)
        print("Texto extraído: ", extracted_text)

        if is_alg_problem(extracted_text):
            self.status_label.setText("Problema algorítmico detectado. Enviando para a IA...")
            self.progress_bar.setValue(60)

            # Envia o texto capturado para a IA
            prompt = f"""
                Resolva o seguinte problema de algoritmo: {extracted_text}

                Por favor, forneça uma solução otimizada e explique passo a passo como o código funciona. 
                Foque em fazer um código de simples entendimento, fazendo um código pythonico.
                Inclua as razões pelas quais você escolheu essa abordagem, as estruturas de dados usadas e a complexidade de tempo e espaço da solução.
                Caso existam outras abordagens possíveis, mencione-as e explique por que esta é a mais adequada.
            """
            ai_response = self.query_ollama(prompt)

            if ai_response:
                self.progress_bar.setValue(80)
                self.ai_response_ready.emit(ai_response)
            else:
                self.status_label.setText("Nenhuma resposta da IA.")
        else:
            self.status_label.setText("Nenhum problema algorítmico detectado.")
            self.progress_bar.setValue(100)

    # Função para enviar texto para o modelo local do Ollama e obter resposta
    def query_ollama(self, prompt):
        import subprocess
        try:
            modified_prompt = f"""
                {prompt}

                Por favor, tente fornecer sua resposta no seguinte formato, se possível:
                [CODE]
                O código Python completo aqui
                [/CODE]

                [EXPLANATION]
                A explicação detalhada aqui
                [/EXPLANATION]

                Se não for possível usar esse formato, apenas forneça a resposta normalmente.
            """
            process = subprocess.Popen(
                ['ollama', 'run', 'deepseek-coder-v2:latest'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(input=modified_prompt)
            if process.returncode == 0:
                return stdout.strip()
            else:
                print(f"Erro no Ollama: {stderr}")
                return None
        except subprocess.TimeoutExpired:
            print("Ollama não respondeu a tempo.")
            return None

    @QtCore.pyqtSlot(str)
    def display_ai_response(self, ai_response):
        code = ""
        explanation = ""

        # Tenta extrair código e explicação usando tags
        code_match = re.search(r'\[CODE\](.*?)\[/CODE\]', ai_response, re.DOTALL)
        explanation_match = re.search(r'\[EXPLANATION\](.*?)\[/EXPLANATION\]', ai_response, re.DOTALL)

        if code_match and explanation_match:
            code = code_match.group(1).strip()
            explanation = explanation_match.group(1).strip()
        else:
            # Se não encontrar as tags, tenta separar o código da explicação
            parts = ai_response.split('```')
            if len(parts) > 1:
                code = parts[1].strip()
                explanation = '\n'.join(parts[2:]).strip()
            else:
                # Se não conseguir separar, usa toda a resposta como explicação
                explanation = ai_response

        self.code_edit.setPlainText(code)

        html_content = markdown.markdown(
            explanation,
            extensions=['fenced_code', 'codehilite']
        )
        formatter = HtmlFormatter(style='monokai', full=True, cssclass='codehilite')
        css_string = formatter.get_style_defs('.codehilite')

        full_html = f"<style>{css_string}</style>{html_content}"
        self.explanation_edit.setHtml(full_html)

        self.status_label.setText("AI response displayed.")
        self.progress_bar.setValue(100)

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