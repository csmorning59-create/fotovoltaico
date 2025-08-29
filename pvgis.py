"""
Route API per l'integrazione con PVGIS
Gestisce le chiamate per ottenere dati di produzione fotovoltaica
"""

from flask import Blueprint, request, jsonify, session
from src.models.user import User, db
from src.models.project import Project
from src.utils.pvgis_client import PVGISClient
import logging

pvgis_bp = Blueprint('pvgis', __name__)

@pvgis_bp.route('/pvgis/production', methods=['POST'])
def calculate_production():
    """
    Calcola la produzione fotovoltaica usando PVGIS
    """
    try:
        # Verifica autenticazione
        if 'user_id' not in session:
            return jsonify({'error': 'Non autenticato'}), 401
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'Utente non trovato'}), 404
        
        # Ottiene i parametri dalla richiesta
        data = request.get_json()
        
        required_fields = ['latitude', 'longitude', 'peak_power_kwp', 'tilt', 'azimuth']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo obbligatorio mancante: {field}'}), 400
        
        # Valida i parametri
        try:
            latitude = float(data['latitude'])
            longitude = float(data['longitude'])
            peak_power_kwp = float(data['peak_power_kwp'])
            tilt = float(data['tilt'])
            azimuth = float(data['azimuth'])
        except (ValueError, TypeError):
            return jsonify({'error': 'Parametri numerici non validi'}), 400
        
        # Parametri opzionali
        mounting_type = data.get('mounting_type', 'free')
        pvtech = data.get('pvtech', 'crystSi')
        loss = float(data.get('loss', 14.0))
        
        # Valida i range
        if not (-90 <= latitude <= 90):
            return jsonify({'error': 'Latitudine deve essere tra -90 e 90'}), 400
        if not (-180 <= longitude <= 180):
            return jsonify({'error': 'Longitudine deve essere tra -180 e 180'}), 400
        if not (0 <= tilt <= 90):
            return jsonify({'error': 'Inclinazione deve essere tra 0 e 90 gradi'}), 400
        if not (-180 <= azimuth <= 180):
            return jsonify({'error': 'Azimuth deve essere tra -180 e 180 gradi'}), 400
        if peak_power_kwp <= 0:
            return jsonify({'error': 'Potenza deve essere maggiore di 0'}), 400
        
        # Inizializza client PVGIS
        client = PVGISClient()
        
        # Calcola la produzione
        result = client.get_pv_production(
            latitude=latitude,
            longitude=longitude,
            peak_power_kwp=peak_power_kwp,
            tilt=tilt,
            azimuth=azimuth,
            mounting_type=mounting_type,
            pvtech=pvtech,
            loss=loss
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Errore sconosciuto PVGIS')
            }), 500
            
    except Exception as e:
        logging.error(f"Errore calcolo produzione PVGIS: {e}")
        return jsonify({'error': f'Errore interno: {str(e)}'}), 500

@pvgis_bp.route('/pvgis/production-dual', methods=['POST'])
def calculate_dual_production():
    """
    Calcola la produzione fotovoltaica per sistema Est-Ovest usando PVGIS
    """
    try:
        # Verifica autenticazione
        if 'user_id' not in session:
            return jsonify({'error': 'Non autenticato'}), 401
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'Utente non trovato'}), 404
        
        # Ottiene i parametri dalla richiesta
        data = request.get_json()
        
        required_fields = ['latitude', 'longitude', 'peak_power_kwp', 'tilt']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo obbligatorio mancante: {field}'}), 400
        
        # Valida i parametri
        try:
            latitude = float(data['latitude'])
            longitude = float(data['longitude'])
            peak_power_kwp = float(data['peak_power_kwp'])
            tilt = float(data['tilt'])
        except (ValueError, TypeError):
            return jsonify({'error': 'Parametri numerici non validi'}), 400
        
        # Parametri opzionali
        azimuth_east = float(data.get('azimuth_east', 90))
        azimuth_west = float(data.get('azimuth_west', -90))
        split_ratio = float(data.get('split_ratio', 0.5))
        
        # Valida i range
        if not (-90 <= latitude <= 90):
            return jsonify({'error': 'Latitudine deve essere tra -90 e 90'}), 400
        if not (-180 <= longitude <= 180):
            return jsonify({'error': 'Longitudine deve essere tra -180 e 180'}), 400
        if not (0 <= tilt <= 90):
            return jsonify({'error': 'Inclinazione deve essere tra 0 e 90 gradi'}), 400
        if peak_power_kwp <= 0:
            return jsonify({'error': 'Potenza deve essere maggiore di 0'}), 400
        if not (0 < split_ratio < 1):
            return jsonify({'error': 'Split ratio deve essere tra 0 e 1'}), 400
        
        # Inizializza client PVGIS
        client = PVGISClient()
        
        # Calcola la produzione Est-Ovest
        result = client.get_dual_axis_production(
            latitude=latitude,
            longitude=longitude,
            peak_power_kwp=peak_power_kwp,
            tilt=tilt,
            azimuth_east=azimuth_east,
            azimuth_west=azimuth_west,
            split_ratio=split_ratio
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Errore sconosciuto PVGIS')
            }), 500
            
    except Exception as e:
        logging.error(f"Errore calcolo produzione dual PVGIS: {e}")
        return jsonify({'error': f'Errore interno: {str(e)}'}), 500

