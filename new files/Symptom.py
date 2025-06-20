from mainfun import Symptom
from data_users import app ,db
from flask import request , jsonify

@app.route('/symptoms/<int:symptom_id>', methods=['GET'])
def get_symptom(symptom_id):
    symptom = Symptom.query.get(symptom_id)
    if symptom:
        return jsonify({"id": symptom.id, "description": symptom.description, "disease_id": symptom.disease_id})
    return jsonify({"error": "Symptom not found"}), 404

@app.route('/symptoms', methods=['POST'])
def create_symptom():
    data = request.json
    symptom = Symptom(description=data['description'], disease_id=data['disease_id'])
    db.session.add(symptom)
    db.session.commit()
    return jsonify({"message": "Symptom created", "id": symptom.id}), 201
