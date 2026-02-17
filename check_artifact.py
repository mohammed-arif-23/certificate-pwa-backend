from reportlab.lib.utils import ImageReader
import os

IMG_PATH = r"C:\Users\Administrator\.gemini\antigravity\brain\47060b86-8e25-4c3e-9adc-d78b2a63bb09\uploaded_image_1771080592612.png"

try:
    if os.path.exists(IMG_PATH):
        image = ImageReader(IMG_PATH)
        w, h = image.getSize()
        print(f"Artifact Image: {w}x{h}")
    else:
        print("Artifact image not found")
except Exception as e:
    print(f"Error: {e}")
