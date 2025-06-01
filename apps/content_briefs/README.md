# Brief Builder

## Project Structure

```
agents/
briefs/
logs/
static/
tasks/
templates/
tests/
utils/
app.py
celery_app.py
config.py
prompts.py
routes.py
requirements.txt
Procfile
.env.example
```

## Setup

1. **Clone the repo**
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Copy and edit environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```
4. **Run the app**
   ```bash
   flask run
   # or
   python -m app
   ```
5. **Run Celery worker**
   ```bash
   celery -A app.celery worker --loglevel=info
   ```

## Usage
- Visit the app in your browser (default: http://localhost:5000)
- Enter a keyword and your website URL to generate a blog brief
- Download results as JSON, DOCX, or view in browser

## Testing
- Place tests in `tests/`
- Run with `pytest` or `python -m unittest discover tests`

## Notes
- All configuration is managed in `config.py` and loaded from environment variables.
- Add utility/helper functions to `utils/` as needed.
