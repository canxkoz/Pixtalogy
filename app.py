from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import json
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import base64
from flask_session import Session

# Import different Mistral client files
from models.mistral_client_radiologist import get_mistral_response as get_mistral_response_radiologist
from models.mistral_client_mental_health import get_mistral_response as get_mistral_response_mental_health
from models.mistral_client_report_explainer import get_mistral_response as get_mistral_response_report_explainer
from models.mistral_client_general_doctor import get_mistral_response as get_mistral_response_general_doctor
from models.mistral_client_dietitian import get_mistral_response as get_mistral_response_dietitian

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Use a secure random key
app.config['SESSION_TYPE'] = 'filesystem'  # Store sessions on the filesystem
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True

db = SQLAlchemy(app)
Session(app)  # Initialize Flask-Session

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

# Create the database
with app.app_context():
    db.create_all()

# Helper Functions
def save_chat_log(user_email, content):
    date_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    chat_folder = os.path.join('user_data', user_email, 'chat', date_time)
    os.makedirs(chat_folder, exist_ok=True)
    chat_file = os.path.join(chat_folder, 'chat_session.txt')
    with open(chat_file, 'w') as f:
        f.write(content)

def create_user_folder(email, name, dob, gender, weight):
    user_folder = os.path.join('user_data', email)
    os.makedirs(user_folder, exist_ok=True)
    os.makedirs(os.path.join(user_folder, 'chat'), exist_ok=True)
    os.makedirs(os.path.join(user_folder, 'upload'), exist_ok=True)
    personal_info = {"name": name, "date_of_birth": dob, "gender": gender, "weight": weight}
    personal_info_path = os.path.join(user_folder, 'personal_information.json')
    with open(personal_info_path, 'w') as f:
        json.dump(personal_info, f)

# Flask Routes
@app.route('/')
def home():
    return render_template('home.html')

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user'] = user.email
            session['conversation_history'] = []  # Reset the conversation history on login
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# Chat Routes
@app.route('/radiologist_chat', methods=['GET', 'POST'])
def radiologist_chat():
    return handle_chat('Radiologist', get_mistral_response_radiologist)

@app.route('/mental_health_chat', methods=['GET', 'POST'])
def mental_health_chat():
    return handle_chat('Mental Health Guide', get_mistral_response_mental_health)

@app.route('/report_explainer_chat', methods=['GET', 'POST'])
def report_explainer_chat():
    return handle_chat('Report Explainer', get_mistral_response_report_explainer)

@app.route('/general_doctor_chat', methods=['GET', 'POST'])
def general_doctor_chat():
    return handle_chat('General Doctor', get_mistral_response_general_doctor)

@app.route('/dietitian_chat', methods=['GET', 'POST'])
def dietitian_chat():
    return handle_chat('Dietitian', get_mistral_response_dietitian)

def handle_chat(chat_type, get_mistral_response):
    if 'user' not in session:
        return redirect(url_for('login'))

    user_email = session['user']
    if request.method == 'POST':
        data = request.get_json()
        message = data.get('message')
        if not message:
            return jsonify({'error': 'No message provided'}), 400

        conversation_history = session.get('conversation_history', [])
        conversation_history.append({"role": "user", "content": message})

        # Get response from LLM and prevent re-uploading image
        response = get_mistral_response(message, conversation_history=conversation_history)
        if response:
            save_chat_log(user_email, f"User: {message}\nLLM: {response}")
            conversation_history.append({"role": "assistant", "content": response})
            session['conversation_history'] = conversation_history
            return jsonify({'response': response})
        else:
            return jsonify({'error': 'No response from LLM'}), 500

    return render_template(f'{chat_type.lower().replace(" ", "_")}_chat.html', user_email=user_email)

# Route for file upload based on chat type
@app.route('/upload_file', methods=['POST'])
def upload_file():
    if 'user' not in session:
        return jsonify({'error': 'User not logged in'}), 403

    chat_type = request.args.get('chat_type')
    if not chat_type:
        return jsonify({'error': 'No chat type provided'}), 400

    get_mistral_response = {
        'radiologist': get_mistral_response_radiologist,
        'mental_health': get_mistral_response_mental_health,
        'report_explainer': get_mistral_response_report_explainer,
        'general_doctor': get_mistral_response_general_doctor,
        'dietitian': get_mistral_response_dietitian
    }.get(chat_type)

    if not get_mistral_response:
        return jsonify({'error': 'Invalid chat type'}), 400

    user_email = session['user']
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        user_upload_folder = os.path.join('user_data', user_email, 'upload')
        if not os.path.exists(user_upload_folder):
            os.makedirs(user_upload_folder)

        filename = secure_filename(file.filename)
        file_path = os.path.join(user_upload_folder, filename)
        file.save(file_path)

        file_ext = os.path.splitext(filename)[1].lower()
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif']

        if file_ext in image_extensions:
            with open(file_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            # Get response from LLM based on the uploaded image
            response = get_mistral_response(content=encoded_string, is_image=True, conversation_history=session.get('conversation_history', []))
            if response:
                return jsonify({'response': response, 'image_data': f"data:image/png;base64,{encoded_string}"})
            else:
                return jsonify({'error': 'No response from LLM'}), 500
        else:
            response = get_mistral_response(content=f"User uploaded a document: {filename}", is_image=False)
            if response:
                return jsonify({'response': response, 'file_path': f"/{file_path}"})
            else:
                return jsonify({'error': 'No response from LLM'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()  # Clear the session data
    return jsonify({'success': True})  # Return a success response


if __name__ == '__main__':
    app.run(debug=True)
