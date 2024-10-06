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
import nltk

nltk.download('punkt')


# Função para converter array NumPy para QImage
def numpy_to_qimage(img):
    height, width, channel = img.shape
    if channel == 4:  # Verifica se a imagem tem 4 canais (RGBA)
        qimg = QtGui.QImage(img.data, width, height, QtGui.QImage.Format_RGBA8888)
    else:  # Assume 3 canais (RGB)
        qimg = QtGui.QImage(img.data, width, height, QtGui.QImage.Format_RGB888)
    return qimg


class PythonHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

        # Definição de cores para diferentes elementos do código
        keyword_format = QtGui.QTextCharFormat()
        keyword_format.setForeground(QtGui.QColor("#569cd6"))
        keyword_format.setFontWeight(QtGui.QFont.Bold)
        keywords = ["def", "class", "for", "if", "elif", "else", "while", "return", "import", "from", "as", "try",
                    "except", "finally", "with"]
        for word in keywords:
            self.highlighting_rules.append((QtCore.QRegExp(r'\b' + word + r'\b'), keyword_format))

        function_format = QtGui.QTextCharFormat()
        function_format.setFontItalic(True)
        function_format.setForeground(QtGui.QColor("#dcdcaa"))
        self.highlighting_rules.append((QtCore.QRegExp(r'\b[A-Za-z0-9_]+(?=\()'), function_format))

        string_format = QtGui.QTextCharFormat()
        string_format.setForeground(QtGui.QColor("#ce9178"))
        self.highlighting_rules.append((QtCore.QRegExp(r'".*?"'), string_format))
        self.highlighting_rules.append((QtCore.QRegExp(r"'.*?'"), string_format))

        comment_format = QtGui.QTextCharFormat()
        comment_format.setForeground(QtGui.QColor("#6a9955"))
        self.highlighting_rules.append((QtCore.QRegExp(r'#.*'), comment_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            expression = QtCore.QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)


# Classe da interface gráfica
class AIResponseViewer(QtWidgets.QWidget):
    # Definição do sinal personalizado
    ai_response_ready = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.set_syntax_highlighting()
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
        main_layout.setSpacing(20)  # Espaçamento entre as colunas

        # Coluna da esquerda (Código)
        left_layout = QtWidgets.QVBoxLayout()
        left_label = QtWidgets.QLabel("Generated Code", self)
        left_label.setAlignment(QtCore.Qt.AlignCenter)
        self.code_edit = QtWidgets.QTextEdit(self)
        self.code_edit.setReadOnly(True)
        self.code_edit.setObjectName("code_edit")
        self.code_edit.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)  # Desativa a quebra de linha

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

        main_layout.addLayout(left_layout, 1)  # Proporção 1
        main_layout.addLayout(right_layout, 1)  # Proporção 1

        bottom_layout = QtWidgets.QVBoxLayout()
        bottom_layout.addWidget(self.progress_bar)
        bottom_layout.addWidget(self.status_label)

        overall_layout = QtWidgets.QVBoxLayout()
        overall_layout.addLayout(main_layout, 1)
        overall_layout.addLayout(bottom_layout)

        self.setLayout(overall_layout)

    def set_syntax_highlighting(self):
        self.highlighter = PythonHighlighter(self.code_edit.document())

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
            return has_keywords(text) or has_patterns(text) or has_token_matches(text)

        # Implementação do Método 1: Expansão das palavras-chave
        def has_keywords(text):
            keywords = [
                'input', 'output', 'example', 'constraint', 'constraints', 'integer', 'integers',
                'array', 'arrays', 'list', 'lists', 'string', 'strings', 'tree', 'trees', 'graph', 'graphs',
                'algorithm', 'algorithms', 'compute', 'calculate', 'determine', 'find', 'search',
                'maximum', 'minimum', 'optimize', 'sort', 'sorted', 'sequence', 'data structure',
                'dynamic programming', 'recursion', 'complexity', 'efficient', 'function', 'test case',
                'subsequence', 'substring', 'nodes', 'edges', 'path', 'weight', 'sum', 'product',
                'modulo', 'prime', 'factorial', 'permutation', 'combination', 'digits', 'frequency',
                'probability', 'queries', 'operations', 'elements', 'pair', 'triplet', 'matrix', 'matrices',
                'number', 'numbers', 'time limit', 'space limit', 'value', 'values', 'total', 'length',
                'height', 'depth', 'breadth', 'width', 'count', 'size', 'capacity', 'level', 'order',
                'neighbor', 'neighbors', 'connected', 'component', 'components', 'degree', 'weights',
                'balanced', 'unbalanced', 'circular', 'linear', 'non-linear', 'symmetric', 'asymmetric',
                'palindrome', 'anagram', 'pattern', 'matching', 'regex', 'regular expression',
                'shuffle', 'reverse', 'rotate', 'flip', 'swap', 'shift', 'merge', 'split', 'join',
                'append', 'insert', 'delete', 'remove', 'replace', 'update', 'modify', 'transform',
                'convert', 'encode', 'decode', 'compress', 'decompress', 'encrypt', 'decrypt',
                'hash', 'map', 'filter', 'reduce', 'flatten', 'zip', 'unzip', 'concatenate', 'compare',
                'equal', 'unequal', 'greater', 'less', 'between', 'range', 'threshold', 'limit', 'bound',
                'unbound', 'infinite', 'finite', 'overflow', 'underflow', 'exception', 'error',
                'valid', 'invalid', 'duplicate', 'unique', 'missing', 'empty', 'null', 'undefined',
                'initialize', 'instantiate', 'implement', 'inherit', 'override', 'overload', 'interface',
                'abstract', 'static', 'final', 'constant', 'variable', 'parameter', 'argument',
                'property', 'attribute', 'method', 'procedure', 'routine', 'loop', 'iteration',
                'recursion', 'conditional', 'branch', 'case', 'switch', 'debug', 'trace', 'log',
                'print', 'display', 'show', 'visualize', 'simulate', 'model', 'train', 'test',
                'validate', 'accuracy', 'precision', 'recall', 'performance', 'benchmark', 'profile',
                'optimize', 'improve', 'enhance', 'refactor', 'restructure', 'design', 'architecture',
                'pattern', 'anti-pattern', 'best practice', 'code smell', 'technical debt',
                'scalable', 'robust', 'secure', 'reliable', 'maintainable', 'portable', 'compatible',
                'efficient', 'fast', 'slow', 'complex', 'simple', 'elegant', 'readable', 'clean',
                'comment', 'document', 'specification', 'requirement', 'analysis', 'synthesis',
                'evaluation', 'iteration', 'development', 'deployment', 'integration', 'delivery',
                'continuous', 'agile', 'scrum', 'kanban', 'waterfall', 'spiral', 'prototype',
                'test-driven', 'behavior-driven', 'domain-driven', 'model-driven'
            ]
            for keyword in keywords:
                if re.search(rf'\b{keyword}\b', text, re.IGNORECASE):
                    return True
            return False

        # Implementação do Método 2: Padrões de expressões regulares
        def has_patterns(text):
            patterns = [
                r'Constraints?:',
                r'Input\s+Format:',
                r'Output\s+Format:',
                r'Sample\s+Input:',
                r'Sample\s+Output:',
                r'Examples?:',
                r'Description:',
                r'Problem\s+Statement:',
                r'You are given',
                r'Write a program',
                r'Given an? .*?, (determine|compute|find|calculate)',
                r'In this problem',
                r'The first line contains',
                r'Read an integer',
                r'For each test case',
                r'Print .*? to stdout',
                r'Explanation',
                r'Note:',
                r'Test\s+Cases?',
                r'Function Description',
                r'Complete the .*? function',
                r'Return the .*?',
                r'Your task is to',
                r'Limits?:',
                r'Input consists of',
                r'Output consists of',
                r'Constraints:',
                r'Objective:',
                r'Challenge:',
                r'Background:',
                r'Compute the',
                r'Find the',
                r'Calculate the',
                r'Determine the',
                r'Implement an algorithm',
                r'Solve the following',
                r'Consider the following',
                r'Assume that',
                r'Suppose that',
                r'Let\'s define',
                r'Let us define',
                r'It is required to',
                r'Develop a function',
                r'Provide an algorithm',
                r'Design a program',
                r'Your function should',
                r'Return YES if',
                r'Return NO if',
                r'Constraints are as follows',
                r'The goal is to',
                r'Under the following conditions',
                r'Examples? \(input/output\):',
                r'All input numbers are',
                r'The input data is guaranteed to be',
                r'The output should be',
                r'Output Format:',
                r'Input Format:',
            ]
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return True
            return False

        # Implementação do Método 6: Análise de tokens com NLTK
        def has_token_matches(text):
            tokens = nltk.word_tokenize(text.lower())
            keywords = set([
                'compute', 'calculate', 'determine', 'find', 'output', 'input',
                'integer', 'array', 'string', 'given', 'write', 'program', 'function',
                'algorithm', 'return', 'constraints', 'test', 'case', 'example', 'data',
                'structure', 'efficient', 'complexity', 'optimize', 'search', 'sort',
                'maximum', 'minimum', 'number', 'numbers', 'list', 'lists', 'trees',
                'graphs', 'nodes', 'edges', 'dynamic', 'programming', 'recursion',
                'solution', 'implement', 'design', 'develop', 'code', 'procedure',
                'method', 'approach', 'logic', 'problem', 'statement', 'task',
                'objective', 'goal', 'challenge', 'operation', 'process', 'step',
                'sequence', 'order', 'condition', 'loop', 'iteration', 'recurrence',
                'formula', 'equation', 'expression', 'variable', 'parameter',
                'argument', 'input', 'output', 'sample', 'test', 'case', 'constraints',
                'limit', 'bound', 'time', 'space', 'efficiency', 'performance',
                'optimize', 'improve', 'increase', 'decrease', 'maximize', 'minimize'
            ])
            token_set = set(tokens)
            common_tokens = keywords.intersection(token_set)
            return len(common_tokens) >= 3  # Ajuste o número conforme necessário

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

                Por favor, forneça sua resposta no seguinte formato:

                [CODE]
                class Solution:
                    def solve_problem(self, parameters):
                        # Seu código aqui
                        pass

                [/CODE]

                [EXPLANATION]
                1. Abordagem:
                   - Explique brevemente a abordagem geral utilizada.

                2. Algoritmo:
                   - Descreva os passos principais do algoritmo.

                3. Estruturas de dados:
                   - Liste e explique as estruturas de dados utilizadas.

                4. Complexidade:
                   - Tempo: Analise a complexidade de tempo.
                   - Espaço: Analise a complexidade de espaço.

                5. Considerações adicionais:
                   - Mencione quaisquer otimizações, casos especiais ou limitações.

                6. Alternativas:
                   - Se houver, mencione brevemente abordagens alternativas.
                [/EXPLANATION]

                Se não for possível usar esse formato exato, tente seguir o mais próximo possível.
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
        self.highlighter.rehighlight()  # Reaplica o destaque de sintaxe

        # Formata a explicação para melhor legibilidade
        formatted_explanation = self.format_explanation(explanation)

        html_content = markdown.markdown(
            formatted_explanation,
            extensions=['fenced_code', 'codehilite']
        )
        formatter = HtmlFormatter(style='monokai', full=True, cssclass='codehilite')
        css_string = formatter.get_style_defs('.codehilite')

        # Adiciona estilos personalizados para melhorar a aparência da explicação
        custom_css = """
        body { font-family: 'Segoe UI', 'Arial', sans-serif; line-height: 1.6; }
        h1, h2, h3 { color: #569cd6; margin-top: 20px; }
        p { margin-bottom: 15px; }
        ul, ol { margin-bottom: 15px; padding-left: 30px; }
        li { margin-bottom: 5px; }
        code { background-color: #1e1e1e; color: #d4d4d4; padding: 2px 4px; border-radius: 3px; }
        pre { background-color: #1e1e1e; border: 1px solid #3c3c3c; border-radius: 5px; padding: 10px; overflow-x: auto; }
        """

        full_html = f"<style>{css_string}{custom_css}</style>{html_content}"
        self.explanation_edit.setHtml(full_html)

        self.status_label.setText("AI response displayed.")
        self.progress_bar.setValue(100)

    def format_explanation(self, explanation):
        sections = [
            "## Abordagem",
            "## Algoritmo",
            "## Estruturas de dados",
            "## Complexidade",
            "## Considerações adicionais",
            "## Alternativas"
        ]

        formatted_lines = []
        current_section = ""
        in_bullet_list = False

        for line in explanation.split('\n'):
            line = line.strip()
            if line and line[0].isdigit() and '.' in line:
                # Converte linhas numeradas em cabeçalhos Markdown
                parts = line.split('.', 1)
                if len(parts) == 2:
                    if in_bullet_list:
                        formatted_lines.append("\n")
                        in_bullet_list = False
                    current_section = sections[int(parts[0]) - 1]
                    formatted_lines.append(f"\n{current_section}\n")
            elif line.lower().startswith(('tempo:', 'espaço:')):
                # Formata as linhas de complexidade
                if in_bullet_list:
                    formatted_lines.append("\n")
                    in_bullet_list = False
                formatted_lines.append(f"- **{line}**\n")
            elif line.startswith('-'):
                # Trata bullet points
                if not in_bullet_list:
                    formatted_lines.append("\n")
                formatted_lines.append(line)
                in_bullet_list = True
            elif ':' in line and not line.lower().startswith(('tempo:', 'espaço:')):
                # Trata linhas com dois pontos como subtópicos
                if in_bullet_list:
                    formatted_lines.append("\n")
                    in_bullet_list = False
                parts = line.split(':', 1)
                formatted_lines.append(f"\n### {parts[0].strip()}:")
                if len(parts) > 1:
                    formatted_lines.append(parts[1].strip())
            elif line:
                # Adiciona outras linhas normalmente
                if in_bullet_list:
                    formatted_lines.append("\n")
                    in_bullet_list = False
                formatted_lines.append(line)

        # Junta as linhas e remove espaços em branco extras
        formatted_text = '\n'.join(formatted_lines)
        formatted_text = re.sub(r'\n{3,}', '\n\n', formatted_text)

        return formatted_text.strip()

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
