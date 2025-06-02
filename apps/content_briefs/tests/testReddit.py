import praw

# Initialize Reddit instance
reddit = praw.Reddit(
client_id='mw9sfMh4aP-9Mr-4o5V5gg',
client_secret='IyXDezuUvOZ2d-t76K38fEDJO02d_g',
user_agent='AgentBugs',
username='TenderTuck',
password='Housty70_reddit!'
)

# Fetching the top posts from the Python subreddit
subreddit = reddit.subreddit('Python')
for post in subreddit.top(limit=5):
    print(f"Title: {post.title}, Score: {post.score}")