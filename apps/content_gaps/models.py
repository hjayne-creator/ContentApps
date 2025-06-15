from datetime import datetime
import uuid
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint, JSON, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from extensions import db

def init_db(app):
    """Create database tables if they don't exist"""
    with app.app_context():
        db.create_all()

class Project(db.Model):
    __tablename__ = 'content_gaps_projects'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_name = Column(String(255), nullable=False)
    primary_url = Column(String(255), nullable=False)
    is_my_site = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    topic_trees = relationship('TopicTree', backref='project', lazy=True, cascade='all, delete-orphan')
    sites = relationship('Site', backref='project', lazy=True, cascade='all, delete-orphan')
    jobs = relationship('ContentGapsJob', backref='project', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'project_name': self.project_name,
            'primary_url': self.primary_url,
            'is_my_site': self.is_my_site,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ContentGapsJob(db.Model):
    __tablename__ = 'content_gaps_jobs'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey('content_gaps_projects.id', ondelete='CASCADE'), nullable=False)
    job_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String(50), nullable=False)
    error_message = Column(Text)
    compare_url = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('project_id', 'job_id', name='uix_project_job'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': str(self.project_id),
            'job_id': str(self.job_id),
            'status': self.status,
            'error_message': self.error_message,
            'compare_url': self.compare_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class TopicTree(db.Model):
    __tablename__ = 'content_gaps_topic_trees'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('content_gaps_projects.id', ondelete='CASCADE'), nullable=False)
    tree_name = Column(String(255), nullable=False)
    root_topic = Column(String(255), nullable=False)
    tree_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': str(self.id),
            'project_id': str(self.project_id),
            'tree_name': self.tree_name,
            'root_topic': self.root_topic,
            'tree': self.tree_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Site(db.Model):
    __tablename__ = 'content_gaps_sites'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('content_gaps_projects.id', ondelete='CASCADE'), nullable=False)
    label = Column(String(255), nullable=False)
    is_my_site = Column(Boolean, default=False)
    pages = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': str(self.id),
            'project_id': str(self.project_id),
            'label': self.label,
            'is_my_site': self.is_my_site,
            'pages': self.pages,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Match(db.Model):
    __tablename__ = 'content_gaps_matches'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey('content_gaps_projects.id', ondelete='CASCADE'), nullable=False)
    tree_id = Column(UUID(as_uuid=True), ForeignKey('content_gaps_topic_trees.id', ondelete='CASCADE'), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey('content_gaps_sites.id', ondelete='CASCADE'), nullable=False)
    page_index = Column(Integer, nullable=False)
    matched_topics = Column(JSON, nullable=False)
    similarity_scores = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('project_id', 'tree_id', 'site_id', 'page_index', name='uix_match_unique'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': str(self.project_id),
            'tree_id': str(self.tree_id),
            'site_id': str(self.site_id),
            'page_index': self.page_index,
            'matched_topics': self.matched_topics,
            'similarity_scores': self.similarity_scores,
            'created_at': self.created_at.isoformat() if self.created_at else None
        } 