# Setup Instructions

## Backend Setup

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Set Up PostgreSQL Database

**Option A: Using PostgreSQL (Recommended for Production)**
1. Install PostgreSQL from https://www.postgresql.org/download/
2. Create a database:
   ```sql
   CREATE DATABASE sonyc_db;
   ```
3. Create `backend/.env` file:
   ```
   DATABASE_URL=postgresql://postgres:your_password@localhost:5432/sonyc_db
   JWT_SECRET_KEY=your-secret-key-change-in-production
   GOOGLE_API_KEY=your-google-api-key
   ```

**Option B: Using SQLite (For Development/Testing)**
If you don't have PostgreSQL set up, you can temporarily use SQLite by modifying `backend/app/database.py`:
```python
DATABASE_URL = "sqlite:///./sonyc.db"
```

### 3. Run the Backend Server
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The server will start at http://localhost:8000/

## Frontend Setup

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Configure Environment
Create `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Run the Frontend Server
```bash
cd frontend
npm run dev
```

The frontend will start at http://localhost:3000/

## Troubleshooting

### Database Connection Errors
If you see database connection errors:
- Ensure PostgreSQL is running
- Check that the DATABASE_URL in `.env` is correct
- Verify the database `sonyc_db` exists
- Check PostgreSQL is accepting connections on port 5432

### API Key Errors
- Set `GOOGLE_API_KEY` in `backend/.env` for RAG features to work
- Get your API key from https://makersuite.google.com/app/apikey

### Port Already in Use
- Backend uses port 8000 by default
- Frontend uses port 3000 by default
- Change ports if needed in the run commands






