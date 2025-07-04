from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(50), default='user')
    is_admin = db.Column(db.Boolean, default=False)
    is_online = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    doctor_profile = db.relationship('Doctor', back_populates='user', uselist=False)

    def is_active(self):
        """Return True if the user is active."""
        return True
    def is_authenticated(self):
        """Return True if the user is authenticated."""
        return True
    def is_anonymous(self):
        """Return False, as this user class does not support anonymous users."""
        return False
    def get_id(self):
        """Return the user ID as a string."""
        return str(self.id)

    def set_password(self, password):
        """Set the password hash for the user."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check the provided password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"

class Doctor(db.Model):
    __tablename__ = 'doctors'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    specialty = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    user = db.relationship('User', back_populates='doctor_profile')

    def __repr__(self):
        return f"<Doctor {self.name}>"

class Disease(db.Model):
    __tablename__ = 'diseases'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    def __repr__(self):
        return f"<Disease {self.name}>"

class Symptom(db.Model):
    __tablename__ = 'symptoms'

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    disease_id = db.Column(db.Integer, db.ForeignKey('diseases.id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    disease = db.relationship('Disease', backref=db.backref('symptoms', lazy=True))

    def __repr__(self):
        return f"<Symptom {self.description}>"

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(50), default='User')  # 'User' or 'Doctor'
    subject = db.Column(db.String(255), nullable=False)
    messages = db.relationship('Message', backref='conversation',cascade="all, delete-orphan", lazy=True, order_by="Message.timestamp")
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)  
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='active')  # 'active', 'closed', 'pending'


    user = db.relationship('User', backref='conversations')

    def __repr__(self):
        return f"<Conversation {self.id} by User {self.user_id}>"


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(50), default='User')  # 'User' or 'Doctor' or 'Assistant'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User')


class Consultation(db.Model):
    __tablename__ = 'consultations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    
    # --- Personal Information ---
    full_name = db.Column(db.String(150), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(50))
    main_complaint = db.Column(db.Text, nullable=False)
    
    # --- Symptoms Details ---
    onset = db.Column(db.Text)
    location = db.Column(db.Text)
    character = db.Column(db.Text)
    duration = db.Column(db.Text)
    aggravating_factors = db.Column(db.Text)
    alleviating_factors = db.Column(db.Text)
    related_symptoms = db.Column(db.Text)
    severity = db.Column(db.Integer)
    
    # --- Medical History ---
    chronic_diseases = db.Column(db.Text)
    current_medications = db.Column(db.Text)
    allergies = db.Column(db.Text)
    previous_surgeries = db.Column(db.Text)
    
    # --- Lifestyle ---
    smoking_status = db.Column(db.String(100))
    
    # --- Relationship to User ---
    user = db.relationship('User', backref=db.backref('consultations', lazy=True))
    doctor = db.relationship('Doctor', backref=db.backref('consultations', lazy=True))

    def __repr__(self):
        return f'<Consultation {self.id} by User {self.user_id}>'