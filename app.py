from datetime import timedelta
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from flask_login import *
from flask_migrate import Migrate
from groq import Groq
from livereload import Server
from config import Config
from models import *  # Import All models here
import os

app = Flask(__name__)
app.config.from_object(Config)
#GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

db.init_app(app)

@user_logged_in.connect_via(app)
def when_user_logged_in(sender, user):
    user.is_online = True
    db.session.commit()

@user_logged_out.connect_via(app)
def when_user_logged_out(sender, user):
    user.is_online = False
    db.session.commit()

migrate = Migrate(app, db)  # Initialize Flask-Migrate for database migrations

# Initialize OpenAI client with the base URL and API key

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

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

@app.before_request
def update_last_seen():
    if current_user.is_authenticated:
        current_user.last_login = datetime.utcnow()
        db.session.commit()
@property
def is_online(self):
    return self.last_login and datetime.utcnow() - self.last_login < timedelta(minutes=30)

def mark_all_offline():
    User.query.update({User.is_online: False})
    db.session.commit()

@app.template_filter('doctor_name')
def doctor_name_filter(doctor_id):
    doctor = Doctor.query.filter_by(user_id=doctor_id).first()
    return doctor.name if doctor else "Unknown"


@app.route("/")
def home():
    return render_template("index.html", user=current_user)

@app.route("/test")
def test():
    return os.environ.get('GROQ_API_KEY')

@app.route("/login" , methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('chat', conversation_id=0))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.password_hash == password:  # Assuming password is stored in plain text for simplicity
            login_user(user)
            return redirect(url_for('dashboard'))
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
            return redirect(url_for('dashboard'))
    return render_template('signup.html')

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    conversations = Conversation.query.filter_by(user_id=current_user.id).order_by(Conversation.timestamp.desc()).all()
    doctors = db.session.query(User).join(Doctor).filter(User.role == 'doctor').all()
    return render_template('dashboard.html', conversations=conversations, doctors=doctors, user=current_user)

@app.route('/new_chat', defaults={'doctor_id': None}, methods=['GET', 'POST'])
@app.route('/new_chat/<int:doctor_id>', methods=['GET', 'POST'])
@login_required
def new_chat(doctor_id):
    if request.method == 'POST':
        # Create a new conversation for the current userm
        new_message = request.form.get('message')
        
        # Create a new conversation with the current user
        new_subject = new_message[:40]  # Use the first 50 characters of the message as the subject
        new_conv = Conversation(user_id=current_user.id, subject=new_subject, role='User', doctor_id=doctor_id, timestamp=datetime.now())
        db.session.add(new_conv)
        db.session.commit()
        msg = Message( conversation_id=new_conv.id, sender_id=current_user.id, role='User', content=new_message, timestamp=datetime.now())
        db.session.add(msg)
        db.session.commit()

        if not doctor_id:
            # Call the Online medical bot API
            bot_response = ask_medical_bot(new_message)
            #bot_response = ask_local_bot(user_input)
            #bot_response = "test response"  # Placeholder for actual bot response

            bot_msg = Message(
                conversation_id=new_conv.id,
                sender_id=0,  # Assuming 0 is the bot's ID
                content=bot_response,
                role='Assistant',
                timestamp=datetime.now()
            )
            db.session.add(bot_msg)
            db.session.commit()

    # Redirect to the new conversation page
    return redirect(url_for('chat', doctor_id=doctor_id, conversation_id=new_conv.id))

