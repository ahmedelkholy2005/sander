import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from src.models.user import db
from src.models.email_campaign import EmailCampaign, SentEmail
from src.routes.user import user_bp
from src.routes.email_routes import email_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# إضافة دعم CORS
from flask_cors import CORS
CORS(app)

app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(email_bp, url_prefix='/api')

# uncomment if you need to use database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", 
    f"sqlite:///{os.path.join(os.getcwd(), 'app.db')}" # Fallback for local development
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)
with app.app_context():
    db.create_all() 

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
    # طباعة معلومات عن إعداد Ngrok
    external_url = os.environ.get('EXTERNAL_URL')
    if external_url:
        print(f"🌐 تم تفعيل التتبع العالمي!")
        print(f"📧 عنوان URL للتتبع: {external_url}")
        print(f"✅ سيتم تتبع فتح الإيميلات من أي مكان في العالم")
    else:
        print(f"🏠 وضع التتبع المحلي")
        print(f"📧 عنوان URL للتتبع: http://localhost:5000")
        print(f"⚠️  سيتم تتبع فتح الإيميلات من نفس الجهاز فقط")
        print(f"💡 لتفعيل التتبع العالمي، استخدم: run_with_ngrok.bat")
    
    print(f"🚀 بدء تشغيل الخادم على http://0.0.0.0:5000")
    print(f"📱 يمكنك الوصول للتطبيق من: http://localhost:5000")
    print("-" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
