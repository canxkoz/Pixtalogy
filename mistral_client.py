import os
from dotenv import load_dotenv
from mistralai import Mistral

# Load the API key from the .env file
load_dotenv()
api_key = os.getenv("MISTRAL_API_KEY")

# Check if the API key is loaded properly
if api_key is None:
    print("Error: API key not found. Please set MISTRAL_API_KEY in your .env file.")
else:
    print(f"Mistral API Key loaded: {api_key}")

# Initialize the Mistral client
client = Mistral(api_key=api_key)

def encode_file(file, is_image=False):
    """Encode the image to base64."""
    try:
        if is_image:
            return base64.b64encode(file.read()).decode('utf-8')
        else:
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None
def get_mistral_response(content, is_image=False, medical_data=None):
    """Send content to Mistral API and return response."""
    model = "pixtral-12b-2409"

    # Initialize messages variable
    messages = []

    # Text input: Interpret medical data and symptoms
    if medical_data:
        messages = [
            {
                "role": "user",
                "content": f"Given the following symptoms and medical history, provide recommendations: {medical_data}"
            }
        ]
    
    # Image input: Medical imaging analysis
    elif is_image:
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Describe this medical image. Provide relevant information in 5 bullet points."
                    },
                    {
                        "type": "image_url",
                        "image_url": f"data:image/jpeg;base64,{content}"
                    }
                ]
            }
        ]
    else:
        # Regular text input handling
        messages = [
            {
                "role": "user",
                "content": content
            }
        ]

    try:
        chat_response = client.chat.complete(
            model=model,
            messages=messages
        )
        print(f"Successful Mistral API Response: {chat_response}")
        return chat_response.choices[0].message.content
    except Exception as e:
        print(f"Mistral API Error: {e}")
        return None
