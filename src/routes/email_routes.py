import os
from flask import Blueprint, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
import pandas as pd
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from src.models.user import db
from src.models.email_campaign import EmailCampaign, SentEmail
import threading
import time

email_bp = Blueprint("email", __name__)

UPLOAD_FOLDER = "/tmp/uploads"
ALLOWED_EXTENSIONS = {"xlsx", "xls"}

def get_base_url():
    """الحصول على عنوان URL الأساسي للتتبع"""
    # يمكن تعيين عنوان URL الخارجي من خلال متغير البيئة
    external_url = os.environ.get("EXTERNAL_URL")
    if external_url:
        return external_url.rstrip("/")
    
    # إذا لم يتم تعيين متغير البيئة، استخدم localhost
    return "http://localhost:5000"

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def create_upload_folder():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

@email_bp.route("/upload-excel", methods=["POST"])
def upload_excel():
    create_upload_folder()
    
    if "file" not in request.files:
        return jsonify({"error": "لم يتم اختيار ملف"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "لم يتم اختيار ملف"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        try:
            # قراءة ملف Excel
            df = pd.read_excel(filepath)
            
            # البحث عن عمود الإيميلات
            email_column = None
            for col in df.columns:
                if "email" in col.lower() or "mail" in col.lower() or "بريد" in col.lower():
                    email_column = col
                    break
            
            if email_column is None:
                # استخدام العمود الأول إذا لم يتم العثور على عمود إيميل
                email_column = df.columns[0]
            
            emails = df[email_column].dropna().tolist()
            
            # تنظيف الإيميلات
            valid_emails = []
            for email in emails:
                email_str = str(email).strip()
                if "@" in email_str and "." in email_str:
                    valid_emails.append(email_str)
            
            os.remove(filepath)  # حذف الملف المؤقت
            
            return jsonify({
                "success": True,
                "emails": valid_emails,
                "count": len(valid_emails)
            })
            
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({"error": f"خطأ في قراءة الملف: {str(e)}"}), 400
    
    return jsonify({"error": "نوع الملف غير مدعوم"}), 400

@email_bp.route("/send-campaign", methods=["POST"])
def send_campaign():
    data = request.get_json()
    
    required_fields = ["sender_name", "sender_email", "subject", "message", "emails"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"الحقل {field} مطلوب"}), 400
    
    # إنشاء حملة جديدة
    campaign = EmailCampaign(
        sender_name=data["sender_name"],
        sender_email=data["sender_email"],
        subject=data["subject"],
        message=data["message"]
    )
    
    db.session.add(campaign)
    db.session.commit()
    
    # إنشاء سجلات الإيميلات المرسلة
    sent_emails = []
    for email in data["emails"]:
        tracking_id = str(uuid.uuid4())
        sent_email = SentEmail(
            campaign_id=campaign.id,
            recipient_email=email,
            tracking_id=tracking_id
        )
        sent_emails.append(sent_email)
        db.session.add(sent_email)
    
    db.session.commit()
    
    # إرسال الإيميلات في خيط منفصل
    thread = threading.Thread(target=send_emails_async, args=(current_app._get_current_object(), campaign.id, data))
    thread.start()
    
    return jsonify({
        "success": True,
        "campaign_id": campaign.id,
        "message": "تم بدء إرسال الإيميلات"
    })

def send_emails_async(app, campaign_id, data):
    """إرسال الإيميلات بشكل غير متزامن"""
    with app.app_context():
        try:
            # إعداد خادم SMTP (يمكن تخصيصه حسب الحاجة)
            smtp_server = data.get("smtp_server", "smtp.gmail.com")
            smtp_port = data.get("smtp_port", 587)
            smtp_username = data.get("smtp_username", data["sender_email"])
            smtp_password = data.get("smtp_password", "")

            if not smtp_password:
                # تحديث حالة جميع الإيميلات إلى فشل
                SentEmail.query.filter_by(campaign_id=campaign_id).update({
                    "status": "failed",
                    "error_message": "كلمة مرور SMTP غير محددة",
                })
                db.session.commit()
                return

            # الاتصال بخادم SMTP
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_username, smtp_password)

            # الحصول على الإيميلات المرسلة لهذه الحملة
            sent_emails = SentEmail.query.filter_by(campaign_id=campaign_id).all()

            for sent_email in sent_emails:
                try:
                    # إنشاء رسالة الإيميل
                    msg = MIMEMultipart("alternative")
                    msg["From"] = f"{data["sender_name"]} <{data["sender_email"]}>"
                    msg["To"] = sent_email.recipient_email
                    msg["Subject"] = data["subject"]

                    # إضافة بكسل التتبع
                    base_url = get_base_url()
                    tracking_pixel = f"<img src=\"{base_url}/api/track/{sent_email.tracking_id}\" width=\"1\" height=\"1\" style=\"display:none;\">"
                    html_message = data["message"] + tracking_pixel

                    # إضافة المحتوى
                    text_part = MIMEText(data["message"], "plain", "utf-8")
                    html_part = MIMEText(html_message, "html", "utf-8")

                    msg.attach(text_part)
                    msg.attach(html_part)

                    # إرسال الإيميل
                    server.send_message(msg)

                    # تحديث حالة الإيميل
                    sent_email.status = "sent"
                    sent_email.sent_at = datetime.utcnow()

                    # تأخير قصير بين الإيميلات
                    time.sleep(1)

                except Exception as e:
                    # تحديث حالة الإيميل في حالة الفشل
                    sent_email.status = "failed"
                    sent_email.error_message = str(e)
                
                db.session.commit()

            server.quit()

        except Exception as e:
            # تحديث حالة جميع الإيميلات إلى فشل
            SentEmail.query.filter_by(campaign_id=campaign_id).update({
                "status": "failed",
                "error_message": str(e),
            })
            db.session.commit()

