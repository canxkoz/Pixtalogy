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

def get_mistral_response(content, is_image=False, medical_data=None, conversation_history=None):
    """Send content to Mistral API and return response."""
    model = "pixtral-12b-2409"
    messages = []

    # Include conversation history if provided, but truncate to the last N messages
    if conversation_history:
        messages.extend(conversation_history[-8:])  # Keep only the last 8 messages

    # Construct the user message based on the input type
    if medical_data:
        messages.append({
            "role": "user",
            "content": f"ou are an expert in understanding and evaluating blood reports and prescriptions, specializing as a general physician. I will ask you questions about my reports and prescriptions. Provide responses within 3 sentences or 20 words. Grade my health status as Normal, Critical, or Very Critical based on the reports. For Critical or Very Critical conditions, provide names and coordinates of nearby hospitals. Suggest medications or lifestyle changes for Non-Critical conditions: {medical_data}"
        })
    elif is_image:
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "You are an expert in understanding and evaluating blood reports and prescriptions, specializing as a general physician. I will ask you questions about my reports and prescriptions. Provide responses within 3 sentences or 20 words. Grade my health status as Normal, Critical, or Very Critical based on the reports. For Critical or Very Critical conditions, provide names and coordinates of nearby hospitals. Suggest medications or lifestyle changes for Non-Critical conditions."
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
            "content": f"You are a report explainer. Assist with the following inquiry: {content}"
        })

    try:
        chat_response = client.chat.complete(model=model, messages=messages)
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
    text_input = "What are the possible conditions based on the symptoms?"
    text_response = get_mistral_response(text_input, conversation_history=conversation_history)
    print("Text Response:", text_response)

    # Update conversation history with text response
    conversation_history.append({"role": "user", "content": text_input})
    conversation_history.append({"role": "assistant", "content": text_response})
