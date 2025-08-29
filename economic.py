"""
Route per l'analisi economica completa
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

from ..models.project import Project
from ..utils.economic_calculator import EconomicCalculator, EconomicParameters

economic_bp = Blueprint('economic', __name__)
logger = logging.getLogger(__name__)

@economic_bp.route('/projects/<int:project_id>/calculate-economics', methods=['POST'])
def calculate_project_economics(project_id):
    """Calcola l'analisi economica completa per un progetto"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Verifica che il progetto abbia i dati necessari
        if not project.geometry_data or not project.pvgis_data:
            return jsonify({
                'success': False,
                'error': 'Il progetto deve avere dati geometrici e PVGIS per l\'analisi economica'
            }), 400
        
        # Parametri economici dalla request
        data = request.get_json() or {}
        
        # Crea parametri economici personalizzati
        economic_params = EconomicParameters(
            # Prezzi energia
            electricity_price_f1=data.get('electricity_price_f1', 0.28),
            electricity_price_f2=data.get('electricity_price_f2', 0.25),
            electricity_price_f3=data.get('electricity_price_f3', 0.22),
            feed_in_tariff=data.get('feed_in_tariff', 0.05),
            
            # Costi impianto
            pv_capex_per_kwp=data.get('pv_capex_per_kwp', 1200),
            pv_opex_annual_percent=data.get('pv_opex_annual_percent', 0.015),
            bess_capex_per_kwh=data.get('bess_capex_per_kwh', 500),
            bess_opex_annual_percent=data.get('bess_opex_annual_percent', 0.01),
            
            # Parametri finanziari
            wacc=data.get('wacc', 0.05),
            analysis_years=data.get('analysis_years', 20),
            
            # Escalation
            electricity_price_escalation=data.get('electricity_price_escalation', 0.02),
            opex_escalation=data.get('opex_escalation', 0.02),
            
            # Incentivi
            tax_deduction_percent=data.get('tax_deduction_percent', 0.0),
            green_certificates=data.get('green_certificates', 0.0)
        )
        
        # Estrai dati dal progetto
        geometry_data = project.geometry_data
        pvgis_data = project.pvgis_data
        bess_data = project.bess_data if hasattr(project, 'bess_data') and project.bess_data else None
        
        # Dati di consumo (se disponibili, altrimenti stima)
        consumption_annual = data.get('consumption_annual_kwh', 200000)  # Default 200 MWh
        consumption_monthly = data.get('consumption_monthly_kwh', [consumption_annual / 12] * 12)
        
        # Parametri FV
        if geometry_data.get('layout_ottimale'):
            pv_power_kwp = geometry_data['layout_ottimale']['potenza_installabile_kwp']
        else:
            pv_power_kwp = geometry_data.get('potenza_installabile_kwp', 0)
        
        pv_production_annual = pvgis_data.get('produzione_annuale_kwh', 0)
        pv_production_monthly = pvgis_data.get('produzione_mensile_kwh', [0] * 12)
        
        # Parametri BESS (se disponibili)
        bess_capacity_kwh = None
        bess_self_consumption_increase = None
        
        if bess_data:
            bess_capacity_kwh = bess_data.get('optimal_capacity_kwh')
            bess_self_consumption_increase = bess_data.get('annual_self_consumption_increase')
        
        # Calcola analisi economica
        calculator = EconomicCalculator()
        results = calculator.calculate_complete_economic_analysis(
            pv_power_kwp=pv_power_kwp,
            pv_production_annual=pv_production_annual,
            pv_production_monthly=pv_production_monthly,
            consumption_annual=consumption_annual,
            consumption_monthly=consumption_monthly,
            bess_capacity_kwh=bess_capacity_kwh,
            bess_self_consumption_increase=bess_self_consumption_increase,
            economic_params=economic_params
        )
        
        # Salva risultati nel progetto
        project.economic_data = {
            'calculation_date': datetime.now().isoformat(),
            'economic_parameters': {
                'wacc': economic_params.wacc,
                'electricity_price_f1': economic_params.electricity_price_f1,
                'electricity_price_f2': economic_params.electricity_price_f2,
                'electricity_price_f3': economic_params.electricity_price_f3,
                'feed_in_tariff': economic_params.feed_in_tariff,
                'pv_capex_per_kwp': economic_params.pv_capex_per_kwp,
                'bess_capex_per_kwh': economic_params.bess_capex_per_kwh,
                'analysis_years': economic_params.analysis_years
            },
            'pv_only_results': {
                'npv': results.pv_only_npv,
                'irr': results.pv_only_irr,
                'payback': results.pv_only_payback,
                'capex': results.pv_only_capex,
                'annual_savings': results.pv_only_annual_savings
            },
            'pv_bess_results': {
                'npv': results.pv_bess_npv,
                'irr': results.pv_bess_irr,
                'payback': results.pv_bess_payback,
                'capex': results.pv_bess_capex,
                'annual_savings': results.pv_bess_annual_savings
            },
            'bess_incremental': {
                'npv': results.bess_incremental_npv,
                'irr': results.bess_incremental_irr,
                'payback': results.bess_incremental_payback
            },
            'kpi_summary': {
                'total_investment': results.total_investment,
                'total_annual_production': results.total_annual_production,
                'total_annual_savings': results.total_annual_savings,
                'lcoe': results.lcoe
            },
            'sensitivity_analysis': results.sensitivity_analysis,
            'consumption_data': {
                'annual_kwh': consumption_annual,
                'monthly_kwh': consumption_monthly
            }
        }
        
        project.save()
        
        return jsonify({
            'success': True,
            'message': 'Analisi economica completata',
            'results': {
                'pv_only': {
                    'npv': results.pv_only_npv,
                    'irr': results.pv_only_irr,
                    'payback': results.pv_only_payback,
                    'capex': results.pv_only_capex,
                    'annual_savings': results.pv_only_annual_savings
                },
                'pv_bess': {
                    'npv': results.pv_bess_npv,
                    'irr': results.pv_bess_irr,
                    'payback': results.pv_bess_payback,
                    'capex': results.pv_bess_capex,
                    'annual_savings': results.pv_bess_annual_savings
                },
                'bess_incremental': {
                    'npv': results.bess_incremental_npv,
                    'irr': results.bess_incremental_irr,
                    'payback': results.bess_incremental_payback
                },
                'kpi_summary': {
                    'total_investment': results.total_investment,
                    'total_annual_production': results.total_annual_production,
                    'total_annual_savings': results.total_annual_savings,
                    'lcoe': results.lcoe
                },
                'sensitivity_analysis': results.sensitivity_analysis,
                'economic_parameters': {
                    'wacc': economic_params.wacc,
                    'wacc_explanation': 'WACC (Weighted Average Cost of Capital) - Costo medio ponderato del capitale, rappresenta il tasso di sconto utilizzato per attualizzare i flussi di cassa futuri',
                    'electricity_prices': {
                        'f1_peak': economic_params.electricity_price_f1,
                        'f2_intermediate': economic_params.electricity_price_f2,
                        'f3_base': economic_params.electricity_price_f3
                    },
                    'capex_costs': {
                        'pv_per_kwp': economic_params.pv_capex_per_kwp,
                        'bess_per_kwh': economic_params.bess_capex_per_kwh
                    }
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Errore calcolo analisi economica: {e}")
        return jsonify({
            'success': False,
            'error': f'Errore durante il calcolo: {str(e)}'
        }), 500

@economic_bp.route('/economic/parameters/defaults', methods=['GET'])
def get_default_economic_parameters():
    """Restituisce i parametri economici di default"""
    try:
        defaults = EconomicParameters()
        
        return jsonify({
            'success': True,
            'parameters': {
                'electricity_prices': {
                    'f1_peak': defaults.electricity_price_f1,
                    'f2_intermediate': defaults.electricity_price_f2,
                    'f3_base': defaults.electricity_price_f3,
                    'feed_in_tariff': defaults.feed_in_tariff
                },
                'capex_costs': {
                    'pv_per_kwp': defaults.pv_capex_per_kwp,
                    'pv_opex_percent': defaults.pv_opex_annual_percent,
                    'bess_per_kwh': defaults.bess_capex_per_kwh,
                    'bess_opex_percent': defaults.bess_opex_annual_percent
                },
                'financial': {
                    'wacc': defaults.wacc,
                    'wacc_explanation': 'WACC (Weighted Average Cost of Capital) - Costo medio ponderato del capitale. Rappresenta il tasso di rendimento minimo richiesto dagli investitori e viene utilizzato come tasso di sconto per attualizzare i flussi di cassa futuri del progetto.',
                    'analysis_years': defaults.analysis_years
                },
                'escalation': {
                    'electricity_price_escalation': defaults.electricity_price_escalation,
                    'opex_escalation': defaults.opex_escalation
                },
                'incentives': {
                    'tax_deduction_percent': defaults.tax_deduction_percent,
                    'green_certificates': defaults.green_certificates
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Errore recupero parametri default: {e}")
        return jsonify({
            'success': False,
            'error': f'Errore: {str(e)}'
        }), 500

@economic_bp.route('/economic/wacc/explanation', methods=['GET'])
def get_wacc_explanation():
    """Restituisce spiegazione dettagliata del WACC"""
    return jsonify({
        'success': True,
        'wacc_explanation': {
            'acronym': 'WACC - Weighted Average Cost of Capital',
            'definition': 'Costo medio ponderato del capitale',
            'description': 'Il WACC rappresenta il tasso di rendimento minimo che un\'azienda deve ottenere sui suoi investimenti per soddisfare tutti i suoi finanziatori (azionisti e creditori).',
            'usage': 'Viene utilizzato come tasso di sconto per attualizzare i flussi di cassa futuri e calcolare il NPV (Net Present Value) del progetto.',
            'typical_ranges': {
                'low_risk': '3-5% (progetti a basso rischio, aziende solide)',
                'medium_risk': '5-8% (progetti standard, aziende medie)',
                'high_risk': '8-12% (progetti ad alto rischio, startup)'
            },
            'factors': [
                'Costo del debito (interessi sui prestiti)',
                'Costo del capitale proprio (rendimento richiesto dagli azionisti)',
                'Struttura finanziaria (rapporto debito/capitale)',
                'Rischio del progetto e del settore',
                'Condizioni di mercato'
            ],
            'impact': 'Un WACC più alto riduce il NPV del progetto, mentre un WACC più basso lo aumenta. È quindi cruciale utilizzare un valore realistico per il tipo di investimento.'
        }
    })

