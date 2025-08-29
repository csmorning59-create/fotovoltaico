"""
Modulo per la gestione automatica del workflow degli stati dei progetti
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

class ProjectStatus(Enum):
    """Stati possibili dei progetti"""
    BOZZA = "bozza"
    DA_ANALIZZARE = "da_analizzare"
    IN_ANALISI = "in_analisi"
    IN_REVISIONE = "in_revisione"
    COMPLETATO = "completato"
    ARCHIVIATO = "archiviato"

class WorkflowTransition:
    """Definisce una transizione di workflow"""
    def __init__(self, from_status: ProjectStatus, to_status: ProjectStatus, 
                 condition_func=None, auto_trigger=False):
        self.from_status = from_status
        self.to_status = to_status
        self.condition_func = condition_func
        self.auto_trigger = auto_trigger

class WorkflowManager:
    """Gestisce il workflow automatico degli stati dei progetti"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.transitions = self._setup_transitions()
    
    def _setup_transitions(self) -> List[WorkflowTransition]:
        """Configura le transizioni di workflow"""
        return [
            # Transizioni automatiche
            WorkflowTransition(
                ProjectStatus.BOZZA, 
                ProjectStatus.DA_ANALIZZARE,
                condition_func=self._has_basic_data,
                auto_trigger=True
            ),
            WorkflowTransition(
                ProjectStatus.DA_ANALIZZARE, 
                ProjectStatus.IN_ANALISI,
                condition_func=self._has_geometry_data,
                auto_trigger=True
            ),
            WorkflowTransition(
                ProjectStatus.IN_ANALISI, 
                ProjectStatus.IN_REVISIONE,
                condition_func=self._has_pvgis_data,
                auto_trigger=True
            ),
            WorkflowTransition(
                ProjectStatus.IN_REVISIONE, 
                ProjectStatus.COMPLETATO,
                condition_func=self._has_economic_analysis,
                auto_trigger=True
            ),
            
            # Transizioni manuali (admin only)
            WorkflowTransition(ProjectStatus.COMPLETATO, ProjectStatus.ARCHIVIATO),
            WorkflowTransition(ProjectStatus.ARCHIVIATO, ProjectStatus.COMPLETATO),
            WorkflowTransition(ProjectStatus.IN_REVISIONE, ProjectStatus.IN_ANALISI),
            WorkflowTransition(ProjectStatus.IN_ANALISI, ProjectStatus.DA_ANALIZZARE),
        ]
    
    def _has_basic_data(self, project) -> bool:
        """Verifica se il progetto ha i dati di base"""
        return (
            project.name and 
            project.address and 
            project.surface_area and 
            project.surface_area > 0
        )
    
    def _has_geometry_data(self, project) -> bool:
        """Verifica se il progetto ha i dati geometrici"""
        return (
            project.geometry_data is not None and 
            'potenza_installabile_kwp' in project.geometry_data and
            project.geometry_data['potenza_installabile_kwp'] > 0
        )
    
    def _has_pvgis_data(self, project) -> bool:
        """Verifica se il progetto ha i dati PVGIS"""
        return (
            project.pvgis_data is not None and
            'produzione_annuale_kwh' in project.pvgis_data and
            project.pvgis_data['produzione_annuale_kwh'] > 0
        )
    
    def _has_economic_analysis(self, project) -> bool:
        """Verifica se il progetto ha l'analisi economica"""
        return (
            project.economic_data is not None and
            'pv_only_results' in project.economic_data and
            'npv' in project.economic_data['pv_only_results']
        )
    
    def get_next_status(self, project) -> Optional[ProjectStatus]:
        """Determina il prossimo stato automatico per il progetto"""
        current_status = ProjectStatus(project.status)
        
        for transition in self.transitions:
            if (transition.from_status == current_status and 
                transition.auto_trigger and
                transition.condition_func and
                transition.condition_func(project)):
                return transition.to_status
        
        return None
    
    def can_transition_to(self, project, target_status: str, user_role: str = 'user') -> bool:
        """Verifica se è possibile transire a un determinato stato"""
        current_status = ProjectStatus(project.status)
        target = ProjectStatus(target_status)
        
        for transition in self.transitions:
            if (transition.from_status == current_status and 
                transition.to_status == target):
                
                # Transizioni automatiche sempre permesse se condizione soddisfatta
                if transition.auto_trigger and transition.condition_func:
                    return transition.condition_func(project)
                
                # Transizioni manuali solo per admin
                if not transition.auto_trigger:
                    return user_role == 'admin'
                
                # Transizioni senza condizioni sempre permesse
                return True
        
        return False
    
    def update_project_status(self, project, user_role: str = 'user') -> bool:
        """Aggiorna automaticamente lo stato del progetto se possibile"""
        next_status = self.get_next_status(project)
        
        if next_status:
            old_status = project.status
            project.status = next_status.value
            project.last_updated = datetime.now()
            
            # Log della transizione
            self.logger.info(f"Progetto {project.id} transito da {old_status} a {next_status.value}")
            
            # Aggiorna note di sistema
            if not project.notes:
                project.notes = ""
            
            project.notes += f"\n[{datetime.now().strftime('%d/%m/%Y %H:%M')}] Stato aggiornato automaticamente: {old_status} → {next_status.value}"
            
            return True
        
        return False
    
    def get_workflow_progress(self, project) -> Dict:
        """Calcola il progresso del workflow per il progetto"""
        current_status = ProjectStatus(project.status)
        
        # Definisce l'ordine degli stati nel workflow
        workflow_order = [
            ProjectStatus.BOZZA,
            ProjectStatus.DA_ANALIZZARE,
            ProjectStatus.IN_ANALISI,
            ProjectStatus.IN_REVISIONE,
            ProjectStatus.COMPLETATO
        ]
        
        try:
            current_index = workflow_order.index(current_status)
            progress_percentage = (current_index / (len(workflow_order) - 1)) * 100
        except ValueError:
            # Stato non nel workflow principale (es. ARCHIVIATO)
            progress_percentage = 100 if current_status == ProjectStatus.ARCHIVIATO else 0
        
        # Verifica completamento delle fasi
        phases_completed = {
            'basic_data': self._has_basic_data(project),
            'geometry': self._has_geometry_data(project),
            'pvgis': self._has_pvgis_data(project),
            'economic': self._has_economic_analysis(project)
        }
        
        return {
            'current_status': current_status.value,
            'progress_percentage': progress_percentage,
            'phases_completed': phases_completed,
            'next_possible_status': self.get_next_status(project).value if self.get_next_status(project) else None
        }
    
    def get_available_transitions(self, project, user_role: str = 'user') -> List[str]:
        """Restituisce le transizioni disponibili per il progetto"""
        current_status = ProjectStatus(project.status)
        available = []
        
        for transition in self.transitions:
            if transition.from_status == current_status:
                # Verifica permessi e condizioni
                if transition.auto_trigger and transition.condition_func:
                    if transition.condition_func(project):
                        available.append(transition.to_status.value)
                elif not transition.auto_trigger and user_role == 'admin':
                    available.append(transition.to_status.value)
                elif not transition.condition_func:
                    available.append(transition.to_status.value)
        
        return available
    
    def get_status_description(self, status: str) -> Dict:
        """Restituisce descrizione e colore per lo stato"""
        descriptions = {
            ProjectStatus.BOZZA.value: {
                'label': 'Bozza',
                'description': 'Progetto creato, dati di base inseriti',
                'color': '#6B7280',
                'icon': '📝'
            },
            ProjectStatus.DA_ANALIZZARE.value: {
                'label': 'Da Analizzare',
                'description': 'Pronto per analisi tecnica',
                'color': '#F59E0B',
                'icon': '⏳'
            },
            ProjectStatus.IN_ANALISI.value: {
                'label': 'In Analisi',
                'description': 'Calcoli geometrici e PVGIS in corso',
                'color': '#3B82F6',
                'icon': '🔬'
            },
            ProjectStatus.IN_REVISIONE.value: {
                'label': 'In Revisione',
                'description': 'Analisi tecnica completata, in revisione',
                'color': '#8B5CF6',
                'icon': '👁️'
            },
            ProjectStatus.COMPLETATO.value: {
                'label': 'Completato',
                'description': 'Analisi completa, pronto per consegna',
                'color': '#10B981',
                'icon': '✅'
            },
            ProjectStatus.ARCHIVIATO.value: {
                'label': 'Archiviato',
                'description': 'Progetto archiviato',
                'color': '#6B7280',
                'icon': '📦'
            }
        }
        
        return descriptions.get(status, {
            'label': status.title(),
            'description': 'Stato sconosciuto',
            'color': '#6B7280',
            'icon': '❓'
        })


