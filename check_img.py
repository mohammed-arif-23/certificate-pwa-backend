from reportlab.lib.utils import ImageReader
import os

TEMPLATE_PATH = r"d:\Valli apps\certificate-pwa\backend\templates\certificate_template.png"

try:
    if os.path.exists(TEMPLATE_PATH):
        image = ImageReader(TEMPLATE_PATH)
        w, h = image.getSize()
        print(f"Width: {w}, Height: {h}")
    else:
        print("Template not found")
except Exception as e:
    print(f"Error: {e}")
