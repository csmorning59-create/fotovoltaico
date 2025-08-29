from flask import Blueprint, request, jsonify, session
from src.models.user import db, User
from src.models.project import Project
from src.routes.auth import require_auth
from src.utils.geometry_calculator import GeometryCalculator
import traceback

geometry_bp = Blueprint('geometry', __name__)

@geometry_bp.route('/projects/<int:project_id>/calculate-geometry', methods=['POST'])
@require_auth
def calculate_project_geometry(project_id):
    """Calcola il layout geometrico per un progetto specifico"""
    try:
        user = User.query.get(session['user_id'])
        project = Project.query.get_or_404(project_id)
        
        # Verifica permessi
        if not user.is_admin() and project.owner_id != user.id:
            return jsonify({'error': 'Accesso negato'}), 403
        
        data = request.get_json()
        
        # Parametri richiesti
        superficie_mq = data.get('superficie_mq') or project.superficie_lorda_mq
        tilt_degrees = data.get('tilt_degrees') or project.tilt_degrees
        margine_metri = data.get('margine_metri') or project.margine_metri or 1.0
        orientation_type = data.get('orientation_type') or project.orientation_type or 'optimal'
        
        # Parametri modulo (opzionali)
        modulo_params = None
        if data.get('modulo_params'):
            modulo_params = data['modulo_params']
        elif project.modulo_potenza_wp:
            modulo_params = {
                'potenza_wp': project.modulo_potenza_wp,
                'lunghezza_mm': project.modulo_lunghezza_mm or 2278,
                'larghezza_mm': project.modulo_larghezza_mm or 1134,
                'nome': f'Modulo {project.modulo_potenza_wp}W'
            }
        
        # Validazione parametri
        if not superficie_mq or not tilt_degrees:
            return jsonify({
                'error': 'Parametri mancanti: superficie_mq e tilt_degrees sono richiesti'
            }), 400
        
        calc = GeometryCalculator()
        
        # Validazione input
        validation = calc.validate_parameters(
            float(superficie_mq), 
            float(tilt_degrees), 
            float(margine_metri)
        )
        
        if not validation['valid']:
            return jsonify({
                'error': 'Parametri non validi',
                'validation_errors': validation['errors']
            }), 400
        
        # Calcolo layout in base al tipo richiesto
        if orientation_type == 'sud':
            result = calc.calculate_south_layout(
                float(superficie_mq),
                float(tilt_degrees),
                float(margine_metri),
                modulo_params
            )
        elif orientation_type == 'est_ovest':
            result = calc.calculate_east_west_layout(
                float(superficie_mq),
                float(tilt_degrees),
                float(margine_metri),
                modulo_params
            )
        else:  # 'optimal' o altro
            result = calc.calculate_optimal_layout(
                float(superficie_mq),
                float(tilt_degrees),
                float(margine_metri),
                modulo_params
            )
        
        # Aggiorna il progetto con i risultati se richiesto
        if data.get('save_to_project', False):
            if 'layout_ottimale' in result:
                # Risultato da calcolo ottimale
                layout = result['layout_ottimale']
            else:
                # Risultato da calcolo specifico
                layout = result
            
            project.potenza_installabile_kwp = layout.get('potenza_installabile_kwp')
            project.orientation_type = layout.get('orientamento')
            project.tilt_degrees = tilt_degrees
            project.margine_metri = margine_metri
            
            if modulo_params:
                project.modulo_potenza_wp = modulo_params.get('potenza_wp')
                project.modulo_lunghezza_mm = modulo_params.get('lunghezza_mm')
                project.modulo_larghezza_mm = modulo_params.get('larghezza_mm')
            
            project.last_updated_by = user.id
            db.session.commit()
        
        return jsonify({
            'success': True,
            'project_id': project_id,
            'calculation_result': result,
            'validation': validation,
            'parameters_used': {
                'superficie_mq': float(superficie_mq),
                'tilt_degrees': float(tilt_degrees),
                'margine_metri': float(margine_metri),
                'orientation_type': orientation_type,
                'modulo_params': modulo_params
            }
        }), 200
        
    except Exception as e:
        print(f"Errore calcolo geometria: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Errore interno: {str(e)}'}), 500

@geometry_bp.route('/geometry/calculate', methods=['POST'])
@require_auth
def calculate_geometry_standalone():
    """Calcola il layout geometrico senza associarlo a un progetto"""
    try:
        data = request.get_json()
        
        # Parametri richiesti
        superficie_mq = data.get('superficie_mq')
        tilt_degrees = data.get('tilt_degrees')
        margine_metri = data.get('margine_metri', 1.0)
        orientation_type = data.get('orientation_type', 'optimal')
        modulo_params = data.get('modulo_params')
        
        if not superficie_mq or not tilt_degrees:
            return jsonify({
                'error': 'Parametri mancanti: superficie_mq e tilt_degrees sono richiesti'
            }), 400
        
        calc = GeometryCalculator()
        
        # Validazione input
        validation = calc.validate_parameters(
            float(superficie_mq), 
            float(tilt_degrees), 
            float(margine_metri)
        )
        
        if not validation['valid']:
            return jsonify({
                'error': 'Parametri non validi',
                'validation_errors': validation['errors']
            }), 400
        
        # Calcolo layout
        if orientation_type == 'sud':
            result = calc.calculate_south_layout(
                float(superficie_mq),
                float(tilt_degrees),
                float(margine_metri),
                modulo_params
            )
        elif orientation_type == 'est_ovest':
            result = calc.calculate_east_west_layout(
                float(superficie_mq),
                float(tilt_degrees),
                float(margine_metri),
                modulo_params
            )
        else:  # 'optimal'
            result = calc.calculate_optimal_layout(
                float(superficie_mq),
                float(tilt_degrees),
                float(margine_metri),
                modulo_params
            )
        
        return jsonify({
            'success': True,
            'calculation_result': result,
            'validation': validation,
            'parameters_used': {
                'superficie_mq': float(superficie_mq),
                'tilt_degrees': float(tilt_degrees),
                'margine_metri': float(margine_metri),
                'orientation_type': orientation_type,
                'modulo_params': modulo_params
            }
        }), 200
        
    except Exception as e:
        print(f"Errore calcolo geometria standalone: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Errore interno: {str(e)}'}), 500

@geometry_bp.route('/geometry/modules', methods=['GET'])
@require_auth
def get_module_suggestions():
    """Ottieni lista moduli fotovoltaici suggeriti"""
    try:
        calc = GeometryCalculator()
        modules = calc.get_module_suggestions()
        
        return jsonify({
            'success': True,
            'modules': modules
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Errore interno: {str(e)}'}), 500

@geometry_bp.route('/geometry/validate', methods=['POST'])
@require_auth
def validate_geometry_parameters():
    """Valida i parametri per il calcolo geometrico"""
    try:
        data = request.get_json()
        
        superficie_mq = data.get('superficie_mq')
        tilt_degrees = data.get('tilt_degrees')
        margine_metri = data.get('margine_metri', 1.0)
        
        if not superficie_mq or not tilt_degrees:
            return jsonify({
                'error': 'Parametri mancanti: superficie_mq e tilt_degrees sono richiesti'
            }), 400
        
        calc = GeometryCalculator()
        validation = calc.validate_parameters(
            float(superficie_mq), 
            float(tilt_degrees), 
            float(margine_metri)
        )
        
        return jsonify({
            'success': True,
            'validation': validation
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Errore interno: {str(e)}'}), 500

