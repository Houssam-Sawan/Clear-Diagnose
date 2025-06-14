from mainfun import app
from mainfun import db
from data_users import Disease
from flask import request, jsonify

@app.route('/diseases/<int:disease_id>', methods=['GET'])
def get_disease(disease_id):
    disease = Disease.query.get(disease_id)
    if disease:
        return jsonify({"id": disease.id, "name": disease.name, "description": disease.description})
    return jsonify({"error": "Disease not found"}), 404

@app.route('/diseases', methods=['POST'])
def create_disease():
    data = request.json
    disease = Disease(name=data['name'], description=data['description'])
    db.session.add(disease)
    db.session.commit()
    return jsonify({"message": "Disease created", "id": disease.id}), 201
