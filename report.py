"""
Route API per la generazione di report PDF
"""

import os
import json
from flask import Blueprint, request, jsonify, session, send_file
from src.models.user import db, User
from src.models.project import Project
from src.routes.auth import require_auth
from src.utils.report_generator import ReportGenerator
from datetime import datetime
import tempfile

report_bp = Blueprint('report', __name__)

# Istanza del generatore di report
report_generator = ReportGenerator()

@report_bp.route('/projects/<int:project_id>/generate-report', methods=['POST'])
@require_auth
def generate_project_report(project_id):
    """Genera report PDF per un progetto specifico"""
    try:
        user = User.query.get(session['user_id'])
        project = Project.query.get_or_404(project_id)
        
        # Verifica permessi
        if not user.is_admin() and project.owner_id != user.id:
            return jsonify({'error': 'Accesso negato'}), 403
        
        # Verifica che il progetto abbia dati sufficienti
        if not project.geometry_data or not project.pvgis_data:
            return jsonify({'error': 'Progetto incompleto. Necessari almeno dati geometrici e PVGIS.'}), 400
        
        # Prepara i dati per il report
        project_data = {
            'name': project.name,
            'address': project.address,
            'superficie_lorda_mq': project.superficie_lorda_mq,
            'status': project.status,
            'geometry_data': json.loads(project.geometry_data) if project.geometry_data else {},
            'pvgis_data': json.loads(project.pvgis_data) if project.pvgis_data else {},
            'bess_data': json.loads(project.bess_data) if project.bess_data else {},
            'economic_data': json.loads(project.economic_data) if project.economic_data else {}
        }
        
        # Crea file temporaneo per il PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            output_path = tmp_file.name
        
        # Genera il report
        report_path = report_generator.generate_report(project_data, output_path)
        
        # Nome file per il download
        safe_project_name = "".join(c for c in project.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"Studio_Fattibilita_{safe_project_name}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        return send_file(
            report_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@report_bp.route('/projects/<int:project_id>/report-preview', methods=['GET'])
@require_auth
def preview_project_report(project_id):
    """Anteprima dei dati che saranno inclusi nel report"""
    try:
        user = User.query.get(session['user_id'])
        project = Project.query.get_or_404(project_id)
        
        # Verifica permessi
        if not user.is_admin() and project.owner_id != user.id:
            return jsonify({'error': 'Accesso negato'}), 403
        
        # Prepara i dati per l'anteprima
        preview_data = {
            'project_info': {
                'name': project.name,
                'address': project.address,
                'superficie_lorda_mq': project.superficie_lorda_mq,
                'status': project.status,
                'created_at': project.created_at.isoformat() if project.created_at else None,
                'updated_at': project.updated_at.isoformat() if project.updated_at else None
            },
            'has_geometry_data': bool(project.geometry_data),
            'has_pvgis_data': bool(project.pvgis_data),
            'has_bess_data': bool(project.bess_data),
            'has_economic_data': bool(project.economic_data),
            'report_ready': bool(project.geometry_data and project.pvgis_data)
        }
        
        # Aggiungi KPI se disponibili
        if project.geometry_data:
            geometry_data = json.loads(project.geometry_data)
            preview_data['kpi'] = {
                'potenza_kwp': geometry_data.get('potenza_installabile_kwp', 0),
                'numero_moduli': geometry_data.get('numero_moduli', 0),
                'fattore_riempimento': geometry_data.get('fattore_riempimento_percent', 0)
            }
        
        if project.pvgis_data:
            pvgis_data = json.loads(project.pvgis_data)
            if 'kpi' not in preview_data:
                preview_data['kpi'] = {}
            preview_data['kpi'].update({
                'produzione_annuale_kwh': pvgis_data.get('produzione_annuale_kwh', 0),
                'produzione_specifica_kwh_kwp': pvgis_data.get('produzione_specifica_kwh_kwp', 0)
            })
        
        if project.economic_data:
            economic_data = json.loads(project.economic_data)
            pv_results = economic_data.get('pv_only_results', {})
            if 'kpi' not in preview_data:
                preview_data['kpi'] = {}
            preview_data['kpi'].update({
                'npv': pv_results.get('npv', 0),
                'irr_percent': pv_results.get('irr', 0) * 100,
                'payback_years': pv_results.get('payback_years', 0)
            })
        
        return jsonify({
            'success': True,
            'preview': preview_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@report_bp.route('/projects/bulk-generate-reports', methods=['POST'])
@require_auth
def bulk_generate_reports():
    """Genera report per più progetti contemporaneamente"""
    try:
        user = User.query.get(session['user_id'])
        data = request.get_json()
        project_ids = data.get('project_ids', [])
        
        if not project_ids:
            return jsonify({'error': 'project_ids richiesti'}), 400
        
        generated_reports = []
        failed_reports = []
        
        for project_id in project_ids:
            try:
                project = Project.query.get(project_id)
                if not project:
                    failed_reports.append({
                        'project_id': project_id,
                        'error': 'Progetto non trovato'
                    })
                    continue
                
                # Verifica permessi
                if not user.is_admin() and project.owner_id != user.id:
                    failed_reports.append({
                        'project_id': project_id,
                        'project_name': project.name,
                        'error': 'Accesso negato'
                    })
                    continue
                
                # Verifica completezza dati
                if not project.geometry_data or not project.pvgis_data:
                    failed_reports.append({
                        'project_id': project_id,
                        'project_name': project.name,
                        'error': 'Dati incompleti'
                    })
                    continue
                
                # Prepara i dati per il report
                project_data = {
                    'name': project.name,
                    'address': project.address,
                    'superficie_lorda_mq': project.superficie_lorda_mq,
                    'status': project.status,
                    'geometry_data': json.loads(project.geometry_data),
                    'pvgis_data': json.loads(project.pvgis_data),
                    'bess_data': json.loads(project.bess_data) if project.bess_data else {},
                    'economic_data': json.loads(project.economic_data) if project.economic_data else {}
                }
                
                # Crea directory per i report se non esiste
                reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
                os.makedirs(reports_dir, exist_ok=True)
                
                # Nome file per il report
                safe_project_name = "".join(c for c in project.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                filename = f"Studio_Fattibilita_{safe_project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                output_path = os.path.join(reports_dir, filename)
                
                # Genera il report
                report_path = report_generator.generate_report(project_data, output_path)
                
                generated_reports.append({
                    'project_id': project_id,
                    'project_name': project.name,
                    'report_path': report_path,
                    'filename': filename,
                    'file_size_kb': round(os.path.getsize(report_path) / 1024, 1)
                })
                
            except Exception as e:
                failed_reports.append({
                    'project_id': project_id,
                    'project_name': project.name if 'project' in locals() else 'N/A',
                    'error': str(e)
                })
        
        return jsonify({
            'message': f'{len(generated_reports)} report generati, {len(failed_reports)} falliti',
            'generated_reports': generated_reports,
            'failed_reports': failed_reports,
            'total_requested': len(project_ids),
            'success_count': len(generated_reports),
            'failure_count': len(failed_reports)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@report_bp.route('/reports/templates', methods=['GET'])
@require_auth
def get_report_templates():
    """Ottieni lista dei template di report disponibili"""
    try:
        templates = [
            {
                'id': 'standard',
                'name': 'Report Standard',
                'description': 'Report completo con analisi tecnica ed economica',
                'sections': [
                    'Informazioni Generali',
                    'KPI Riassuntivi', 
                    'Analisi Tecnica',
                    'Layout Impianto',
                    'Produzione Energetica',
                    'Analisi Economica',
                    'Parametri di Calcolo',
                    'Note e Disclaimer'
                ],
                'charts': [
                    'Produzione Mensile',
                    'Analisi Economica',
                    'Layout Fotovoltaico'
                ],
                'default': True
            },
            {
                'id': 'executive',
                'name': 'Executive Summary',
                'description': 'Report sintetico per il management',
                'sections': [
                    'KPI Riassuntivi',
                    'Analisi Economica',
                    'Raccomandazioni'
                ],
                'charts': [
                    'Analisi Economica'
                ],
                'default': False
            },
            {
                'id': 'technical',
                'name': 'Report Tecnico',
                'description': 'Focus su aspetti tecnici e ingegneristici',
                'sections': [
                    'Specifiche Tecniche',
                    'Layout Impianto',
                    'Produzione Energetica',
                    'Dati PVGIS',
                    'Parametri di Calcolo'
                ],
                'charts': [
                    'Produzione Mensile',
                    'Layout Fotovoltaico'
                ],
                'default': False
            }
        ]
        
        return jsonify({
            'templates': templates
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@report_bp.route('/reports/statistics', methods=['GET'])
@require_auth
def get_report_statistics():
    """Ottieni statistiche sui report generati"""
    try:
        user = User.query.get(session['user_id'])
        
        # Directory dei report
        reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
        
        stats = {
            'total_reports': 0,
            'total_size_mb': 0,
            'reports_today': 0,
            'reports_this_week': 0,
            'reports_this_month': 0,
            'average_size_kb': 0,
            'recent_reports': []
        }
        
        if os.path.exists(reports_dir):
            today = datetime.now().date()
            week_start = today - timedelta(days=today.weekday())
            month_start = today.replace(day=1)
            
            total_size = 0
            recent_files = []
            
            for filename in os.listdir(reports_dir):
                if filename.endswith('.pdf'):
                    filepath = os.path.join(reports_dir, filename)
                    file_stat = os.stat(filepath)
                    file_date = datetime.fromtimestamp(file_stat.st_mtime).date()
                    file_size = file_stat.st_size
                    
                    stats['total_reports'] += 1
                    total_size += file_size
                    
                    # Conteggi per periodo
                    if file_date == today:
                        stats['reports_today'] += 1
                    if file_date >= week_start:
                        stats['reports_this_week'] += 1
                    if file_date >= month_start:
                        stats['reports_this_month'] += 1
                    
                    # File recenti
                    recent_files.append({
                        'filename': filename,
                        'size_kb': round(file_size / 1024, 1),
                        'created_at': datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                    })
            
            # Calcola statistiche
            stats['total_size_mb'] = round(total_size / (1024 * 1024), 2)
            stats['average_size_kb'] = round(total_size / (1024 * stats['total_reports']), 1) if stats['total_reports'] > 0 else 0
            
            # Ordina per data e prendi i più recenti
            recent_files.sort(key=lambda x: x['created_at'], reverse=True)
            stats['recent_reports'] = recent_files[:10]
        
        return jsonify({
            'statistics': stats
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

