import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from src.models.user import db
from src.routes.user import user_bp
from src.routes.auth import auth_bp
from src.routes.project import project_bp
from src.routes.geometry import geometry_bp
from src.routes.pvgis import pvgis_bp
from src.routes.bess import bess_bp
from src.routes.economic import economic_bp
from src.routes.workflow import workflow_bp
from src.routes.report import report_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Registra blueprint
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(project_bp, url_prefix='/api')
app.register_blueprint(geometry_bp, url_prefix='/api')
app.register_blueprint(pvgis_bp, url_prefix='/api')
app.register_blueprint(bess_bp, url_prefix='/api')
app.register_blueprint(economic_bp, url_prefix='/api')
app.register_blueprint(workflow_bp, url_prefix='/api')
app.register_blueprint(report_bp, url_prefix='/api')

# Configurazione database
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file upload

db.init_app(app)

# Importa tutti i modelli per creare le tabelle
from src.models.project import Project, BulkImport, SystemParameter

with app.app_context():
    db.create_all()
    
    # Crea utente admin di default se non esiste
    from src.models.user import User
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_user = User(
            username='admin',
            email='admin@fotovoltaico.com',
            role='admin'
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.commit()
        print("Utente admin creato: username=admin, password=admin123")

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
