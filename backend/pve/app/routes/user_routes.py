# app/routes/user_routes.py
from flask import Blueprint, request, jsonify, current_app
from ..utils.token_utils import verify_user_token, token_required
from ..models.user_model import User
from ..utils.logger import log_request

user_bp = Blueprint('user_bp', __name__)

@user_bp.route('/api/get-user-info', methods=['POST'])
@log_request
@token_required
def get_user_info():
    try:
        request_data = request.get_json()
        user_id = request_data.get('id')

        user = User.get_user_by_id(user_id)
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        user_info = user.to_dict()
        return jsonify({'status': 'success', 'user_info': user_info})
    except Exception as e:
        current_app.logger.error(f"Error fetching user info: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@user_bp.route('/api/update-user', methods=['POST'])
@log_request
@token_required
def update_user():
    try:
        request_data = request.get_json()
        user_id = request_data.get('id')

        user = User.get_user_by_id(user_id)
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404

        user.update(request_data)
        return jsonify({'status': 'success', 'message': 'User data updated successfully'})
    except Exception as e:
        current_app.logger.error(f"Error updating user data: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
