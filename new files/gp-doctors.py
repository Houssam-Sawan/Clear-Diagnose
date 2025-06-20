from mainfun import app
from mainfun import db
from data_users import Doctor
from flask import request, jsonify

@app.route('/doctors/<int:doctor_id>', methods=['GET'])
def get_doctor(doctor_id):
    doctor = Doctor.query.get(doctor_id)
    if doctor:
        return jsonify({"id": doctor.id, "name": doctor.name, "specialty": doctor.specialty})
    return jsonify({"error": "Doctor not found"}), 404

@app.route('/doctors', methods=['POST'])
def create_doctor():
    data = request.json
    doctor = Doctor(name=data['name'], specialty=data['specialty'])
    db.session.add(doctor)
    db.session.commit()
    return jsonify({"message": "Doctor created", "id": doctor.id}), 201
