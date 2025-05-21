from app import create_app
from rq import Worker, Queue, Connection
import redis

# Create the Flask app and push the app context
app = create_app()
app.app_context().push()

listen = ['topic_competitors']
redis_url = 'redis://host.docker.internal:6379/0'
conn = redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(list(map(Queue, listen)))
        worker.work()