from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from flask_migrate import Migrate
from openai import OpenAI
#from gpt4all import GPT4All
from livereload import Server
from config import Config
from models import *  # Import All models here
import os

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

migrate = Migrate(app, db)  # Initialize Flask-Migrate for database migrations

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key="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",
)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect to login page if not authenticated
# Define a user class that extends UserMixin for Flask-Login compatibility
class UserLogin(UserMixin, User):
    pass

@login_manager.user_loader
def load_user(user_id):
    """Load a user by their ID."""
    return UserLogin.query.get(int(user_id))

@app.before_request
def create_tables():
    """Create database tables before the first request."""
    db.create_all()


@app.route("/")
def home():
    return render_template("index.html", user=current_user)

@app.route("/login" , methods=["GET", "POST"])
def login():
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.password_hash == password:  # Assuming password is stored in plain text for simplicity
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid username or password.')
    return render_template("login.html")

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('new_username')
        email = request.form.get('new_email')
        password = request.form.get('new_password')
        if User.query.filter_by(username=username).first():
            flash('Username already taken.')
        else:
            user = User(username=username, email=email, password_hash=password)
            #user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for('dashboard'), user=current_user)
    return render_template('signup.html')

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route("/dashboard")
def dashboard():
    conversations = Conversation.query.filter_by(user_id=current_user.id).order_by(Conversation.timestamp.desc()).all()
    return render_template('dashboard.html', conversations=conversations)

@app.route('/conversation/new', methods=['GET', 'POST'])
@login_required
def new_conversation():
    if request.method == 'POST':
        subject = request.form.get('subject')
        message = request.form.get('message')
        if not subject or not message:
            flash('Subject and message are required.', 'danger')
            return redirect(url_for('new_conversation'))

        convo = Conversation(
            user_id=current_user.id,
            subject=subject,
            role= current_user.role
        )
        db.session.add(convo)
        db.session.commit()
        flash('Conversation created successfully.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('new_conversation.html')

@app.route('/conversation/<int:conversation_id>', methods=['GET', 'POST'])
@login_required
def conversation(conversation_id):
    convo = Conversation.query.filter_by(id=conversation_id, user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        user_input  = request.form.get('message')
        if user_input:
            msg = Message(
                conversation_id=convo.id,
                sender_id=current_user.id,
                content=user_input
            )
            db.session.add(msg)
            db.session.commit()
            flash("Message sent.", "success")

            # Call the Online medical bot API
            bot_response = ask_medical_bot(user_input)
            #bot_response = ask_local_bot(user_input)
            #bot_response = "test response"  # Placeholder for actual bot response

            bot_msg = Message(
                conversation_id=convo.id,
                sender_id=0,  # Assuming 0 is the bot's ID
                content=bot_response
            )
            db.session.add(bot_msg)
            db.session.commit()
        return redirect(url_for('conversation', conversation_id=conversation_id))

    return render_template('conversation.html', conversation=convo)

@app.route('/chat/<int:conversation_id>', methods=['GET', 'POST'])
@login_required
def chat(conversation_id):
    convo = Conversation.query.filter_by(id=conversation_id, user_id=current_user.id).first_or_404()
    conversations = Conversation.query.filter_by(user_id=current_user.id).order_by(Conversation.timestamp.desc()).all()

    if request.method == 'POST':
        user_input  = request.form.get('message')
        if user_input:
            msg = Message(
                conversation_id=convo.id,
                sender_id=current_user.id,
                content=user_input
            )
            db.session.add(msg)
            db.session.commit()
            flash("Message sent.", "success")

            # Call the Online medical bot API
            bot_response = ask_medical_bot(user_input)
            #bot_response = ask_local_bot(user_input)
            #bot_response = "test response"  # Placeholder for actual bot response

            bot_msg = Message(
                conversation_id=convo.id,
                sender_id=0,  # Assuming 0 is the bot's ID
                content=bot_response
            )
            db.session.add(bot_msg)
            db.session.commit()
        return redirect(url_for('chat', conversation_id=conversation_id))

    return render_template('chat.html', conversation=convo, conversations=conversations)
"""
gpt_model = GPT4All("Mistral-7B-Instruct-v0.3.IQ1_M.gguf", model_path=".", allow_download=False)

def ask_local_bot(prompt):
    system_prompt = (
        "You are a cautious and helpful medical assistant. "
        "Based on the user's symptoms, suggest possible causes and remind them to consult a doctor. "
        "Make your answers as short as possible. "
        "Ask for more information if needed, untillyou narrow down the possibilities. "
        "you can ask personal questions like age and gender to narrow down the possibilities. "
        "If the user asks about a specific disease, provide a brief description. "
        "If the user asks about a specific symptom, provide a brief description. "
        "Only return the final reply, not internal thoughts or reasoning."
    )
    response = gpt_model.chat_completion(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        max_tokens=200
    )
    return response['choices'][0]['message']['content']
"""
MODEL = "mistralai/mistral-small-3.2-24b-instruct:free"

def ask_medical_bot(user_input):
    system_prompt = (
        "You are a cautious and helpful medical assistant. "
        "Based on the user's symptoms, suggest possible causes and remind them to consult a doctor. "
        "Make your answers as short as possible. "
        "Ask for more information if needed, untillyou narrow down the possibilities. "
        "you can ask personal questions like age and gender to narrow down the possibilities. "
        "If the user asks about a specific disease, provide a brief description. "
        "If the user asks about a specific symptom, provide a brief description. "
        "Only return the final reply, not internal thoughts or reasoning."

    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
    )

    try:
        return response.choices[0].message.content
    except Exception as e:
        print(f"[GPT Error] {e}")
        return "Sorry, something went wrong while generating a response. Please try again."


if __name__ == "__main__":
    # Ensure the instance folder exists
    with app.app_context():  # Needed for DB operations
        db.create_all()      # Creates the database and tables
    server = Server(app.wsgi_app)
    server.watch("**/*.py")  # Watch Python files for changes
    server.watch("templates/*.html")
    server.watch("static/*.*")
    server.serve(host="0.0.0.0", port=5000, debug=True) 
