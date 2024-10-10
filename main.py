import sys
import threading
import subprocess
import re
import markdown
from markdown.extensions import codehilite, fenced_code
from pygments.formatters import HtmlFormatter
from PyQt5 import QtWidgets, QtGui, QtCore
from pynput import keyboard

from syntax_highlighter import PythonHighlighter
from image_processing import capture_screen, extract_text_from_image
from problem_detection import is_alg_problem

class AIResponseViewer(QtWidgets.QWidget):
    ai_response_ready = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.set_syntax_highlighting()
        self.monitor_number = 1
        self.ai_response_ready.connect(self.display_ai_response)
        self.start_keyboard_listener()

    def init_ui(self):
        self.setWindowTitle("AI Response Viewer")
        self.setGeometry(100, 100, 1200, 700)
        self.setup_styles()
        self.setup_layout()

    def setup_styles(self):
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

    def setup_layout(self):
        main_layout = QtWidgets.QHBoxLayout()
        main_layout.setSpacing(20)

        left_layout = self.create_column_layout("Generated Code", "code_edit")
        right_layout = self.create_column_layout("Explanation", "explanation_edit")

        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 1)

        bottom_layout = QtWidgets.QVBoxLayout()
        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setValue(0)
        self.status_label = QtWidgets.QLabel("Press F8 to generate AI response.", self)
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label.setObjectName("status_label")
        bottom_layout.addWidget(self.progress_bar)
        bottom_layout.addWidget(self.status_label)

        overall_layout = QtWidgets.QVBoxLayout()
        overall_layout.addLayout(main_layout, 1)
        overall_layout.addLayout(bottom_layout)

        self.setLayout(overall_layout)

    def create_column_layout(self, title, edit_name):
        layout = QtWidgets.QVBoxLayout()
        label = QtWidgets.QLabel(title, self)
        label.setAlignment(QtCore.Qt.AlignCenter)
        text_edit = QtWidgets.QTextEdit(self)
        text_edit.setReadOnly(True)
        text_edit.setObjectName(edit_name)
        text_edit.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        layout.addWidget(label)
        layout.addWidget(text_edit)
        setattr(self, edit_name, text_edit)
        return layout

    def set_syntax_highlighting(self):
        self.highlighter = PythonHighlighter(self.code_edit.document())

    def start_keyboard_listener(self):
        self.listener_thread = threading.Thread(target=self._keyboard_listener, daemon=True)
        self.listener_thread.start()

    def _keyboard_listener(self):
        with keyboard.GlobalHotKeys({'<f8>': self.on_hotkey}) as listener:
            listener.join()

    def on_hotkey(self):
        self.status_label.setText("Capturing the screen...")
        self.progress_bar.setValue(20)
        threading.Thread(target=self.process_screen).start()

    def process_screen(self):
        img = capture_screen(self.monitor_number)
        self.status_label.setText("Processing the image...")
        self.progress_bar.setValue(40)

        extracted_text = extract_text_from_image(img)

        if is_alg_problem(extracted_text):
            self.status_label.setText("Algorithmic problem detected. Sending to AI...")
            self.progress_bar.setValue(60)
            ai_response = self.query_ollama(self.create_prompt(extracted_text))
            if ai_response:
                self.progress_bar.setValue(80)
                self.ai_response_ready.emit(ai_response)
            else:
                self.status_label.setText("No response from AI.")
        else:
            self.status_label.setText("No algorithmic problem detected.")
            self.progress_bar.setValue(100)

    def create_prompt(self, extracted_text):
        return f"""
            Solve the following algorithmic problem: {extracted_text}

            Please provide an optimized solution and explain step by step how the code works.
            Focus on making the code easy to understand, using Pythonic style.
            Include the reasons for choosing this approach, the data structures used, and the time and space complexity of the solution.
            If there are other possible approaches, mention them and explain why this one is the most suitable.

            Please provide your response in the following format:

            [CODE]
            class Solution:
                def solve_problem(self, parameters):
                    # Your code here
                    pass
            [/CODE]

            [EXPLANATION]
            1. Approach:
               - Briefly explain the general approach used.

            2. Algorithm:
               - Describe the main steps of the algorithm.

            3. Data structures:
               - List and explain the data structures used.

            4. Complexity:
               - Time: Analyze the time complexity.
               - Space: Analyze the space complexity.

            5. Additional considerations:
               - Mention any optimizations, special cases, or limitations.

            6. Alternatives:
               - If applicable, briefly mention alternative approaches.
            [/EXPLANATION]

            If it's not possible to use this exact format, try to follow it as closely as possible.
        """

    def query_ollama(self, prompt):
        try:
            process = subprocess.Popen(
                ['ollama', 'run', 'deepseek-coder-v2:latest'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(input=prompt)
            if process.returncode == 0:
                return stdout.strip()
            else:
                print(f"Ollama error: {stderr}")
                return None
        except subprocess.TimeoutExpired:
            print("Ollama did not respond in time.")
            return None

    @QtCore.pyqtSlot(str)
    def display_ai_response(self, ai_response):
        code, explanation = self.extract_code_and_explanation(ai_response)
        self.code_edit.setPlainText(code)
        self.highlighter.rehighlight()

        formatted_explanation = self.format_explanation(explanation)
        html_content = self.create_html_content(formatted_explanation)
        self.explanation_edit.setHtml(html_content)

        self.status_label.setText("AI response displayed.")
        self.progress_bar.setValue(100)

    def extract_code_and_explanation(self, ai_response):
        code_match = re.search(r'\[CODE\](.*?)\[/CODE\]', ai_response, re.DOTALL)
        explanation_match = re.search(r'\[EXPLANATION\](.*?)\[/EXPLANATION\]', ai_response, re.DOTALL)

        if code_match and explanation_match:
            return code_match.group(1).strip(), explanation_match.group(1).strip()
        else:
            parts = ai_response.split('```')
            if len(parts) > 1:
                return parts[1].strip(), '\n'.join(parts[2:]).strip()
            else:
                return "", ai_response

    def format_explanation(self, explanation):
        sections = [
            "## Approach",
            "## Algorithm",
            "## Data structures",
            "## Complexity",
            "## Additional considerations",
            "## Alternatives"
        ]

        formatted_lines = []
        current_section = ""
        in_bullet_list = False

        for line in explanation.split('\n'):
            line = line.strip()
            if line and line[0].isdigit() and '.' in line:
                parts = line.split('.', 1)
                if len(parts) == 2:
                    if in_bullet_list:
                        formatted_lines.append("\n")
                        in_bullet_list = False
                    current_section = sections[int(parts[0]) - 1]
                    formatted_lines.append(f"\n{current_section}\n")
            elif line.lower().startswith(('time:', 'space:')):
                if in_bullet_list:
                    formatted_lines.append("\n")
                    in_bullet_list = False
                formatted_lines.append(f"- **{line}**\n")
            elif line.startswith('-'):
                if not in_bullet_list:
                    formatted_lines.append("\n")
                formatted_lines.append(line)
                in_bullet_list = True
            elif ':' in line and not line.lower().startswith(('time:', 'space:')):
                if in_bullet_list:
                    formatted_lines.append("\n")
                    in_bullet_list = False
                parts = line.split(':', 1)
                formatted_lines.append(f"\n### {parts[0].strip()}:")
                if len(parts) > 1:
                    formatted_lines.append(parts[1].strip())
            elif line:
                if in_bullet_list:
                    formatted_lines.append("\n")
                    in_bullet_list = False
                formatted_lines.append(line)

        formatted_text = '\n'.join(formatted_lines)
        return re.sub(r'\n{3,}', '\n\n', formatted_text).strip()

    def create_html_content(self, formatted_explanation):
        html_content = markdown.markdown(
            formatted_explanation,
            extensions=['fenced_code', 'codehilite']
        )
        formatter = HtmlFormatter(style='monokai', full=True, cssclass='codehilite')
        css_string = formatter.get_style_defs('.codehilite')

        custom_css = """
        body { font-family: 'Segoe UI', 'Arial', sans-serif; line-height: 1.6; }
        h1, h2, h3 { color: #569cd6; margin-top: 20px; }
        p { margin-bottom: 15px; }
        ul, ol { margin-bottom: 15px; padding-left: 30px; }
        li { margin-bottom: 5px; }
        code { background-color: #1e1e1e; color: #d4d4d4; padding: 2px 4px; border-radius: 3px; }
        pre { background-color: #1e1e1e; border: 1px solid #3c3c3c; border-radius: 5px; padding: 10px; overflow-x: auto; }
        """

        return f"<style>{css_string}{custom_css}</style>{html_content}"

    def closeEvent(self, event):
        event.accept()

def main():
    app = QtWidgets.QApplication(sys.argv)
    viewer = AIResponseViewer()
    viewer.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()