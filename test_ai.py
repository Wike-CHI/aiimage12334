import os
from google import genai
from google.genai import types

API_KEY = "sk-9pI1g5gQqtCuvbzOE0Fb3467901b4cAb801f1cE333F27886"  

client = genai.Client(
    api_key=API_KEY,
    http_options={"base_url": "https://aihubmix.com/gemini"},  
)

prompt = (
    "Da Vinci style anatomical sketch of a dissected Monarch butterfly. "
    "Detailed drawings of the head, wings, and legs on textured parchment with notes in English."
)

# Optional parameters
aspect_ratio = "1:1"   # 支持: "1:1", "2:3", "3:2", "3:4", 4:3", "4:5", 5:4", "9:16", "16:9", "21:9"
resolution   = "4K"    # 支持: "1K", "2K", "4K"，"K"必须大写

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