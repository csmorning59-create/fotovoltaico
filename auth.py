from flask import Blueprint, request, jsonify, session
from src.models.user import db, User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login utente"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username e password sono richiesti'}), 400
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_active:
            session['user_id'] = user.id
            session['user_role'] = user.role
            return jsonify({
                'message': 'Login effettuato con successo',
                'user': user.to_dict()
            }), 200
        else:
            return jsonify({'error': 'Credenziali non valide'}), 401
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Logout utente"""
    session.clear()
    return jsonify({'message': 'Logout effettuato con successo'}), 200

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """Ottieni informazioni utente corrente"""
    if 'user_id' not in session:
        return jsonify({'error': 'Non autenticato'}), 401
    
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return jsonify({'error': 'Utente non trovato'}), 404
    
    return jsonify({'user': user.to_dict()}), 200

@auth_bp.route('/register', methods=['POST'])
def register():
    """Registrazione nuovo utente (solo per admin)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Non autenticato'}), 401
    
    current_user = User.query.get(session['user_id'])
    if not current_user or not current_user.is_admin():
        return jsonify({'error': 'Accesso negato - solo admin'}), 403
    
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', 'user')
        
        if not username or not email or not password:
            return jsonify({'error': 'Username, email e password sono richiesti'}), 400
        
        if role not in ['admin', 'user']:
            return jsonify({'error': 'Ruolo non valido'}), 400
        
        # Verifica se username o email esistono già
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username già esistente'}), 400
        
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email già esistente'}), 400
        
        # Crea nuovo utente
        new_user = User(username=username, email=email, role=role)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            'message': 'Utente creato con successo',
            'user': new_user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def require_auth(f):
    """Decorator per richiedere autenticazione"""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Non autenticato'}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def require_admin(f):
    """Decorator per richiedere ruolo admin"""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Non autenticato'}), 401
        
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin():
            return jsonify({'error': 'Accesso negato - solo admin'}), 403
        
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

