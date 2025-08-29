"""
Route API per la gestione del workflow dei progetti
"""

from flask import Blueprint, request, jsonify, session
from src.models.user import db, User
from src.models.project import Project
from src.routes.auth import require_auth, require_admin
from src.utils.workflow_manager import WorkflowManager
from datetime import datetime

workflow_bp = Blueprint('workflow', __name__)

# Istanza del workflow manager
workflow_manager = WorkflowManager()

@workflow_bp.route('/projects/<int:project_id>/workflow/status', methods=['PUT'])
@require_auth
def update_project_status(project_id):
    """Aggiorna manualmente lo stato del progetto"""
    try:
        user = User.query.get(session['user_id'])
        project = Project.query.get_or_404(project_id)
        
        # Verifica permessi
        if not user.is_admin() and project.owner_id != user.id:
            return jsonify({'error': 'Accesso negato'}), 403
        
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'error': 'Status richiesto'}), 400
        
        # Verifica se la transizione è permessa
        if not workflow_manager.can_transition_to(project, new_status, user.role):
            return jsonify({'error': 'Transizione non permessa'}), 400
        
        old_status = project.status
        project.status = new_status
        project.last_updated_by = user.id
        project.updated_at = datetime.utcnow()
        
        # Aggiorna note
        if not project.notes:
            project.notes = ""
        
        project.notes += f"\n[{datetime.now().strftime('%d/%m/%Y %H:%M')}] Stato cambiato manualmente da {user.username}: {old_status} → {new_status}"
        
        db.session.commit()
        
        # Ottieni progresso aggiornato
        workflow_progress = workflow_manager.get_workflow_progress(project)
        
        return jsonify({
            'message': f'Stato aggiornato da {old_status} a {new_status}',
            'project': project.to_dict(),
            'workflow_progress': workflow_progress
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@workflow_bp.route('/projects/<int:project_id>/workflow/auto-update', methods=['POST'])
@require_auth
def auto_update_project_status(project_id):
    """Aggiorna automaticamente lo stato del progetto basato sui dati"""
    try:
        user = User.query.get(session['user_id'])
        project = Project.query.get_or_404(project_id)
        
        # Verifica permessi
        if not user.is_admin() and project.owner_id != user.id:
            return jsonify({'error': 'Accesso negato'}), 403
        
        old_status = project.status
        updated = workflow_manager.update_project_status(project, user.role)
        
        if updated:
            db.session.commit()
            workflow_progress = workflow_manager.get_workflow_progress(project)
            
            return jsonify({
                'message': f'Stato aggiornato automaticamente da {old_status} a {project.status}',
                'updated': True,
                'project': project.to_dict(),
                'workflow_progress': workflow_progress
            }), 200
        else:
            return jsonify({
                'message': 'Nessun aggiornamento necessario',
                'updated': False,
                'project': project.to_dict(),
                'workflow_progress': workflow_manager.get_workflow_progress(project)
            }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@workflow_bp.route('/projects/<int:project_id>/workflow/progress', methods=['GET'])
@require_auth
def get_project_workflow_progress(project_id):
    """Ottieni il progresso del workflow per un progetto"""
    try:
        user = User.query.get(session['user_id'])
        project = Project.query.get_or_404(project_id)
        
        # Verifica permessi
        if not user.is_admin() and project.owner_id != user.id:
            return jsonify({'error': 'Accesso negato'}), 403
        
        workflow_progress = workflow_manager.get_workflow_progress(project)
        available_transitions = workflow_manager.get_available_transitions(project, user.role)
        status_info = workflow_manager.get_status_description(project.status)
        
        return jsonify({
            'workflow_progress': workflow_progress,
            'available_transitions': available_transitions,
            'status_info': status_info
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@workflow_bp.route('/workflow/status-definitions', methods=['GET'])
@require_auth
def get_status_definitions():
    """Ottieni le definizioni di tutti gli stati possibili"""
    try:
        statuses = ['bozza', 'da_analizzare', 'in_analisi', 'in_revisione', 'completato', 'archiviato']
        
        definitions = {}
        for status in statuses:
            definitions[status] = workflow_manager.get_status_description(status)
        
        return jsonify({
            'status_definitions': definitions
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@workflow_bp.route('/projects/workflow/bulk-update', methods=['POST'])
@require_admin
def bulk_update_workflow():
    """Aggiornamento massivo del workflow per più progetti"""
    try:
        data = request.get_json()
        project_ids = data.get('project_ids', [])
        action = data.get('action')  # 'auto_update' o 'set_status'
        new_status = data.get('status')  # per 'set_status'
        
        if not project_ids:
            return jsonify({'error': 'project_ids richiesti'}), 400
        
        user = User.query.get(session['user_id'])
        updated_projects = []
        
        for project_id in project_ids:
            project = Project.query.get(project_id)
            if not project:
                continue
            
            old_status = project.status
            
            if action == 'auto_update':
                updated = workflow_manager.update_project_status(project, user.role)
                if updated:
                    updated_projects.append({
                        'id': project.id,
                        'name': project.name,
                        'old_status': old_status,
                        'new_status': project.status
                    })
            
            elif action == 'set_status' and new_status:
                if workflow_manager.can_transition_to(project, new_status, user.role):
                    project.status = new_status
                    project.last_updated_by = user.id
                    project.updated_at = datetime.utcnow()
                    
                    updated_projects.append({
                        'id': project.id,
                        'name': project.name,
                        'old_status': old_status,
                        'new_status': new_status
                    })
        
        db.session.commit()
        
        return jsonify({
            'message': f'{len(updated_projects)} progetti aggiornati',
            'updated_projects': updated_projects
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@workflow_bp.route('/dashboard/workflow-stats', methods=['GET'])
@require_auth
def get_workflow_stats():
    """Ottieni statistiche del workflow per la dashboard"""
    try:
        user = User.query.get(session['user_id'])
        
        if user.is_admin():
            # Admin vede tutti i progetti
            projects = Project.query.all()
        else:
            # User vede solo i suoi progetti
            projects = Project.query.filter_by(owner_id=user.id).all()
        
        # Conta progetti per stato
        status_counts = {}
        for project in projects:
            status = project.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Calcola progresso medio
        total_progress = 0
        for project in projects:
            progress = workflow_manager.get_workflow_progress(project)
            total_progress += progress['progress_percentage']
        
        avg_progress = total_progress / len(projects) if projects else 0
        
        # Progetti che necessitano attenzione
        needs_attention = []
        for project in projects:
            next_status = workflow_manager.get_next_status(project)
            if next_status:
                needs_attention.append({
                    'id': project.id,
                    'name': project.name,
                    'current_status': project.status,
                    'next_status': next_status.value,
                    'last_updated': project.updated_at.isoformat() if project.updated_at else None
                })
        
        # Aggiungi descrizioni stati
        status_info = {}
        for status in status_counts.keys():
            status_info[status] = workflow_manager.get_status_description(status)
        
        return jsonify({
            'status_counts': status_counts,
            'status_info': status_info,
            'total_projects': len(projects),
            'average_progress': round(avg_progress, 1),
            'needs_attention': needs_attention[:10]  # Primi 10
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

