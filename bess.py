"""
Route API per il modulo BESS (Battery Energy Storage System)
Gestisce i calcoli di dimensionamento e analisi economica delle batterie
"""

from flask import Blueprint, request, jsonify, session
from src.models.user import User, db
from src.models.project import Project
from src.utils.bess_calculator import (
    BESSCalculator, 
    BESSParameters, 
    ConsumptionProfile,
    create_default_consumption_profile,
    estimate_consumption_from_power
)
from datetime import datetime
import logging
import json

bess_bp = Blueprint('bess', __name__)

@bess_bp.route('/bess/calculate', methods=['POST'])
def calculate_bess():
    """
    Calcola il dimensionamento BESS ottimale
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
        
        # Parametri obbligatori
        required_fields = ['pv_production_monthly', 'annual_consumption_kwh']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo obbligatorio mancante: {field}'}), 400
        
        # Validazione dati
        try:
            pv_production_monthly = data['pv_production_monthly']
            if len(pv_production_monthly) != 12:
                return jsonify({'error': 'Produzione mensile deve avere 12 valori'}), 400
            
            annual_consumption_kwh = float(data['annual_consumption_kwh'])
            if annual_consumption_kwh <= 0:
                return jsonify({'error': 'Consumo annuale deve essere positivo'}), 400
                
        except (ValueError, TypeError):
            return jsonify({'error': 'Parametri numerici non validi'}), 400
        
        # Parametri opzionali con valori di default
        electricity_price = float(data.get('electricity_price', 0.25))  # €/kWh
        feed_in_tariff = float(data.get('feed_in_tariff', 0.05))  # €/kWh
        wacc = float(data.get('wacc', 0.05))  # 5%
        
        # Parametri BESS (opzionali)
        bess_params = BESSParameters(
            dod=float(data.get('dod', 0.8)),
            c_rate=float(data.get('c_rate', 0.5)),
            efficiency=float(data.get('efficiency', 0.95)),
            cycle_life=int(data.get('cycle_life', 6000)),
            capex_per_kwh=float(data.get('capex_per_kwh', 500.0)),
            opex_annual_percent=float(data.get('opex_annual_percent', 1.0)),
            degradation_annual=float(data.get('degradation_annual', 0.02))
        )
        
        # Profilo di consumo
        if 'consumption_profile' in data:
            # Profilo personalizzato
            profile_data = data['consumption_profile']
            consumption_profile = ConsumptionProfile(
                monthly_kwh=profile_data.get('monthly_kwh', [annual_consumption_kwh/12]*12),
                f1_percent=float(profile_data.get('f1_percent', 0.33)),
                f2_percent=float(profile_data.get('f2_percent', 0.33)),
                f3_percent=float(profile_data.get('f3_percent', 0.34)),
                granularity=profile_data.get('granularity', 'monthly')
            )
        else:
            # Profilo di default
            consumption_profile = create_default_consumption_profile(annual_consumption_kwh)
        
        # Calcolo BESS
        calculator = BESSCalculator()
        results = calculator.calculate_optimal_bess(
            pv_production_monthly=pv_production_monthly,
            consumption_profile=consumption_profile,
            bess_params=bess_params,
            electricity_price=electricity_price,
            feed_in_tariff=feed_in_tariff,
            wacc=wacc
        )
        
        # Formatta risultati per JSON
        response_data = {
            'success': True,
            'results': {
                # Dimensionamento
                'optimal_capacity_kwh': round(results.optimal_capacity_kwh, 1),
                'optimal_power_kw': round(results.optimal_power_kw, 1),
                
                # Performance energetica
                'annual_self_consumption_increase': round(results.annual_self_consumption_increase, 0),
                'annual_grid_reduction': round(results.annual_grid_reduction, 0),
                
                # Analisi economica
                'capex_total': round(results.capex_total, 0),
                'opex_annual': round(results.opex_annual, 0),
                'savings_annual': round(results.savings_annual, 0),
                'payback_years': round(results.payback_years, 1),
                'npv_20_years': round(results.npv_20_years, 0),
                'irr_percent': round(results.irr_percent, 1),
                
                # Metriche tecniche
                'daily_cycles': round(results.daily_cycles, 2),
                'total_cycles_20_years': round(results.total_cycles_20_years, 0),
                'capacity_retention_20_years': round(results.capacity_retention_20_years * 100, 1),
                
                # Breakdown economico
                'avoided_grid_cost': round(results.avoided_grid_cost, 0),
                'incentives_annual': round(results.incentives_annual, 0),
                'lcoe_reduction': round(results.lcoe_reduction, 2)
            },
            'parameters_used': {
                'bess_params': {
                    'dod': bess_params.dod,
                    'c_rate': bess_params.c_rate,
                    'efficiency': bess_params.efficiency,
                    'cycle_life': bess_params.cycle_life,
                    'capex_per_kwh': bess_params.capex_per_kwh,
                    'opex_annual_percent': bess_params.opex_annual_percent,
                    'degradation_annual': bess_params.degradation_annual
                },
                'economic_params': {
                    'electricity_price': electricity_price,
                    'feed_in_tariff': feed_in_tariff,
                    'wacc': wacc
                }
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logging.error(f"Errore calcolo BESS: {e}")
        return jsonify({'error': f'Errore interno: {str(e)}'}), 500

@bess_bp.route('/projects/<int:project_id>/calculate-bess', methods=['POST'])
def calculate_project_bess(project_id):
    """
    Calcola e salva i dati BESS per un progetto specifico
    """
    try:
        # Verifica autenticazione
        if 'user_id' not in session:
            return jsonify({'error': 'Non autenticato'}), 401
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'Utente non trovato'}), 404
        
        # Verifica progetto
        project = Project.query.get(project_id)
        if not project:
            return jsonify({'error': 'Progetto non trovato'}), 404
        
        # Verifica permessi
        if user.role != 'admin' and project.assigned_to != user.id:
            return jsonify({'error': 'Non autorizzato per questo progetto'}), 403
        
        # Ottiene parametri dalla richiesta
        data = request.get_json()
        
        # Verifica che il progetto abbia dati PVGIS
        if not project.pvgis_data:
            return jsonify({'error': 'Calcola prima la produzione PVGIS per questo progetto'}), 400
        
        # Estrae dati PVGIS dal progetto
        import json
        pvgis_data = json.loads(project.pvgis_data)
        pv_production_monthly = [
            pvgis_data['monthly_data'][i]['pv_production'] 
            for i in range(12)
        ]
        
        # Parametri di consumo
        annual_consumption_kwh = float(data.get('annual_consumption_kwh', 0))
        if annual_consumption_kwh <= 0:
            # Stima da potenza installata se non fornito
            if project.installed_power_kw:
                annual_consumption_kwh = estimate_consumption_from_power(
                    project.installed_power_kw, 
                    load_factor=float(data.get('load_factor', 0.3))
                )
            else:
                return jsonify({'error': 'Fornire consumo annuale o completare il dimensionamento FV'}), 400
        
        # Parametri economici
        electricity_price = float(data.get('electricity_price', 0.25))
        feed_in_tariff = float(data.get('feed_in_tariff', 0.05))
        wacc = float(data.get('wacc', 0.05))
        
        # Parametri BESS
        bess_params = BESSParameters(
            dod=float(data.get('dod', 0.8)),
            c_rate=float(data.get('c_rate', 0.5)),
            efficiency=float(data.get('efficiency', 0.95)),
            cycle_life=int(data.get('cycle_life', 6000)),
            capex_per_kwh=float(data.get('capex_per_kwh', 500.0)),
            opex_annual_percent=float(data.get('opex_annual_percent', 1.0)),
            degradation_annual=float(data.get('degradation_annual', 0.02))
        )
        
        # Profilo di consumo
        consumption_profile = create_default_consumption_profile(annual_consumption_kwh)
        
        # Calcolo BESS
        calculator = BESSCalculator()
        results = calculator.calculate_optimal_bess(
            pv_production_monthly=pv_production_monthly,
            consumption_profile=consumption_profile,
            bess_params=bess_params,
            electricity_price=electricity_price,
            feed_in_tariff=feed_in_tariff,
            wacc=wacc
        )
        
        # Salva risultati nel progetto
        bess_data = {
            'calculation_date': str(datetime.now()),
            'input_parameters': {
                'annual_consumption_kwh': annual_consumption_kwh,
                'electricity_price': electricity_price,
                'feed_in_tariff': feed_in_tariff,
                'wacc': wacc,
                'bess_parameters': {
                    'dod': bess_params.dod,
                    'c_rate': bess_params.c_rate,
                    'efficiency': bess_params.efficiency,
                    'cycle_life': bess_params.cycle_life,
                    'capex_per_kwh': bess_params.capex_per_kwh,
                    'opex_annual_percent': bess_params.opex_annual_percent,
                    'degradation_annual': bess_params.degradation_annual
                }
            },
            'results': {
                'optimal_capacity_kwh': results.optimal_capacity_kwh,
                'optimal_power_kw': results.optimal_power_kw,
                'annual_self_consumption_increase': results.annual_self_consumption_increase,
                'annual_grid_reduction': results.annual_grid_reduction,
                'capex_total': results.capex_total,
                'opex_annual': results.opex_annual,
                'savings_annual': results.savings_annual,
                'payback_years': results.payback_years,
                'npv_20_years': results.npv_20_years,
                'irr_percent': results.irr_percent,
                'daily_cycles': results.daily_cycles,
                'total_cycles_20_years': results.total_cycles_20_years,
                'capacity_retention_20_years': results.capacity_retention_20_years,
                'avoided_grid_cost': results.avoided_grid_cost,
                'incentives_annual': results.incentives_annual,
                'lcoe_reduction': results.lcoe_reduction
            }
        }
        
        project.bess_data = json.dumps(bess_data)
        project.bess_capacity_kwh = results.optimal_capacity_kwh
        project.bess_power_kw = results.optimal_power_kw
        
        # Aggiorna timestamp
        project.updated_at = datetime.now()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Calcolo BESS completato e salvato',
            'results': bess_data['results']
        })
        
    except Exception as e:
        logging.error(f"Errore calcolo BESS progetto {project_id}: {e}")
        return jsonify({'error': f'Errore interno: {str(e)}'}), 500

@bess_bp.route('/bess/compare-scenarios', methods=['POST'])
def compare_bess_scenarios():
    """
    Confronta scenari con diverse configurazioni BESS
    """
    try:
        # Verifica autenticazione
        if 'user_id' not in session:
            return jsonify({'error': 'Non autenticato'}), 401
        
        data = request.get_json()
        
        # Parametri base
        pv_production_monthly = data['pv_production_monthly']
        annual_consumption_kwh = float(data['annual_consumption_kwh'])
        
        # Scenari da confrontare
        scenarios = data.get('scenarios', [
            {'name': 'Conservativo', 'capacity_multiplier': 0.5},
            {'name': 'Ottimale', 'capacity_multiplier': 1.0},
            {'name': 'Aggressivo', 'capacity_multiplier': 1.5}
        ])
        
        calculator = BESSCalculator()
        consumption_profile = create_default_consumption_profile(annual_consumption_kwh)
        
        results = []
        
        for scenario in scenarios:
            # Calcola capacità per questo scenario
            base_params = BESSParameters()
            
            # Calcola capacità ottimale base
            optimal_capacity = calculator._optimize_bess_capacity(
                pv_production_monthly,
                consumption_profile,
                base_params,
                0.25,  # electricity_price
                0.05   # feed_in_tariff
            )
            
            # Applica moltiplicatore scenario
            scenario_capacity = optimal_capacity * scenario['capacity_multiplier']
            
            # Calcola risultati per questo scenario
            scenario_results = calculator.calculate_optimal_bess(
                pv_production_monthly=pv_production_monthly,
                consumption_profile=consumption_profile,
                bess_params=base_params,
                electricity_price=0.25,
                feed_in_tariff=0.05,
                wacc=0.05
            )
            
            # Override della capacità
            scenario_results.optimal_capacity_kwh = scenario_capacity
            scenario_results.optimal_power_kw = scenario_capacity * base_params.c_rate
            
            results.append({
                'scenario_name': scenario['name'],
                'capacity_kwh': round(scenario_capacity, 1),
                'power_kw': round(scenario_capacity * base_params.c_rate, 1),
                'capex_total': round(scenario_capacity * base_params.capex_per_kwh, 0),
                'payback_years': round(scenario_results.payback_years, 1),
                'npv_20_years': round(scenario_results.npv_20_years, 0),
                'irr_percent': round(scenario_results.irr_percent, 1),
                'annual_savings': round(scenario_results.savings_annual, 0)
            })
        
        return jsonify({
            'success': True,
            'scenarios': results
        })
        
    except Exception as e:
        logging.error(f"Errore confronto scenari BESS: {e}")
        return jsonify({'error': f'Errore interno: {str(e)}'}), 500

