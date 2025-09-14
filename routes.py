from quart import Blueprint, request, jsonify, g, Response
import datetime
import jwt
import json
from auth import jwt_required
from config import config
import services as srv

# Create blueprints for different parts of the API
api = Blueprint('api', __name__, url_prefix='/api/v2')

def serialize_contacts(contacts):
    """Helper to convert ObjectId to string for a list of contacts."""
    for contact in contacts:
        if '_id' in contact:
            contact['_id'] = str(contact['_id'])
    return contacts

@api.route('/')
async def index():
    return jsonify({"message": "Welcome to the Contacts API!"})

# --- Auth Routes ---
@api.route('/signup', methods=['POST'])
async def api_register():
    try:
        data = await request.get_json()
        image, name, username, password, mobile = data.get('image'), data.get('name'), data.get('username'), data.get('password'), data.get('mobile')

        if not all([name, username, password]):
            return jsonify({"error": "Missing required fields"}), 400
        if await srv.check_user_async(username):
            return jsonify({"error": "Username already exists."}), 409

        success, message = await srv.create_user_async(image, name, username, password, mobile)
        return (jsonify({"success": True, "message": message}), 201) if success else (jsonify({"success": False, "error": message}), 500)
    except Exception as e:
        return jsonify({"success": False, "error": f"An internal server error occurred: {e}"}), 500

@api.route('/signin', methods=['POST'])
async def api_login():
    try:
        data = await request.get_json()
        username, password = data.get('username'), data.get('password')
        if not all([username, password]):
            return jsonify({"error": "Missing required fields"}), 400

        if await srv.validate_user_async(username, password):
            payload = {'username': username, 'exp': datetime.datetime.now(datetime.timezone.utc) + config.JWT_EXPIRATION_DELTA}
            token = jwt.encode(payload, config.JWT_SECRET_KEY, algorithm='HS256')
            return jsonify({"success": True, "message": "Login successful", "token": token}), 200
        else:
            return jsonify({"success": False, "error": "Invalid username or password"}), 401
    except Exception as e:
        return jsonify({"success": False, "error": f"An internal server error occurred: {e}"}), 500

@api.route('/check_username', methods=['POST'])
async def api_check_username():
    try:
        data = await request.get_json()
        username = data.get('username')
        if not username:
            return jsonify({"error": "Missing 'username' field"}), 400
        exists = await srv.check_user_async(username)
        return jsonify({"exists": exists, "message": "Username already taken" if exists else "Username is available"}), 200
    except Exception as e:
        return jsonify({"error": f"An internal server error occurred: {e}"}), 500

@api.route('/logout', methods=['POST'])
@jwt_required
async def api_logout():
    return jsonify({"success": True, "message": "Logged out successfully"}), 200

# --- User Routes ---
@api.route('/user', methods=['GET'])
@jwt_required
async def api_get_user_profile():
    user = await srv.get_user_profile_async(g.username)
    if user:
        user_info = {"photo": user.get("Photo"), "name": user.get("Name"), "username": user.get("Username"), "mobile": user.get("Contact")}
        return jsonify({"success": True, "user": user_info}), 200
    return jsonify({"error": "User not found"}), 404

@api.route('/user/update', methods=['PUT'])
@jwt_required
async def api_update_user_profile():
    data = await request.get_json()
    image, name, mobile = data.get('image'), data.get('name'), data.get('mobile')
    if not name:
        return jsonify({"error": "Name is a required field."}), 400

    success, message = await srv.update_user_async(g.username, image, name, mobile)
    if success:
        user = await srv.get_user_profile_async(g.username)
        user_info = {"photo": user.get("Photo"), "name": user.get("Name"), "username": user.get("Username"), "mobile": user.get("Contact")}
        return jsonify({"success": True, "message": message, "user": user_info}), 200
    return jsonify({"error": message}), 404

# --- Contact Routes ---
@api.route('/contacts', methods=['GET'])
@jwt_required
async def api_contacts():
    contacts_list = await srv.get_contacts_async(g.username)
    return jsonify({"success": True, "contacts": serialize_contacts(contacts_list)}), 200

