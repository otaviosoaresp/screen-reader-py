# AI Response Viewer for Algorithmic Problems

## Description
This project is a desktop application that captures algorithmic problems from the user's screen, processes them using OCR (Optical Character Recognition), and sends them to a local AI model for a solution. The application displays the AI's response, including the solution code and a detailed explanation.

## Features
- Screen capture triggered by keyboard shortcut (F8)
- Image processing and text extraction using OCR
- Detection of algorithmic problems in extracted text
- Solution generation using a local AI model (Ollama)
- Graphical interface for displaying code and explanation
- Syntax highlighting for Python code

## Requirements
- Python 3.7+
- PyQt5
- OpenCV
- Tesseract OCR
- NLTK
- Ollama (deepseek-coder-v2 model)

## Installation
1. Clone the repository:
   ```
   git clone https://github.com/otaviosoaresp/screen-reader-py.git
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Install Ollama and the deepseek-coder-v2 model:
   ```
   curl https://ollama.ai/install.sh | sh
   ollama pull deepseek-coder-v2
   ```

## Usage
1. Run the main script:
   ```
   python main.py
   ```
2. Press F8 to capture the screen containing the algorithmic problem
3. Wait for processing and AI response generation
4. View the solution code and explanation in the graphical interface

## Project Structure
- `main.py`: Main script containing the GUI and application logic
- `syntax_highlighter.py`: Class for Python code syntax highlighting
- `image_processing.py`: Functions for image processing and OCR
- `problem_detection.py`: Functions for detecting algorithmic problems in text
