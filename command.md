1. Start the PostgreSQL service
brew services start postgresql@14

2. Start Redis
brew services start redis

3. Navigate to Backend
cd backend

4. Activate Python Virtual Environment
source ../venv/bin/activate

5. Install Dependencies (only once prefered)
pip install -r requirements.txt

6. Start FastAPI Server (In terminal 1)
uvicorn app.main:app --reload

7. Start the Celery worker (In terminal 2)
cd backend
source ../venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info --pool=solo 

8. Run Pipeline (In terminal 3)
cd backend
source ../venv/bin/activate
python3 process_recording.py --file data/recordings/call_01.wav
