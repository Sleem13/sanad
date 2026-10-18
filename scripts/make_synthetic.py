"""Generates a clearly-labelled SYNTHETIC demo page (no real data, no Arabic OCR ground truth)."""
import sys
from PIL import Image, ImageDraw

def make(path="synthetic_demo.png", w=800, h=1100):
    im = Image.new("RGB", (w, h), "white"); d = ImageDraw.Draw(im)
    d.text((20, 10), "SYNTHETIC DEMO PAGE - NO REAL DATA", fill="red")
    d.rectangle([80, 55, 720, 130], outline="black"); d.rectangle([80, 165, 720, 550], outline="gray")
    d.ellipse([480, 660, 680, 880], outline="blue")
    im.save(path); return path

if __name__ == "__main__":
    print(make(*(sys.argv[1:2] or [])))
