from datetime import datetime
from apps import db
from sqlalchemy.dialects.postgresql import JSON

class TopicCompetitorsJob(db.Model):
    __tablename__ = 'topic_competitors_jobs'

    id = db.Column(db.Integer, primary_key=True)
    main_topic = db.Column(db.String(255), nullable=False)
    subtopics = db.Column(JSON, nullable=True)
    keywords = db.Column(JSON, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(32), nullable=False, default='processing')
    result = db.Column(JSON, nullable=True)
    error = db.Column(db.Text, nullable=True)
    summary = db.Column(db.Text, nullable=True)
    top_domains = db.Column(JSON, nullable=True)
    user_ip = db.Column(db.String(64), nullable=True)
    duration = db.Column(db.Float, nullable=True)
    celery_task_id = db.Column(db.String(128), nullable=True)
    progress = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'main_topic': self.main_topic,
            'subtopics': self.subtopics,
            'keywords': self.keywords,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'status': self.status,
            'result': self.result,
            'error': self.error,
            'summary': self.summary,
            'top_domains': self.top_domains,
            'user_ip': self.user_ip,
            'duration': self.duration,
            'celery_task_id': self.celery_task_id,
            'progress': self.progress
        } 