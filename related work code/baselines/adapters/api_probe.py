import base64, io, json, os, sys, time
from openai import OpenAI
from PIL import Image, ImageDraw
client, model = OpenAI(), os.environ["OPENAI_MODEL"]
print("model:", model)
t = time.time()
r = client.chat.completions.create(model=model, messages=[{"role": "user", "content": "Reply with the word ok."}])
print("text:", r.choices[0].message.content.strip()[:40], f"{time.time()-t:.1f}s")
img = Image.new("RGB", (128, 128), "white"); ImageDraw.Draw(img).rectangle([30, 30, 100, 100], fill="red")
b = io.BytesIO(); img.save(b, "PNG"); url = "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()
try:
    r = client.chat.completions.create(model=model, messages=[{"role": "user", "content": [
        {"type": "text", "text": "What colour is the square? One word."}, {"type": "image_url", "image_url": {"url": url}}]}])
    print("image:", r.choices[0].message.content.strip()[:40])
except Exception as e:
    print("image: FAILED", type(e).__name__, str(e)[:200])
