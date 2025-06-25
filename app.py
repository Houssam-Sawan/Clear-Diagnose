from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin

from livereload import Server
from config import Config
from models import *  # Import All models here
import os

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

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
            message=message,
            status='Unread'
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
        content = request.form.get('message')
        if content:
            msg = Message(
                conversation_id=convo.id,
                sender_id=current_user.id,
                content=content
            )
            db.session.add(msg)
            db.session.commit()
            flash("Message sent.", "success")
        return redirect(url_for('conversation', conversation_id=conversation_id))

    return render_template('conversation.html', conversation=convo)


if __name__ == "__main__":
    # Ensure the instance folder exists
    with app.app_context():  # Needed for DB operations
        db.create_all()      # Creates the database and tables
    server = Server(app.wsgi_app)
    server.watch("**/*.py")  # Watch Python files for changes
    server.watch("templates/*.html")
    server.watch("static/*.*")
    server.serve(host="0.0.0.0", port=5000, debug=True) 