@email_bp.route("/track/<tracking_id>")
def track_email_open(tracking_id):
    """تتبع فتح الإيميل"""
    sent_email = SentEmail.query.filter_by(tracking_id=tracking_id).first()
    
    if sent_email and not sent_email.is_opened:
        sent_email.is_opened = True
        sent_email.opened_at = datetime.utcnow()
        db.session.commit()
    
    # إرجاع صورة شفافة 1x1 بكسل
    from io import BytesIO
    import base64
    
    # صورة GIF شفافة 1x1 بكسل
    gif_data = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")
    
    return send_file(
        BytesIO(gif_data),
        mimetype="image/gif",
        as_attachment=False
    )

@email_bp.route("/campaigns")
def get_campaigns():
    """الحصول على جميع الحملات"""
    campaigns = EmailCampaign.query.order_by(EmailCampaign.created_at.desc()).all()
    return jsonify([campaign.to_dict() for campaign in campaigns])

@email_bp.route("/campaign/<int:campaign_id>/stats")
def get_campaign_stats(campaign_id):
    """الحصول على إحصائيات الحملة"""
    campaign = EmailCampaign.query.get_or_404(campaign_id)
    sent_emails = SentEmail.query.filter_by(campaign_id=campaign_id).all()
    
    total = len(sent_emails)
    sent = len([e for e in sent_emails if e.status == "sent"])
    failed = len([e for e in sent_emails if e.status == "failed"])
    opened = len([e for e in sent_emails if e.is_opened])
    
    return jsonify({
        "campaign": campaign.to_dict(),
        "stats": {
            "total": total,
            "sent": sent,
            "failed": failed,
            "opened": opened,
            "open_rate": (opened / sent * 100) if sent > 0 else 0
        },
        "emails": [email.to_dict() for email in sent_emails]
    })

@email_bp.route("/campaign/<int:campaign_id>/export/<status>")
def export_emails(campaign_id, status):
    """تصدير الإيميلات حسب الحالة"""
    if status == "opened":
        emails = SentEmail.query.filter_by(campaign_id=campaign_id, is_opened=True).all()
    elif status == "failed":
        emails = SentEmail.query.filter_by(campaign_id=campaign_id, status="failed").all()
    elif status == "sent":
        emails = SentEmail.query.filter_by(campaign_id=campaign_id, status="sent").all()
    else:
        return jsonify({"error": "حالة غير صحيحة"}), 400
    
    email_list = [email.recipient_email for email in emails]
    
    return jsonify({
        "emails": email_list,
        "count": len(email_list)
    })


