from flask import Flask, jsonify, render_template,  url_for, request

from livereload import Server
from config import Config
from models import *  # Import All models here
import os

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login")
def login():
    return render_template("loginandsinup.html")

@app.route("/testdb")
def testdb():
    try:
        db.create_all()  # Ensure the database and tables are created
        return jsonify({"message": "Database connection successful!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Ensure the instance folder exists
    with app.app_context():  # Needed for DB operations
        db.create_all()      # Creates the database and tables
    server = Server(app.wsgi_app)
    server.watch("**/*.py")  # Watch Python files for changes
    server.watch("templates/*.html")
    server.watch("static/*.*")
    server.serve(host="0.0.0.0", port=5000, debug=True) 