@pvgis_bp.route('/projects/<int:project_id>/calculate-pvgis', methods=['POST'])
def calculate_project_pvgis(project_id):
    """
    Calcola e salva i dati PVGIS per un progetto specifico
    """
    try:
        # Verifica autenticazione
        if 'user_id' not in session:
            return jsonify({'error': 'Non autenticato'}), 401
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'Utente non trovato'}), 404
        
        # Trova il progetto
        project = Project.query.get(project_id)
        if not project:
            return jsonify({'error': 'Progetto non trovato'}), 404
        
        # Verifica permessi
        if not user.is_admin() and project.owner_id != user.id:
            return jsonify({'error': 'Accesso negato'}), 403
        
        # Verifica che il progetto abbia i dati geometrici necessari
        if not project.potenza_installabile_kwp:
            return jsonify({'error': 'Progetto deve avere potenza installabile calcolata'}), 400
        
        # Ottiene parametri dalla richiesta o usa valori di default
        data = request.get_json() or {}
        
        # Usa coordinate di default per Milano se non specificate
        # In produzione, queste dovrebbero essere estratte dall'indirizzo del progetto
        latitude = float(data.get('latitude', 45.4642))  # Milano
        longitude = float(data.get('longitude', 9.1900))  # Milano
        
        # Usa parametri del progetto
        peak_power_kwp = float(project.potenza_installabile_kwp)
        tilt = float(project.inclinazione_gradi or 30)
        
        # Determina orientamento
        orientation_type = project.orientation_type or 'sud'
        
        # Inizializza client PVGIS
        client = PVGISClient()
        
        if orientation_type == 'est_ovest':
            # Calcola produzione Est-Ovest
            result = client.get_dual_axis_production(
                latitude=latitude,
                longitude=longitude,
                peak_power_kwp=peak_power_kwp,
                tilt=tilt
            )
        else:
            # Calcola produzione Sud (default)
            azimuth = float(project.azimuth_degrees or 180)  # Sud
            result = client.get_pv_production(
                latitude=latitude,
                longitude=longitude,
                peak_power_kwp=peak_power_kwp,
                tilt=tilt,
                azimuth=azimuth
            )
        
        if result['success']:
            # Salva i risultati nel progetto
            project.produzione_annua_kwh = result['annual_production_kwh']
            
            # Aggiorna timestamp
            from datetime import datetime
            project.updated_at = datetime.utcnow()
            
            # Salva nel database
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Dati PVGIS calcolati e salvati',
                'data': result,
                'project_updated': {
                    'id': project.id,
                    'produzione_annua_kwh': project.produzione_annua_kwh
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Errore calcolo PVGIS')
            }), 500
            
    except Exception as e:
        logging.error(f"Errore calcolo PVGIS progetto {project_id}: {e}")
        return jsonify({'error': f'Errore interno: {str(e)}'}), 500

@pvgis_bp.route('/pvgis/compare-orientations', methods=['POST'])
def compare_orientations():
    """
    Confronta la produzione tra orientamento Sud e Est-Ovest
    """
    try:
        # Verifica autenticazione
        if 'user_id' not in session:
            return jsonify({'error': 'Non autenticato'}), 401
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'Utente non trovato'}), 404
        
        # Ottiene i parametri dalla richiesta
        data = request.get_json()
        
        required_fields = ['latitude', 'longitude', 'peak_power_kwp', 'tilt']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo obbligatorio mancante: {field}'}), 400
        
        # Valida i parametri
        latitude = float(data['latitude'])
        longitude = float(data['longitude'])
        peak_power_kwp = float(data['peak_power_kwp'])
        tilt = float(data['tilt'])
        
        # Inizializza client PVGIS
        client = PVGISClient()
        
        # Calcola produzione Sud
        result_sud = client.get_pv_production(
            latitude=latitude,
            longitude=longitude,
            peak_power_kwp=peak_power_kwp,
            tilt=tilt,
            azimuth=180  # Sud
        )
        
        # Calcola produzione Est-Ovest
        result_eo = client.get_dual_axis_production(
            latitude=latitude,
            longitude=longitude,
            peak_power_kwp=peak_power_kwp,
            tilt=tilt
        )
        
        if result_sud['success'] and result_eo['success']:
            # Calcola confronto
            diff_kwh = result_eo['annual_production_kwh'] - result_sud['annual_production_kwh']
            diff_percent = (diff_kwh / result_sud['annual_production_kwh']) * 100
            
            comparison = {
                'sud': {
                    'annual_production_kwh': result_sud['annual_production_kwh'],
                    'specific_production_kwh_kwp': result_sud['specific_production_kwh_kwp'],
                    'performance_ratio': result_sud['performance_ratio']
                },
                'est_ovest': {
                    'annual_production_kwh': result_eo['annual_production_kwh'],
                    'annual_production_east_kwh': result_eo['annual_production_east_kwh'],
                    'annual_production_west_kwh': result_eo['annual_production_west_kwh'],
                    'specific_production_kwh_kwp': result_eo['specific_production_kwh_kwp']
                },
                'comparison': {
                    'difference_kwh': diff_kwh,
                    'difference_percent': diff_percent,
                    'best_orientation': 'est_ovest' if diff_kwh > 0 else 'sud',
                    'recommendation': 'Est-Ovest produce di più' if diff_kwh > 0 else 'Sud produce di più'
                }
            }
            
            return jsonify({
                'success': True,
                'data': comparison
            }), 200
        else:
            errors = []
            if not result_sud['success']:
                errors.append(f"Errore Sud: {result_sud.get('error')}")
            if not result_eo['success']:
                errors.append(f"Errore Est-Ovest: {result_eo.get('error')}")
            
            return jsonify({
                'success': False,
                'error': '; '.join(errors)
            }), 500
            
    except Exception as e:
        logging.error(f"Errore confronto orientamenti: {e}")
        return jsonify({'error': f'Errore interno: {str(e)}'}), 500

