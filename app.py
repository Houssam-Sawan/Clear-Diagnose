from flask import Flask, jsonify
from livereload import Server
import mysql.connector
import os

app = Flask(__name__)

# Database configuration
db_config = {
    "host": os.getenv("DB_HOST", "mariadb"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "rootpassword"),
    "database": os.getenv("DB_DATABASE", "cddb"),
}

@app.route("/")
def home():
    return "This is the home  hgpage reloaded!"

@app.route("/testdb")
def testdb():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT 'Connected to MariaDB!'")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return jsonify({"message": result[0]})
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)})

if __name__ == "__main__":
    server = Server(app.wsgi_app)
    server.watch("**/*.py")  # Watch Python files for changes
    server.watch("templates/*.html")
    server.serve(host="0.0.0.0", port=5000, debug=True) 
