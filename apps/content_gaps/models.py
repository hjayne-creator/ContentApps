from datetime import datetime
from apps import db

class ContentGapsJob(db.Model):
    __tablename__ = 'content_gaps_jobs'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String(36), nullable=False)  # UUID
    job_id = db.Column(db.String(36), nullable=False)  # UUID
    status = db.Column(db.String(50), nullable=False)
    error_message = db.Column(db.Text)
    compare_url = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('project_id', 'job_id', name='uix_project_job'),
    )

    def to_dict(self):
        return {
            'job_id': self.job_id,
            'status': self.status,
            'error_message': self.error_message,
            'compare_url': self.compare_url,
            'created_at': self.created_at.isoformat() if self.created_at else None
        } 