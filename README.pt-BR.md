# Visualizador de Respostas de IA para Problemas Algorítmicos

## Descrição
Este projeto é uma aplicação de desktop que captura problemas algorítmicos da tela do usuário, os processa usando OCR (Reconhecimento Óptico de Caracteres) e envia para um modelo de IA local para obter uma solução. A aplicação exibe a resposta da IA, incluindo o código da solução e uma explicação detalhada.

## Funcionalidades
- Captura de tela ativada por atalho de teclado (F8)
- Processamento de imagem e extração de texto usando OCR
- Detecção de problemas algorítmicos no texto extraído
- Geração de solução usando um modelo de IA local (Ollama)
- Interface gráfica para exibição de código e explicação
- Destaque de sintaxe para o código Python

## Requisitos
- Python 3.7+
- PyQt5
- OpenCV
- Tesseract OCR
- NLTK
- Ollama (modelo deepseek-coder-v2)

## Instalação
1. Clone o repositório:
   ```
   git clone https://github.com/seu-usuario/nome-do-repositorio.git
   ```
2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
3. Instale o Ollama e o modelo deepseek-coder-v2:
   ```
   curl https://ollama.ai/install.sh | sh
   ollama pull deepseek-coder-v2
   ```

## Uso
1. Execute o script principal:
   ```
   python main.py
   ```
2. Pressione F8 para capturar a tela contendo o problema algorítmico
3. Aguarde o processamento e a geração da resposta pela IA
4. Visualize o código da solução e a explicação na interface gráfica

## Estrutura do Projeto
- `main.py`: Script principal contendo a interface gráfica e lógica da aplicação
- `syntax_highlighter.py`: Classe para destaque de sintaxe do código Python
- `image_processing.py`: Funções para processamento de imagem e OCR
- `problem_detection.py`: Funções para detecção de problemas algorítmicos no texto
