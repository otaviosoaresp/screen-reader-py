import mss
import pytesseract
from PIL import Image
import numpy as np
import cv2
import subprocess
import re
import time


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

    # Exibe a imagem processada para depuração
    #cv2.imshow("Imagem Processada", processed_img)

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


# Fluxo principal
def main():
    monitor_number = 1  # Número do monitor a ser capturado
    print("Iniciando a captura de tela. Pressione 'q' na janela de visualização para encerrar.")

    with mss.mss() as sct:
        monitor = sct.monitors[monitor_number]
        while True:
            screenshot = sct.grab(monitor)
            img = np.array(screenshot)

            # Extrai o texto da imagem e faz o log do resultado
            extracted_text = extract_text_from_image(img)

            # Verifica se é um problema algorítmico
            if is_alg_problem(extracted_text):
                print("Problema algorítmico detectado! Enviando para IA...")
                prompt = """
                    Dado um problema algorítmico, escreva um algoritmo que resolva o problema.
                    
                    O retorno deve ser somente a solução do problema.
                    
                    Você pode fazer uma breve explicação do seu algoritmo, mas o retorno deve ser a solução.
                    
                
                    Algoritmo:
                """

                ai_response = query_ollama(f'{prompt}\n{extracted_text}')
                if ai_response:
                    print(f"Resposta da IA:\n{ai_response}")
            else:
                print("Nenhum problema algorítmico detectado.")

            # # Exibe a captura de tela em uma janela
            # cv2.imshow("Captura de Tela", img)

            # Verifica se a tecla 'q' foi pressionada para encerrar
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                break

            # Pequena pausa para evitar sobrecarga
            time.sleep(1)


if __name__ == "__main__":
    main()
