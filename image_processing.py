import numpy as np
import mss
import cv2
import pytesseract
from PIL import Image

def capture_screen(monitor_number=1):
    with mss.mss() as sct:
        monitor = sct.monitors[monitor_number]
        screenshot = sct.grab(monitor)
        return np.array(screenshot)

def preprocess_image(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

def extract_text_from_image(img):
    processed_img = preprocess_image(img)
    image = Image.fromarray(processed_img)
    return pytesseract.image_to_string(image)