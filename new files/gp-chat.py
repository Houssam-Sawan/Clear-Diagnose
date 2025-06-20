from mainfun import Conversation
from data_users import app ,db
from flask import request , jsonify

@app.route('/conversations/<int:conv_id>', methods=['GET'])
def get_conversation(conv_id):
    convo = Conversation.query.get(conv_id)
    if convo:
        return jsonify({"id": convo.id, "user_id": convo.user_id, "message": convo.message})
    return jsonify({"error": "Conversation not found"}), 404

@app.route('/conversations', methods=['POST'])
def create_conversation():
    data = request.json
    convo = Conversation(user_id=data['user_id'], message=data['message'])
    db.session.add(convo)
    db.session.commit()
    return jsonify({"message": "Conversation saved", "id": convo.id}), 201
