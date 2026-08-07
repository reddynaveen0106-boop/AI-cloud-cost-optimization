import datetime
import json
import os
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

from logger import logger

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/cloud_cost_detective")

# Connection pool holder
_db_pool = None

# In-memory storage fallback if PostgreSQL server is not connected
_in_memory_analyses: List[Dict[str, Any]] = []
# Pre-seeded default user: demo@example.com / Password123!
_in_memory_users: List[Dict[str, Any]] = [
    {
        "id": 1,
        "email": "demo@example.com",
        "password_hash": "$2b$12$iWdncKBCKkJGjjch4g4hHe/6kjw8PDpFxBWKTPLXi0Gv6qFSDGs0.",
        "created_at": "2026-07-28T00:00:00Z"
    }
]

_user_id_counter: int = 2



async def create_user(email: str, password_hash: str) -> Dict[str, Any]:
    """
    Creates a new user record in PostgreSQL or in-memory fallback.
    """
    global _user_id_counter
    email_lower = email.strip().lower()
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if _db_pool:
        try:
            async with _db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO users (email, password_hash)
                    VALUES ($1, $2)
                    RETURNING id, email, password_hash, created_at;
                    """,
                    email_lower,
                    password_hash
                )
                user_dict = {
                    "id": row["id"],
                    "email": row["email"],
                    "password_hash": row["password_hash"],
                    "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"])
                }
                logger.info(f"Created user '{email_lower}' with ID {user_dict['id']} in PostgreSQL.")
                return user_dict
        except Exception as e:
            logger.error(f"Failed to create user in PostgreSQL: {str(e)}")
            raise e

    # In-memory fallback
    for u in _in_memory_users:
        if u["email"] == email_lower:
            raise ValueError(f"User with email '{email_lower}' already exists.")

    user_dict = {
        "id": _user_id_counter,
        "email": email_lower,
        "password_hash": password_hash,
        "created_at": created_at
    }
    _user_id_counter += 1
    _in_memory_users.append(user_dict)
    logger.info(f"Created user '{email_lower}' with ID {user_dict['id']} in memory fallback.")
    return user_dict


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves user by email address from PostgreSQL or in-memory fallback.
    """
    email_lower = email.strip().lower()
    if _db_pool:
        try:
            async with _db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT id, email, password_hash, created_at FROM users WHERE LOWER(email) = $1",
                    email_lower
                )
                if row:
                    return {
                        "id": row["id"],
                        "email": row["email"],
                        "password_hash": row["password_hash"],
                        "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"])
                    }
                return None
        except Exception as e:
            logger.error(f"Failed to fetch user from PostgreSQL: {str(e)}")

    # In-memory fallback
    for u in _in_memory_users:
        if u["email"] == email_lower:
            return u
    return None



async def init_db():
    """
    Initializes PostgreSQL database connection pool and creates 'users' and 'analyses' tables.
    Falls back gracefully if PostgreSQL server is unreachable.
    """
    global _db_pool
    db_url = os.getenv("DATABASE_URL", "").strip()

    if not db_url:
        logger.info("DATABASE_URL not set in environment. Operating with in-memory database fallback.")
        return

    try:
        import asyncpg
        logger.info(f"Connecting to PostgreSQL database...")
        _db_pool = await asyncpg.create_pool(db_url, timeout=5)

        async with _db_pool.acquire() as conn:
            # 1. Create users table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Create analyses table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id VARCHAR(255) PRIMARY KEY,
                    user_id INT REFERENCES users(id) ON DELETE SET NULL,
                    region VARCHAR(100) NOT NULL,
                    resources_scanned INT NOT NULL DEFAULT 0,
                    issues_found INT NOT NULL DEFAULT 0,
                    estimated_monthly_savings VARCHAR(100) NOT NULL DEFAULT '$0.00',
                    analysis_result JSONB NOT NULL,
                    status VARCHAR(50) NOT NULL DEFAULT 'completed',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)

        logger.info("PostgreSQL database tables 'users' and 'analyses' initialized successfully.")

    except Exception as e:
        logger.warning(f"Could not connect to PostgreSQL database ({str(e)}). Using in-memory history fallback.")
        _db_pool = None


async def save_analysis(
    analysis_id: str,
    region: str,
    resources_scanned: int,
    issues_found: int,
    estimated_monthly_savings: str,
    analysis_result: Dict[str, Any],
    status: str = "completed",
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Saves an analysis record to PostgreSQL 'analyses' table or in-memory fallback.
    """
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    record = {
        "id": analysis_id,
        "user_id": user_id,
        "region": region,
        "resources_scanned": resources_scanned,
        "issues_found": issues_found,
        "estimated_monthly_savings": estimated_monthly_savings,
        "analysis_result": analysis_result,
        "status": status,
        "created_at": created_at
    }

    if _db_pool:
        try:
            async with _db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO analyses (id, user_id, region, resources_scanned, issues_found, estimated_monthly_savings, analysis_result, status, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9)
                    ON CONFLICT (id) DO UPDATE SET
                        status = EXCLUDED.status,
                        analysis_result = EXCLUDED.analysis_result,
                        issues_found = EXCLUDED.issues_found,
                        estimated_monthly_savings = EXCLUDED.estimated_monthly_savings;
                    """,
                    analysis_id,
                    user_id,
                    region,
                    resources_scanned,
                    issues_found,
                    estimated_monthly_savings,
                    json.dumps(analysis_result),
                    status,
                    datetime.datetime.fromisoformat(created_at)
                )
            logger.info(f"Saved analysis '{analysis_id}' to PostgreSQL 'analyses' table.")
            return record
        except Exception as e:
            logger.error(f"Failed to insert analysis into PostgreSQL: {str(e)}")

    # In-memory fallback
    _in_memory_analyses.insert(0, record)
    logger.info(f"Saved analysis '{analysis_id}' to in-memory history fallback.")
    return record


async def get_user_analyses(user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Fetches analysis history records from PostgreSQL or in-memory fallback.
    """
    if _db_pool:
        try:
            async with _db_pool.acquire() as conn:
                if user_id is not None:
                    rows = await conn.fetch(
                        "SELECT id, user_id, region, resources_scanned, issues_found, estimated_monthly_savings, analysis_result, status, created_at FROM analyses WHERE user_id = $1 ORDER BY created_at DESC",
                        user_id
                    )
                else:
                    rows = await conn.fetch(
                        "SELECT id, user_id, region, resources_scanned, issues_found, estimated_monthly_savings, analysis_result, status, created_at FROM analyses ORDER BY created_at DESC"
                    )

                results = []
                for r in rows:
                    res_data = r["analysis_result"]
                    if isinstance(res_data, str):
                        res_data = json.loads(res_data)
                    results.append({
                        "id": r["id"],
                        "user_id": r["user_id"],
                        "region": r["region"],
                        "resources_scanned": r["resources_scanned"],
                        "issues_found": r["issues_found"],
                        "estimated_monthly_savings": r["estimated_monthly_savings"],
                        "analysis_result": res_data,
                        "status": r["status"],
                        "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"])
                    })
                return results
        except Exception as e:
            logger.error(f"Failed to query analyses from PostgreSQL: {str(e)}")

    # In-memory fallback
    if user_id is not None:
        return [a for a in _in_memory_analyses if a.get("user_id") == user_id]
    return _in_memory_analyses
