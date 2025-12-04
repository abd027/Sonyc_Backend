# PostgreSQL Docker Setup Guide

## Quick Start

### 1. Start PostgreSQL Container

Make sure Docker Desktop is running, then execute:

```bash
cd backend
docker-compose up -d
```

This will:
- Pull the PostgreSQL 15 Alpine image (if not already present)
- Create a container named `sonyc_postgres`
- Start PostgreSQL on port 5432
- Create a database named `sonyc_db`
- Set up persistent storage

### 2. Verify Container is Running

```bash
docker-compose ps
```

You should see the `sonyc_postgres` container running.

### 3. Check Database Connection

```bash
# Test connection from command line
docker exec -it sonyc_postgres psql -U postgres -d sonyc_db -c "SELECT version();"
```

### 4. Update .env File (if needed)

The default `.env` file already has the correct DATABASE_URL:
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sonyc_db
```

This matches the Docker container configuration.

## Container Management

### Start Container
```bash
docker-compose up -d
```

### Stop Container
```bash
docker-compose stop
```

### Stop and Remove Container
```bash
docker-compose down
```

### Stop and Remove Container + Data (⚠️ This deletes all data!)
```bash
docker-compose down -v
```

### View Logs
```bash
docker-compose logs -f postgres
```

### Access PostgreSQL CLI
```bash
docker exec -it sonyc_postgres psql -U postgres -d sonyc_db
```

## Database Credentials

- **Host**: localhost
- **Port**: 5432
- **Database**: sonyc_db
- **Username**: postgres
- **Password**: postgres

## Troubleshooting

### Port Already in Use
If port 5432 is already in use, you can change it in `docker-compose.yml`:
```yaml
ports:
  - "5433:5432"  # Use 5433 on host instead
```
Then update `.env`:
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/sonyc_db
```

### Container Won't Start
1. Check Docker Desktop is running
2. Check logs: `docker-compose logs postgres`
3. Verify port 5432 is not in use by another service

### Reset Database
```bash
docker-compose down -v
docker-compose up -d
```

## Next Steps

Once PostgreSQL is running:

1. **Start the backend server**:
   ```bash
   cd backend
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Verify database tables are created**:
   The backend will automatically create tables on startup if they don't exist.

3. **Test the API**:
   - Visit http://localhost:8000/docs
   - Try creating a user via `/auth/signup`
   - Verify data persists in the database

## Production Notes

⚠️ **For production**, change the default password:
1. Update `POSTGRES_PASSWORD` in `docker-compose.yml`
2. Update `DATABASE_URL` in `.env` to match
3. Use environment variables or secrets management for sensitive data