@app.route('/chat/<int:conversation_id>', defaults={'doctor_id': None}, methods=['GET', 'POST'])
@app.route('/chat/<int:conversation_id>/doctor/<int:doctor_id>', methods=['GET', 'POST'])
@login_required
def chat(conversation_id, doctor_id):
    doctors = db.session.query(User).join(Doctor).filter(User.role == 'doctor').all()

    # test sample for doctors data
    #doctors = [{'id': 1, 'name': 'Dr. Smith', 'specialty': 'Cardiology' , 'is_online':True}]
    conversations = Conversation.query.filter_by(user_id=current_user.id).order_by(Conversation.timestamp.desc()).all()
    doctor_conversations = Conversation.query.filter_by(doctor_id=current_user.id).order_by(Conversation.timestamp.desc()).all()
    
    if current_user.role == 'doctor':
        # If the user is a doctor, show their conversations with patients
        conversations = doctor_conversations

    # If conversation_id is 0, redirect to the Show new chat dialog
    if conversation_id == 0:
        # Fetch the conversation and its messages
        return render_template('chat.html', conversations=conversations, doctors=doctors,doctor_id=doctor_id, new_chat=True)
    user_id = request.args.get('user_id', type=int)

    if user_id :
        # If user_id is provided, filter conversations by user_id
        convo = Conversation.query.filter_by(id=conversation_id, user_id=user_id, doctor_id=current_user.id).first_or_404()
    else:
        convo = Conversation.query.filter_by(id=conversation_id, user_id=current_user.id).first_or_404()

    if request.method == 'POST' :
        user_input  = request.form.get('message')
        
        if user_input:
            
            msg = Message(
                conversation_id=convo.id,
                sender_id=current_user.id,
                content=user_input,
                role=current_user.role,  
                timestamp=datetime.now()
            )
            db.session.add(msg)
            db.session.commit()

            if not convo.doctor_id:
                # Call the Online medical bot API
                bot_response = ask_medical_bot(user_input)
                #bot_response = ask_local_bot(user_input)
                #bot_response = "test response"  # Placeholder for actual bot response

                bot_msg = Message(
                    conversation_id=convo.id,
                    sender_id=0,  # Assuming 0 is the bot's ID
                    content=bot_response,
                    role='Assistant',
                    timestamp=datetime.now()
                )
                db.session.add(bot_msg)
                db.session.commit()
                return redirect(url_for('chat', conversation_id=conversation_id, new_chat=False))
            elif current_user.role == 'doctor':
                # If the conversation is with a patient, redirect to the chat page
                return redirect(url_for('chat', conversation_id=conversation_id,doctor_id=convo.doctor_id, user_id=convo.user_id))
            else:
                # If the conversation is with a doctor, redirect to the chat page
                return redirect(url_for('chat', conversation_id=conversation_id,doctor_id=convo.doctor_id))
    
    return render_template('chat.html', conversations=conversations, conversation=convo, doctors=doctors, new_chat=False)


    
@app.route('/chatt/<int:conversation_id>/delete', methods=['POST'])
@login_required
def delete_conversation(conversation_id):
    conversation = Conversation.query.filter_by(id=conversation_id, user_id=current_user.id).first_or_404()

    # Delete all messages in the conversation
    Message.query.filter_by(conversation_id=conversation.id).delete()

    # Then delete the conversation itself
    db.session.delete(conversation)
    db.session.commit()

    #flash("Conversation deleted successfully.", "success")
    return redirect(url_for('chat', conversation_id=0)) 

@app.route('/chattt/<int:conversation_id>/delete', methods=['POST'])
@login_required
def deletee_conversation(conversation_id):
    conversation = Conversation.query.filter_by(id=conversation_id, user_id=current_user.id).first_or_404()

    # Delete all messages in the conversation
    Message.query.filter_by(conversation_id=conversation.id).delete()

    # Then delete the conversation itself
    db.session.delete(conversation)
    db.session.commit()

    #flash("Conversation deleted successfully.", "success")
    return redirect(url_for('dashboard'))
MODEL = "llama3-70b-8192"

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

### --- Medical Consultation Form Routes --- ###

# 1. Display the medical consultation form (questions.html)
@app.route('/consultation')
@login_required  
def consultation_form():
    """Renders the medical consultation form page."""
    doctor_id = request.args.get('doctor_id', type=int)
    if doctor_id:
        return render_template('question.html', doctor_id=doctor_id)
    return render_template('question.html')

# 2. Handle form submission and send the data via email
@app.route('/submit-consultation', methods=['POST'])
@login_required 

def submit_consultation():
    """Handles form submission, saves it to the database, and then sends the data via email."""
    if request.method == 'POST':
        form_data = request.form
        doctor_id = request.form.get('doctor_id', type=int)

        # create a new Consultation object with the form data
        new_consultation = Consultation(
            user_id=current_user.id,
            full_name=form_data.get('full_name'),
            age=form_data.get('age'),
            gender=form_data.get('gender'),
            main_complaint=form_data.get('main_complaint'),
            onset=form_data.get('onset'),
            location=form_data.get('location'),
            character=form_data.get('character'),
            duration=form_data.get('duration'),
            aggravating_factors=form_data.get('aggravating'),
            alleviating_factors=form_data.get('alleviating'),
            related_symptoms=form_data.get('related_symptoms'),
            severity=form_data.get('severity'),
            chronic_diseases=", ".join(form_data.getlist('chronic_diseases')), # Handle list
            current_medications=form_data.get('medications'),
            allergies=form_data.get('allergies'),
            previous_surgeries=form_data.get('surgeries'),
            smoking_status=form_data.get('smoking'),
            doctor_id=doctor_id,  
        )
        
        try:
            db.session.add(new_consultation)
            db.session.commit()


            # redirect to the thank you page after successful submission
            flash('Form submitted and saved successfully!', 'success')
            return redirect(url_for('thank_you'), consultation_id=new_consultation.id)

        except Exception as e:
            db.session.rollback() # Rollback the session in case of failure
            flash(f'An error occurred: {e}', 'danger')
            return redirect(url_for('consultation_form'))

    return redirect(url_for('consultation_form'))

