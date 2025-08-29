from src.models.user import db
from datetime import datetime

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    address = db.Column(db.Text)
    latitude = db.Column(db.Numeric(10, 8))
    longitude = db.Column(db.Numeric(11, 8))
    superficie_lorda_mq = db.Column(db.Numeric(10, 2))
    
    # Workflow status
    status = db.Column(db.String(20), nullable=False, default='Bozza')  # Bozza, Da Analizzare, In Analisi, In Revisione, Completato, Archiviato
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    last_updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Parametri fotovoltaico
    tilt_degrees = db.Column(db.Numeric(5, 2))
    azimuth_degrees = db.Column(db.Numeric(5, 2))
    orientation_type = db.Column(db.String(20), default='sud')  # 'sud' or 'est_ovest'
    modulo_potenza_wp = db.Column(db.Integer)
    modulo_lunghezza_mm = db.Column(db.Integer)
    modulo_larghezza_mm = db.Column(db.Integer)
    margine_metri = db.Column(db.Numeric(5, 2))
    
    # Parametri BESS
    bess_enabled = db.Column(db.Boolean, default=False)
    bess_capacity_kwh = db.Column(db.Numeric(10, 2))
    bess_power_kw = db.Column(db.Numeric(10, 2))
    bess_dod = db.Column(db.Numeric(3, 2), default=0.8)
    bess_c_rate = db.Column(db.Numeric(3, 2), default=1.0)
    bess_capex_eur_kwh = db.Column(db.Numeric(10, 2), default=500)
    
    # Parametri economici
    capex_eur_kwp = db.Column(db.Numeric(10, 2))
    om_eur_kwp_anno = db.Column(db.Numeric(10, 2))
    wacc_percent = db.Column(db.Numeric(5, 2), default=5.0)
    
    # Risultati calcolati
    potenza_installabile_kwp = db.Column(db.Numeric(10, 2))
    produzione_annua_kwh = db.Column(db.Numeric(12, 2))
    autoconsumo_percent = db.Column(db.Numeric(5, 2))
    npv_eur = db.Column(db.Numeric(12, 2))
    irr_percent = db.Column(db.Numeric(5, 2))
    payback_anni = db.Column(db.Numeric(5, 2))
    
    # Metadati aggiuntivi per import massivo
    cod_sito = db.Column(db.String(50))
    regione = db.Column(db.String(100))
    provincia = db.Column(db.String(100))
    comune = db.Column(db.String(100))
    descrizione_immobile = db.Column(db.Text)
    tipo_proprieta = db.Column(db.String(100))
    cluster_potenza = db.Column(db.String(100))

    def __repr__(self):
        return f'<Project {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'latitude': float(self.latitude) if self.latitude else None,
            'longitude': float(self.longitude) if self.longitude else None,
            'superficie_lorda_mq': float(self.superficie_lorda_mq) if self.superficie_lorda_mq else None,
            'status': self.status,
            'owner_id': self.owner_id,
            'created_by': self.created_by,
            'last_updated_by': self.last_updated_by,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            
            # Parametri tecnici
            'tilt_degrees': float(self.tilt_degrees) if self.tilt_degrees else None,
            'azimuth_degrees': float(self.azimuth_degrees) if self.azimuth_degrees else None,
            'orientation_type': self.orientation_type,
            'modulo_potenza_wp': self.modulo_potenza_wp,
            'modulo_lunghezza_mm': self.modulo_lunghezza_mm,
            'modulo_larghezza_mm': self.modulo_larghezza_mm,
            'margine_metri': float(self.margine_metri) if self.margine_metri else None,
            
            # BESS
            'bess_enabled': self.bess_enabled,
            'bess_capacity_kwh': float(self.bess_capacity_kwh) if self.bess_capacity_kwh else None,
            'bess_power_kw': float(self.bess_power_kw) if self.bess_power_kw else None,
            'bess_dod': float(self.bess_dod) if self.bess_dod else None,
            'bess_c_rate': float(self.bess_c_rate) if self.bess_c_rate else None,
            'bess_capex_eur_kwh': float(self.bess_capex_eur_kwh) if self.bess_capex_eur_kwh else None,
            
            # Economici
            'capex_eur_kwp': float(self.capex_eur_kwp) if self.capex_eur_kwp else None,
            'om_eur_kwp_anno': float(self.om_eur_kwp_anno) if self.om_eur_kwp_anno else None,
            'wacc_percent': float(self.wacc_percent) if self.wacc_percent else None,
            
            # Risultati
            'potenza_installabile_kwp': float(self.potenza_installabile_kwp) if self.potenza_installabile_kwp else None,
            'produzione_annua_kwh': float(self.produzione_annua_kwh) if self.produzione_annua_kwh else None,
            'autoconsumo_percent': float(self.autoconsumo_percent) if self.autoconsumo_percent else None,
            'npv_eur': float(self.npv_eur) if self.npv_eur else None,
            'irr_percent': float(self.irr_percent) if self.irr_percent else None,
            'payback_anni': float(self.payback_anni) if self.payback_anni else None,
            
            # Metadati
            'cod_sito': self.cod_sito,
            'regione': self.regione,
            'provincia': self.provincia,
            'comune': self.comune,
            'descrizione_immobile': self.descrizione_immobile,
            'tipo_proprieta': self.tipo_proprieta,
            'cluster_potenza': self.cluster_potenza
        }

class BulkImport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255))
    imported_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    import_date = db.Column(db.DateTime, default=datetime.utcnow)
    projects_created = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='In Corso')  # 'In Corso', 'Completato', 'Errore'
    error_message = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'imported_by': self.imported_by,
            'import_date': self.import_date.isoformat() if self.import_date else None,
            'projects_created': self.projects_created,
            'status': self.status,
            'error_message': self.error_message
        }

class SystemParameter(db.Model):
    """Parametri globali del sistema configurabili dall'admin"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # 'economic', 'technical', 'bess', etc.
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'category': self.category,
            'updated_by': self.updated_by,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

