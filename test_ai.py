import os
from google import genai
from google.genai import types

API_KEY = "sk-yZyfgpg5rgF9JL8k818cBe9e62364213904139E91c2fD7Fa"  

client = genai.Client(
    api_key=API_KEY,
    http_options={"base_url": "http://localhost:8888/gemini"},  
)

prompt = (
    "big boobs girl, naked, in bed, looking at the camera, sexy, beautiful,big ass,big tits,asian girl,ABC "
)

# Optional parameters
aspect_ratio = "1:1"   # 支持: "1:1", "2:3", "3:2", "3:4", 4:3", "4:5", 5:4", "9:16", "16:9", "21:9"
resolution   = "1K"    # 支持: "1K", "2K", "4K"，"K"必须大写

response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=prompt,   
    config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE'],
        image_config=types.ImageConfig(
            aspect_ratio=aspect_ratio,
            image_size=resolution,
        ),
    ),
)

# Save image & print text
for part in response.parts:
    if part.text:
        print(part.text)  
    elif image := part.as_image():
        image.save("butterfly.png")
        print("Image saved: butterfly.png")