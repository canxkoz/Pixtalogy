from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import json
import base64
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from mistral_client import get_mistral_response, encode_file  # Import Mistral client

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db = SQLAlchemy(app)

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

# Create the database
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return render_template('home.html')

# Signup Route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        dob = request.form['dob']
        gender = request.form['gender']
        weight = request.form['weight']
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        if User.query.filter_by(email=email).first():
            return "User already exists, please login."
        
        new_user = User(email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        create_user_folder(email, name, dob, gender, weight)

        return redirect(url_for('login'))
    return render_template('signup.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user'] = user.email
            return redirect(url_for('chat'))

    return render_template('login.html')

# Chat Route for Text Input
@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'user' not in session:
        return redirect(url_for('login'))

    user_email = session['user']

    # Load user's personal information from their folder
    user_folder = os.path.join('user_data', user_email)
    personal_info_path = os.path.join(user_folder, 'personal_information.json')

    if os.path.exists(personal_info_path):
        with open(personal_info_path, 'r') as file:
            personal_info = json.load(file)
    else:
        personal_info = None

    # If it's a POST request (message sending)
    if request.method == 'POST':
        data = request.get_json()
        message = data.get('message')

        # Send the message to Mistral client for processing
        response = get_mistral_response(message)

        if response:
            save_chat_log(user_email, f"User: {message}\nLLM: {response}")
            return jsonify({'response': response})
        else:
            return jsonify({'error': 'No response from LLM'}), 500

    # If it's a GET request (page load)
    return render_template('chat.html', user_email=user_email, personal_info=personal_info)


@app.route('/upload_file', methods=['POST'])
def upload_file():
    if 'user' not in session:
        return jsonify({'error': 'User not logged in'}), 403

    user_email = session['user']
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        # Ensure the user-specific upload folder exists
        user_upload_folder = os.path.join('user_data', user_email, 'upload')
        if not os.path.exists(user_upload_folder):
            os.makedirs(user_upload_folder)

        # Save the file in the user-specific folder
        filename = secure_filename(file.filename)
        file_path = os.path.join(user_upload_folder, filename)
        file.save(file_path)

        # Check file extension and return appropriate response
        file_ext = os.path.splitext(filename)[1].lower()
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif']

        if file_ext in image_extensions:
            # Handle image file
            with open(file_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            response = get_mistral_response(content=encoded_string, is_image=True)
            if response:
                return jsonify({'response': response, 'image_data': f"data:image/png;base64,{encoded_string}"})
            else:
                return jsonify({'error': 'No response from LLM'}), 500
        else:
            # Handle document upload (PDF, DOCX, etc.)
            response = get_mistral_response(content=f"User uploaded a document: {filename}", is_image=False)
            if response:
                save_chat_log(user_email, f"User uploaded a document: {filename}. LLM: {response}")
                return jsonify({'response': response, 'file_path': f"/{file_path}"})
            else:
                return jsonify({'error': 'No response from LLM'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Reset the chat conversation
@app.route('/reset', methods=['POST'])
def reset_conversation():
    if 'user' not in session:
        return jsonify({'error': 'User not logged in'}), 403

    user_email = session['user']
    return jsonify({'message': 'Conversation has been reset.'})

# Utility function to save chat or API response logs in the user folder
def save_chat_log(user_email, content):
    date_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    chat_folder = os.path.join('user_data', user_email, 'chat', date_time)
    os.makedirs(chat_folder, exist_ok=True)
    chat_file = os.path.join(chat_folder, 'chat_session.txt')
    with open(chat_file, 'w') as f:
        f.write(content)

# Utility function to create user folder
def create_user_folder(email, name, dob, gender, weight):
    user_folder = os.path.join('user_data', email)
    os.makedirs(user_folder, exist_ok=True)
    
    os.makedirs(os.path.join(user_folder, 'chat'), exist_ok=True)
    os.makedirs(os.path.join(user_folder, 'upload'), exist_ok=True)

    personal_info = {
        "name": name,
        "date_of_birth": dob,
        "gender": gender,
        "weight": weight
    }
    
    personal_info_path = os.path.join(user_folder, 'personal_information.json')
    with open(personal_info_path, 'w') as f:
        json.dump(personal_info, f)

if __name__ == '__main__':
    app.run(debug=True)
