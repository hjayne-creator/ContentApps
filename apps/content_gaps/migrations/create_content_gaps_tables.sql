-- Create projects table
CREATE TABLE IF NOT EXISTS content_gaps_projects (
    id UUID PRIMARY KEY,
    project_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create topic trees table
CREATE TABLE IF NOT EXISTS content_gaps_topic_trees (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES content_gaps_projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    tree_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, name)
);

-- Create sites table
CREATE TABLE IF NOT EXISTS content_gaps_sites (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES content_gaps_projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    content JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, name)
);

-- Create matches table
CREATE TABLE IF NOT EXISTS content_gaps_matches (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES content_gaps_projects(id) ON DELETE CASCADE,
    topic_tree_id UUID NOT NULL REFERENCES content_gaps_topic_trees(id) ON DELETE CASCADE,
    site_id UUID NOT NULL REFERENCES content_gaps_sites(id) ON DELETE CASCADE,
    topic_id VARCHAR(255) NOT NULL,
    topic_name TEXT NOT NULL,
    site_url TEXT NOT NULL,
    site_name VARCHAR(255) NOT NULL,
    match_score FLOAT NOT NULL,
    match_details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, topic_tree_id, site_id, topic_id)
);

-- Create jobs table
CREATE TABLE IF NOT EXISTS content_gaps_jobs (
    id SERIAL PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES content_gaps_projects(id) ON DELETE CASCADE,
    job_id UUID NOT NULL,
    status VARCHAR(50) NOT NULL,
    error_message TEXT,
    compare_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, job_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_content_gaps_topic_trees_project_id ON content_gaps_topic_trees(project_id);
CREATE INDEX IF NOT EXISTS idx_content_gaps_sites_project_id ON content_gaps_sites(project_id);
CREATE INDEX IF NOT EXISTS idx_content_gaps_matches_project_id ON content_gaps_matches(project_id);
CREATE INDEX IF NOT EXISTS idx_content_gaps_matches_topic_tree_id ON content_gaps_matches(topic_tree_id);
CREATE INDEX IF NOT EXISTS idx_content_gaps_matches_site_id ON content_gaps_matches(site_id);
CREATE INDEX IF NOT EXISTS idx_content_gaps_jobs_project_id ON content_gaps_jobs(project_id);
CREATE INDEX IF NOT EXISTS idx_content_gaps_jobs_job_id ON content_gaps_jobs(job_id); 