# 3. Route for the thank you page after successful submission
@app.route('/thank-you/<int:consultation_id>', methods=['GET'])
def thank_you(consultation_id):
    """Displays a thank you page after successful form submission."""
    consultation = Consultation.query.get_or_404(consultation_id)
    doctor_id = consultation.doctor_id
    # Create a new conversation for the current userm
    new_message = format_consultation_data(consultation_id)
    
    # Create a new conversation with the current user
    new_subject = new_message[:40]  # Use the first 50 characters of the message as the subject
    new_conv = Conversation(user_id=current_user.id, subject=new_subject, role='User', doctor_id=doctor_id, timestamp=datetime.now())
    db.session.add(new_conv)
    db.session.commit()
    msg = Message( conversation_id=new_conv.id, sender_id=current_user.id, role='User', content=new_message, timestamp=datetime.now())
    db.session.add(msg)
    db.session.commit()

    if not doctor_id:
        # Call the Online medical bot API
        bot_response = ask_medical_bot(new_message)
        #bot_response = ask_local_bot(user_input)
        #bot_response = "test response"  # Placeholder for actual bot response

        bot_msg = Message(
            conversation_id=new_conv.id,
            sender_id=0,  # Assuming 0 is the bot's ID
            content=bot_response,
            role='Assistant',
            timestamp=datetime.now()
        )
        db.session.add(bot_msg)
        db.session.commit()
    return render_template('thanks.html', consultation=consultation, conversation=new_conv)


### ----------------------------------------------------------------- ###
# --- Consultation Routes ---
@app.route('/my_consultations')
@login_required
def my_consultations():
    """Display a list of all consultations submitted by the current user."""
    # Query consultations for the logged-in user, newest first
    consultations = Consultation.query.filter_by(user_id=current_user.id).order_by(Consultation.timestamp.desc()).all()
    doctors = db.session.query(User).join(Doctor).filter(User.role == 'doctor').all()
    return render_template('my_consultations.html', consultations=consultations, doctors=doctors)

@app.route('/contact' , methods=['GET', 'POST'])
def contact():
    return render_template('contact.html')

@app.route('/consultation_details/<int:consultation_id>')
@login_required
def consultation_details(consultation_id):
    """Display the full details of a specific consultation."""
    doctors = db.session.query(User).join(Doctor).filter(User.role == 'doctor').all()
    consultation = Consultation.query.get_or_404(consultation_id)
    # Security check: ensure the user owns this consultation
    if consultation.user_id != current_user.id:
        from flask import abort
        abort(403) # Forbidden
    return render_template('consultation_details.html', consultation=consultation, doctors=doctors)

def format_consultation_data(consultation_id):
    new_consultation = Consultation.query.get_or_404(consultation_id)
    
    # Format the consultation data for display
    consultation_text = f"""
    Consultation (ID: {new_consultation.id})   , 
    --- 1. Personal Information and Main Complaint ---
    - Full Name: {new_consultation.full_name}
    - Age: {new_consultation.age}
    - Gender: {new_consultation.gender}
    - Main Complaint: {new_consultation.main_complaint}

    --- 2. Current Symptoms Details ---
    - Onset: {new_consultation.onset}
    - Location: {new_consultation.location}
    - Character: {new_consultation.character}
    - Duration: {new_consultation.duration}
    - Aggravating Factors: {new_consultation.aggravating_factors}
    - Alleviating Factors: {new_consultation.alleviating_factors}
    - Related Symptoms: {new_consultation.related_symptoms}
    - Severity (1-10): {new_consultation.severity}

    --- 3. Medical History ---
    - Chronic Diseases: {new_consultation.chronic_diseases}
    - Current Medications: {new_consultation.current_medications}
    - Allergies: {new_consultation.allergies}
    - Previous Surgeries: {new_consultation.previous_surgeries}

    --- 4. Lifestyle ---
    - Smoking Status: {new_consultation.smoking_status}

    --- End of Report ---
    """
    return consultation_text

# Dynamic routes for AJAX requests
@app.route('/chatmessage/<int:conversation_id>')
@login_required
def get_partial_messages(conversation_id):
    messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.timestamp).all()
    
    convo = Conversation.query.filter_by(id=conversation_id).first_or_404()
    
    
    return render_template('message_list.html', messages=messages, conversation=convo)

@app.route("/online-status")
@login_required
def online_status():
    doctors = User.query.filter_by(role="doctor").all()
    return jsonify(doctors=[{
        "id": doc.id,
        "is_online": doc.is_online
    } for doc in doctors])

if __name__ == "__main__":
    # Ensure the instance folder exists
    with app.app_context():  # Needed for DB operations
        db.create_all()      # Creates the database and tables
    server = Server(app.wsgi_app)
    server.watch("**/*.py")  # Watch Python files for changes
    server.watch("templates/*.html")
    server.watch("static/*.*")
    server.serve(host="0.0.0.0", port=5000, debug=True) 
