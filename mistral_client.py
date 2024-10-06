import os
import base64
import requests
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


def get_mistral_response(content, is_image=False, medical_data=None, conversation_history=None, chat_type=None):
    """Send content to Mistral API and return response."""
    model = "pixtral-12b-2409"  # Adjust based on the Mistral model being used

    # Initialize messages variable
    messages = []

    # Include conversation history if provided, but truncate to the last N messages
    if conversation_history:
        messages.extend(conversation_history[-10:])  # Keep only the last 10 messages

    # Handling medical data input (for text-based medical questions)
    if medical_data:
        messages.append({
            "role": "user",
            "content": f"Given the following symptoms and medical history, provide recommendations: {medical_data}"
        })

    # Handling image input for medical imaging analysis (like radiology)
    elif is_image and chat_type == "Radiologist":
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "You are an expert radiologist. Diagnose the patients with the following CT Scans. Provide a detailed evaluation of each CT Scan and provide a report."
                },
                {
                    "type": "image_url",
                    "image_url": f"data:image/jpeg;base64,{content}"
                }
            ]
        })
    else:
        # Regular text input handling for different chat types (contextualize based on chat_type)
        if chat_type == "Radiologist":
            context = "You are an expert radiologist providing diagnoses and medical imaging analysis."
        elif chat_type == "Mental Health Guide":
            context = "You are a mental health guide offering support and advice."
        elif chat_type == "Report Explainer":
            context = "You are an expert in explaining medical reports in a simple and understandable way."
        elif chat_type == "General Doctor":
            context = "You are a general doctor providing advice on general health concerns."
        elif chat_type == "Dietitian":
            context = "You are a dietitian providing nutritional advice."

        # Add context to the conversation
        messages.append({
            "role": "user",
            "content": f"{context}\n{content}"
        })

    try:
        # Example call to the Mistral API (adjust as per actual API details)
        response = requests.post(
            'https://api.mistral.ai/chat',  # Replace with the actual Mistral API endpoint
            json={
                "model": model,
                "messages": messages
            },
            headers={'Authorization': f'Bearer {api_key}'},  # Replace with your actual auth header
            verify=False  # Temporary bypass of SSL verification (remove for production)
        )
        response.raise_for_status()  # Raise an error for bad HTTP status codes
        return response.json().get('choices')[0]['message']['content']
    except requests.exceptions.SSLError as e:
        print(f"Mistral API SSL Error: {e}")
        return None
    except Exception as e:
        print(f"Mistral API Error: {e}")
        return None