# Test del modulo
if __name__ == "__main__":
    # Simulazione di un progetto per test
    class MockProject:
        def __init__(self):
            self.id = 1
            self.name = "Test Project"
            self.address = "Via Test 123"
            self.surface_area = 2500
            self.status = "bozza"
            self.geometry_data = None
            self.pvgis_data = None
            self.economic_data = None
            self.notes = ""
            self.last_updated = datetime.now()
    
    # Test workflow
    wm = WorkflowManager()
    project = MockProject()
    
    print("=== TEST WORKFLOW MANAGER ===")
    print(f"Stato iniziale: {project.status}")
    
    # Test transizione da bozza
    progress = wm.get_workflow_progress(project)
    print(f"Progresso: {progress['progress_percentage']}%")
    print(f"Fasi completate: {progress['phases_completed']}")
    
    # Simula aggiunta dati geometrici
    project.geometry_data = {'potenza_installabile_kwp': 228.7}
    wm.update_project_status(project)
    print(f"Dopo geometria: {project.status}")
    
    # Simula aggiunta dati PVGIS
    project.pvgis_data = {'produzione_annuale_kwh': 164830}
    wm.update_project_status(project)
    print(f"Dopo PVGIS: {project.status}")
    
    # Simula aggiunta analisi economica
    project.economic_data = {'pv_only_results': {'npv': 113823}}
    wm.update_project_status(project)
    print(f"Dopo economia: {project.status}")
    
    # Test descrizioni stati
    for status in ['bozza', 'da_analizzare', 'in_analisi', 'completato']:
        desc = wm.get_status_description(status)
        print(f"{desc['icon']} {desc['label']}: {desc['description']}")

