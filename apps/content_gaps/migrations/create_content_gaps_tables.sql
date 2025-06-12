-- Create content_gaps_topic_trees table
CREATE TABLE IF NOT EXISTS content_gaps_topic_trees (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    tree_name VARCHAR(255) NOT NULL,
    root_topic VARCHAR(255) NOT NULL,
    tree_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_topic_trees_project_id ON content_gaps_topic_trees(project_id);

-- Create content_gaps_sites table
CREATE TABLE IF NOT EXISTS content_gaps_sites (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    label VARCHAR(255) NOT NULL,
    is_my_site BOOLEAN DEFAULT FALSE,
    pages JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sites_project_id ON content_gaps_sites(project_id);

-- Create content_gaps_matches table
CREATE TABLE IF NOT EXISTS content_gaps_matches (
    id SERIAL PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    tree_id VARCHAR(36) NOT NULL,
    site_id VARCHAR(36) NOT NULL,
    page_index INTEGER NOT NULL,
    matched_topics JSONB NOT NULL,
    similarity_scores JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_matches_project_tree ON content_gaps_matches(project_id, tree_id);
CREATE INDEX IF NOT EXISTS idx_matches_site ON content_gaps_matches(site_id); 