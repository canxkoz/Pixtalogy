import os
import base64
import logging
from dotenv import load_dotenv
from mistralai import Mistral

# Load the API key from the .env file
load_dotenv()
api_key = os.getenv("MISTRAL_API_KEY")

# Check if the API key is loaded properly
if api_key is None:
    logging.error("Error: API key not found. Please set MISTRAL_API_KEY in your .env file.")
else:
    logging.info("Mistral API Key loaded successfully.")

# Initialize the Mistral client
client = Mistral(api_key=api_key)

def encode_file(file, is_image=False):
    """Encode the image to base64."""
    try:
        if is_image:
            return base64.b64encode(file.read()).decode('utf-8')
        return None
    except Exception as e:
        logging.error(f"Error encoding file: {e}")
        return None

def get_mistral_response(content, is_image=False, mental_health_data=None, conversation_history=None):
    """Send content to Mistral API and return response."""
    model = "pixtral-12b-2409"
    messages = []

    # Include conversation history if provided, but truncate to the last 8 messages
    if conversation_history:
        messages.extend(conversation_history[-8:])  # Keep only the last 8 messages

    # Construct the user message based on the input type
    if mental_health_data:
        messages.append({
            "role": "user",
            "content": f"Given the following mental health data, provide recommendations: {mental_health_data[:150]}"  # Limiting data length
        })
    elif is_image:
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "You are a psychiatrist specializing in mental health. I will be asking you questions about my mental health concerns. Provide answers within 3 sentences or 20 words. Assess my condition as Normal, Critical, or Very Critical. For Critical or Very Critical conditions, provide names and coordinates of nearby mental health facilities. Suggest coping strategies or treatment options for Non-Critical conditions."
                },
                {
                    "type": "image_url",
                    "image_url": f"data:image/jpeg;base64,{content}"
                }
            ]
        })
    else:
        messages.append({
            "role": "user",
            "content": f"You are a mental health professional. Assist with the following inquiry in a maximum of 20 words: {content[:150]}"  # Limiting text input length
        })

    try:
        # Adjusting token size limit
        chat_response = client.chat.complete(model=model, messages=messages, max_tokens=50)  # Limit output tokens

        logging.info(f"Successful Mistral API Response: {chat_response}")

        # Ensure choices are available before accessing
        if chat_response.choices:
            return chat_response.choices[0].message.content
        logging.error("No response choices available from Mistral API.")
        return "No response from the model."
    except Exception as e:
        logging.error(f"Mistral API Error: {e}")
        return "Error occurred while communicating with the Mistral API."

if __name__ == "__main__":
    # Example usage
    conversation_history = []  # Initialize conversation history

    # Example for uploading and processing an image
    with open("path_to_image.jpg", "rb") as image_file:
        encoded_image = encode_file(image_file, is_image=True)

    # Getting a response based on the uploaded image
    image_response = get_mistral_response(encoded_image, is_image=True, conversation_history=conversation_history)
    print("Image Response:", image_response)

    # Updating conversation history with image upload
    conversation_history.append({"role": "user", "content": "Image uploaded for analysis."})
    conversation_history.append({"role": "assistant", "content": image_response})

    # Example for sending a text message
    text_input = "What are the possible mental health conditions based on the symptoms?"
    text_response = get_mistral_response(text_input, conversation_history=conversation_history)
    print("Text Response:", text_response)

    # Update conversation history with text response
    conversation_history.append({"role": "user", "content": text_input})
    conversation_history.append({"role": "assistant", "content": text_response})