@api.route('/create_contact', methods=['POST'])
@jwt_required
async def api_create_contact():
    data = await request.get_json()
    if not data or not data.get('name') or not data.get('mobile'):
        return jsonify({"error": "Name and mobile are required"}), 400
    
    success, message, new_contact = await srv.add_contact_async(
        g.username, data.get('image'), data.get('name'), data.get('mobile'),
        data.get('email'), data.get('job_title'), data.get('company'),
        data.get('labels', []), datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    if success:
        return jsonify({"success": True, "message": message}), 201
    return jsonify({"error": message}), 500

@api.route('/edit_contact/<contact_id>', methods=['GET', 'PUT'])
@jwt_required
async def api_edit_contact(contact_id):
    if request.method == 'GET':
        contact = await srv.get_contact_by_id_async(g.username, contact_id)
        if contact:
            contact['_id'] = str(contact['_id'])
            return jsonify({"success": True, "contact": contact}), 200
        return jsonify({"error": "Contact not found"}), 404

    if request.method == 'PUT':
        data = await request.get_json()
        new_name = f"{data.get('fname', '')} {data.get('lname', '')}".strip()
        if not new_name or not data.get('mobile'):
            return jsonify({"error": "Name and Mobile are required fields."}), 400
        
        success, message = await srv.update_contact_async(
            g.username, contact_id, new_name, data.get('mobile'), data.get('email'),
            data.get('job_title'), data.get('company'), data.get('labels')
        )
        return (jsonify({"success": True, "message": message}), 200) if success else (jsonify({"error": message}), 404)

@api.route('/contact/<contact_id>', methods=['GET'])
@jwt_required
async def api_get_contact(contact_id):
    contact = await srv.get_contact_by_id_async(g.username, contact_id)
    if contact:
        contact['_id'] = str(contact['_id'])
        return jsonify({"success": True, "contact": contact}), 200
    return jsonify({"error": "Contact not found"}), 404

@api.route('/merge_contacts', methods=['POST'])
@jwt_required
async def api_merge_contacts():
    data = await request.get_json()
    contact_ids = data.get('contact_ids')
    success, message, merged_contact = await srv.merge_contacts_async(g.username, contact_ids)
    if success:
        return jsonify({"success": True, "message": message, "contact": merged_contact}), 201
    return jsonify({"success": False, "error": message}), 400

@api.route('/remove_contact/<contact_id>', methods=['DELETE'])
@jwt_required
async def api_remove_contact(contact_id):
    success, message = await srv.move_to_trash_async(g.username, contact_id)
    return (jsonify({"success": True, "message": message}), 200) if success else (jsonify({"error": message}), 404)

@api.route('/contacts/search', methods=['GET'])
@jwt_required
async def api_search_contacts():
    query = request.args.get('query', '')
    if not query:
        return jsonify({"error": "Missing search query parameter 'query'"}), 400
    results = await srv.search_contacts_async(g.username, query)
    return jsonify({"success": True, "contacts": serialize_contacts(results)}), 200

@api.route('/contacts/export', methods=['GET'])
@jwt_required
async def api_export_contacts():
    contacts = await srv.get_contacts_async(g.username)
    json_content = json.dumps(serialize_contacts(contacts), indent=2)
    return Response(
        json_content, mimetype='application/json',
        headers={'Content-Disposition': 'attachment;filename=contacts.json'}
    )

# --- Trash Routes ---
@api.route('/trash', methods=['GET'])
@jwt_required
async def api_get_trashed_contacts():
    trashed_docs = await srv.get_trashed_contacts_async(g.username)
    return jsonify({"success": True, "trashed_contacts": trashed_docs}), 200

@api.route('/restore_contact/<contact_id>', methods=['POST'])
@jwt_required
async def api_restore_contact(contact_id):
    success, message = await srv.restore_contact_async(g.username, contact_id)
    return (jsonify({"success": True, "message": message}), 200) if success else (jsonify({"error": message}), 404)

@api.route('/delete_permanently/<contact_id>', methods=['DELETE'])
@jwt_required
async def api_delete_permanently(contact_id):
    success, message = await srv.delete_permanently_async(g.username, contact_id)
    return (jsonify({"success": True, "message": message}), 200) if success else (jsonify({"error": message}), 404)

@api.route('/empty_trash', methods=['DELETE'])
@jwt_required
async def api_empty_trash():
    success, message = await srv.empty_trash_async(g.username)
    return (jsonify({"success": True, "message": message}), 200) if success else (jsonify({"error": message}), 404)

# --- Label Routes ---
@api.route('/create_label', methods=['POST'])
@jwt_required
async def api_create_label():
    data = await request.get_json()
    label_name = data.get('label_name')
    if not label_name:
        return jsonify({"error": "Missing 'label_name' field"}), 400
    if await srv.check_the_label_exists_async(g.username, label_name):
        return jsonify({"error": "Label already exists"}), 409
    
    success, message = await srv.create_label_async(g.username, label_name)
    return (jsonify({"success": True, "message": message}), 201) if success else (jsonify({"error": message}), 400)

@api.route('/get_labels', methods=['GET'])
@jwt_required
async def api_get_labels():
    labels = await srv.get_labels_async(g.username)
    return jsonify({"success": True, "labels": labels}), 200

@api.route('/delete_label', methods=['DELETE'])
@jwt_required
async def api_delete_label():
    data = await request.get_json()
    label_name = data.get('label_name')
    if not label_name:
        return jsonify({"error": "Missing 'label_name' field"}), 400
    success, message = await srv.delete_label_async(g.username, label_name)
    return (jsonify({"success": True, "message": message}), 200) if success else (jsonify({"error": message}), 404)

@api.route('/edit_label', methods=['PUT'])
@jwt_required
async def api_edit_label():
    data = await request.get_json()
    old_label, new_label = data.get('old_label_name'), data.get('new_label_name')
    if not old_label or not new_label:
        return jsonify({"error": "Missing 'old_label_name' or 'new_label_name' field"}), 400
    if not await srv.check_the_label_exists_async(g.username, old_label):
        return jsonify({"error": "Label not found"}), 404
    
    success, message = await srv.edit_the_label_async(g.username, old_label, new_label)
    return (jsonify({"success": True, "message": message}), 200) if success else (jsonify({"error": message}), 400)
