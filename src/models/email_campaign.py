from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.user import db

class EmailCampaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_name = db.Column(db.String(100), nullable=False)
    sender_email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقة مع الإيميلات المرسلة
    sent_emails = db.relationship('SentEmail', backref='campaign', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'sender_name': self.sender_name,
            'sender_email': self.sender_email,
            'subject': self.subject,
            'message': self.message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class SentEmail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('email_campaign.id'), nullable=False)
    recipient_email = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, sent, failed
    sent_at = db.Column(db.DateTime)
    opened_at = db.Column(db.DateTime)
    is_opened = db.Column(db.Boolean, default=False)
    tracking_id = db.Column(db.String(100), unique=True)
    error_message = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'recipient_email': self.recipient_email,
            'status': self.status,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None,
            'is_opened': self.is_opened,
            'tracking_id': self.tracking_id,
            'error_message': self.error_message
        }

