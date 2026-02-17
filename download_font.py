import requests
import os

FONT_URL = "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Bold.ttf"
DEST = r"d:\Valli apps\certificate-pwa\backend\fonts\Poppins-Bold.ttf"

try:
    print(f"Downloading {FONT_URL}...")
    response = requests.get(FONT_URL)
    response.raise_for_status()
    with open(DEST, "wb") as f:
        f.write(response.content)
    print("Font downloaded successfully.")
except Exception as e:
    print(f"Failed to download font: {e}")
