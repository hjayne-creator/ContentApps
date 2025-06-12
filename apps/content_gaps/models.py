from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint, JSON, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

db = SQLAlchemy()

class Project(db.Model):
    __tablename__ = 'content_gaps_projects'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    topic_trees = relationship('TopicTree', backref='project', lazy=True, cascade='all, delete-orphan')
    sites = relationship('Site', backref='project', lazy=True, cascade='all, delete-orphan')
    jobs = relationship('ContentGapsJob', backref='project', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'project_name': self.project_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ContentGapsJob(db.Model):
    __tablename__ = 'content_gaps_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String(36), nullable=False)
    job_id = db.Column(db.String(36), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    error_message = db.Column(db.Text)
    compare_url = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('project_id', 'job_id', name='uix_project_job'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'job_id': self.job_id,
            'status': self.status,
            'error_message': self.error_message,
            'compare_url': self.compare_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class TopicTree(db.Model):
    __tablename__ = 'content_gaps_topic_trees'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = db.Column(db.String(36), nullable=False)
    tree_name = db.Column(db.String(255), nullable=False)
    root_topic = db.Column(db.String(255), nullable=False)
    tree_data = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_topic_trees_project_id', 'project_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'tree_name': self.tree_name,
            'root_topic': self.root_topic,
            'tree': self.tree_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Site(db.Model):
    __tablename__ = 'content_gaps_sites'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = db.Column(db.String(36), nullable=False)
    label = db.Column(db.String(255), nullable=False)
    is_my_site = db.Column(db.Boolean, default=False)
    pages = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_sites_project_id', 'project_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'label': self.label,
            'is_my_site': self.is_my_site,
            'pages': self.pages,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Match(db.Model):
    __tablename__ = 'content_gaps_matches'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String(36), nullable=False)
    tree_id = db.Column(db.String(36), nullable=False)
    site_id = db.Column(db.String(36), nullable=False)
    page_index = db.Column(db.Integer, nullable=False)
    matched_topics = db.Column(db.JSON, nullable=False)
    similarity_scores = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_matches_project_tree', 'project_id', 'tree_id'),
        db.Index('idx_matches_site', 'site_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'tree_id': self.tree_id,
            'site_id': self.site_id,
            'page_index': self.page_index,
            'matched_topics': self.matched_topics,
            'similarity_scores': self.similarity_scores,
            'created_at': self.created_at.isoformat() if self.created_at else None
        } 