"""
Database module for LinkedIn Job Monitor

Handles job tracking, deduplication, and persistence using SQLite.
"""

import sqlite3
import hashlib
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

# Setup logging
logger = logging.getLogger(__name__)

@dataclass
class Job:
    """Data class representing a job posting."""
    id: Optional[int] = None
    title: str = ""
    company: str = ""
    location: str = ""
    linkedin_url: str = ""
    job_hash: str = ""
    first_seen: datetime = None
    last_seen: datetime = None
    notified: bool = False
    
    # Job data fields
    pay_range_min: Optional[int] = None
    pay_range_max: Optional[int] = None
    pay_range_text: str = ""
    pay_type: str = "yearly"  # "yearly", "hourly", "monthly"
    location_type: str = ""   # "Remote", "Hybrid", "On-site"
    city: str = ""            # "NYC", "LA", "SF", "SD", "Remote"
    posted_time: str = ""     # Original text like "2 hours ago"
    posted_hours_ago: Optional[int] = None
    linkedin_job_id: str = ""
    company_career_url: str = ""
    
    def __post_init__(self):
        """Initialize computed fields after object creation."""
        if self.first_seen is None:
            self.first_seen = datetime.now(timezone.utc)
        if self.last_seen is None:
            self.last_seen = datetime.now(timezone.utc)
        if not self.job_hash and self.title and self.company:
            self.job_hash = self._generate_hash()
    
    def _generate_hash(self) -> str:
        """Generate a unique hash for this job based on title and company."""
        # Create a unique identifier from title, company, and location
        content = f"{self.title.lower().strip()}|{self.company.lower().strip()}|{self.location.lower().strip()}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    

class JobDatabase:
    """Database manager for job tracking."""
    
    def __init__(self, db_path: str):
        """Initialize database connection and create tables if needed."""
        self.db_path = db_path
        
        # Create data directory if it doesn't exist
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        self._create_tables()
    
    def _row_to_job(self, row) -> Job:
        """Convert database row to Job object."""
        return Job(
            id=row['id'],
            title=row['title'],
            company=row['company'],
            location=row['location'],
            linkedin_url=row['linkedin_url'],
            job_hash=row['job_hash'],
            first_seen=datetime.fromisoformat(row['first_seen']),
            last_seen=datetime.fromisoformat(row['last_seen']),
            notified=bool(row['notified']),
            pay_range_min=row['pay_range_min'],
            pay_range_max=row['pay_range_max'],
            pay_range_text=row['pay_range_text'] or '',
            pay_type=row['pay_type'] or 'yearly',
            location_type=row['location_type'] or '',
            city=row['city'] or '',
            posted_time=row['posted_time'] or '',
            posted_hours_ago=row['posted_hours_ago'],
            linkedin_job_id=row['linkedin_job_id'] or '',
            company_career_url=row['company_career_url'] or ''
        )
    
    def _create_tables(self):
        """Create database tables if they don't exist."""
        create_jobs_table = """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT NOT NULL,
            linkedin_url TEXT,
            job_hash TEXT UNIQUE NOT NULL,
            first_seen TIMESTAMP NOT NULL,
            last_seen TIMESTAMP NOT NULL,
            notified BOOLEAN DEFAULT FALSE,
            
            -- Job data fields
            pay_range_min INTEGER,
            pay_range_max INTEGER,
            pay_range_text TEXT,
            pay_type TEXT DEFAULT 'yearly',
            location_type TEXT,
            city TEXT,
            posted_time TEXT,
            posted_hours_ago INTEGER,
            linkedin_job_id TEXT,
            company_career_url TEXT,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        create_search_history_table = """
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT NOT NULL,
            search_url TEXT NOT NULL,
            screenshot_count INTEGER DEFAULT 0,
            jobs_found INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            success BOOLEAN DEFAULT TRUE,
            error_message TEXT
        );
        """
        
        create_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_job_hash ON jobs(job_hash);",
            "CREATE INDEX IF NOT EXISTS idx_first_seen ON jobs(first_seen);",
            "CREATE INDEX IF NOT EXISTS idx_notified ON jobs(notified);",
            "CREATE INDEX IF NOT EXISTS idx_city ON search_history(city);",
            "CREATE INDEX IF NOT EXISTS idx_timestamp ON search_history(timestamp);"
        ]
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute(create_jobs_table)
            cursor.execute(create_search_history_table)
            
            for index_sql in create_indexes:
                cursor.execute(index_sql)
            
            self.conn.commit()
            logger.info("Database initialized successfully")
            
        except sqlite3.Error as e:
            logger.error(f"Error creating database tables: {e}")
            self.conn.rollback()
        finally:
            cursor.close()
    
    def add_job(self, job: Job) -> bool:
        """
        Add a new job to the database.
        
        Args:
            job: Job instance to add
            
        Returns:
            True if job was added (new), False if job already exists
        """
        cursor = self.conn.cursor()
        
        try:
            # Check if job already exists
            existing_job = self.get_job_by_hash(job.job_hash)
            
            if existing_job:
                # Update last_seen timestamp
                cursor.execute(
                    "UPDATE jobs SET last_seen = ? WHERE job_hash = ?",
                    (datetime.now(timezone.utc), job.job_hash)
                )
                self.conn.commit()
                return False  # Job already existed
            
            # Insert new job
            cursor.execute("""
                INSERT INTO jobs (
                    title, company, location, linkedin_url, job_hash,
                    first_seen, last_seen, notified,
                    pay_range_min, pay_range_max, pay_range_text, pay_type,
                    location_type, city, posted_time, posted_hours_ago,
                    linkedin_job_id, company_career_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.title, job.company, job.location, job.linkedin_url,
                job.job_hash, job.first_seen, job.last_seen, job.notified,
                job.pay_range_min, job.pay_range_max, job.pay_range_text, job.pay_type,
                job.location_type, job.city, job.posted_time, job.posted_hours_ago,
                job.linkedin_job_id, job.company_career_url
            ))
            
            self.conn.commit()
            return True  # New job added
            
        except sqlite3.Error as e:
            logger.error(f"Error adding job: {e}")
            self.conn.rollback()
            return False
        finally:
            cursor.close()
    
    def get_job_by_hash(self, job_hash: str) -> Optional[Job]:
        """Get a job by its hash."""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM jobs WHERE job_hash = ?", (job_hash,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_job(row)
            return None
            
        except sqlite3.Error as e:
            logger.error(f"Error getting job by hash: {e}")
            return None
        finally:
            cursor.close()
    
    def get_recent_jobs(self, hours: int = 24, limit: int = 50) -> List[Job]:
        """Get jobs found in the last N hours."""
        cursor = self.conn.cursor()
        
        try:
            cutoff_time = datetime.now(timezone.utc).replace(
                hour=datetime.now(timezone.utc).hour - hours
            )
            
            cursor.execute("""
                SELECT * FROM jobs 
                WHERE first_seen > ? 
                ORDER BY first_seen DESC 
                LIMIT ?
            """, (cutoff_time, limit))
            
            jobs = []
            for row in cursor.fetchall():
                jobs.append(self._row_to_job(row))
            
            return jobs
            
        except sqlite3.Error as e:
            logger.error(f"Error getting recent jobs: {e}")
            return []
        finally:
            cursor.close()
    
    def mark_job_notified(self, job_hash: str) -> bool:
        """Mark a job as having been notified."""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE jobs SET notified = TRUE WHERE job_hash = ?",
                (job_hash,)
            )
            self.conn.commit()
            return cursor.rowcount > 0
            
        except sqlite3.Error as e:
            logger.error(f"Error marking job as notified: {e}")
            self.conn.rollback()
            return False
        finally:
            cursor.close()
    
    def get_unnotified_jobs(self) -> List[Job]:
        """Get all jobs that haven't been notified yet."""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM jobs WHERE notified = FALSE ORDER BY first_seen DESC")
            
            jobs = []
            for row in cursor.fetchall():
                jobs.append(self._row_to_job(row))
            
            return jobs
            
        except sqlite3.Error as e:
            logger.error(f"Error getting unnotified jobs: {e}")
            return []
        finally:
            cursor.close()
    
    def log_search(self, city: str, search_url: str, screenshot_count: int = 0, 
                   jobs_found: int = 0, success: bool = True, error_message: str = None):
        """Log a search attempt to the search history."""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO search_history (
                    city, search_url, screenshot_count, jobs_found, success, error_message
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (city, search_url, screenshot_count, jobs_found, success, error_message))
            
            self.conn.commit()
            
        except sqlite3.Error as e:
            logger.error(f"Error logging search: {e}")
            self.conn.rollback()
        finally:
            cursor.close()
    
    def get_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        cursor = self.conn.cursor()
        
        try:
            stats = {}
            
            # Total jobs
            cursor.execute("SELECT COUNT(*) as count FROM jobs")
            stats['total_jobs'] = cursor.fetchone()['count']
            
            # Jobs today
            today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            cursor.execute("SELECT COUNT(*) as count FROM jobs WHERE first_seen >= ?", (today,))
            stats['jobs_today'] = cursor.fetchone()['count']
            
            # Unnotified jobs
            cursor.execute("SELECT COUNT(*) as count FROM jobs WHERE notified = FALSE")
            stats['unnotified_jobs'] = cursor.fetchone()['count']
            
            # Total searches
            cursor.execute("SELECT COUNT(*) as count FROM search_history")
            stats['total_searches'] = cursor.fetchone()['count']
            
            # Successful searches today
            cursor.execute("""
                SELECT COUNT(*) as count FROM search_history 
                WHERE timestamp >= ? AND success = TRUE
            """, (today,))
            stats['successful_searches_today'] = cursor.fetchone()['count']
            
            return stats
            
        except sqlite3.Error as e:
            logger.error(f"Error getting stats: {e}")
            return {}
        finally:
            cursor.close()
    
    def cleanup_old_jobs(self, days_old: int = 7) -> int:
        """
        Delete jobs older than specified days.
        
        Args:
            days_old: Number of days after which to delete jobs (default 7)
            
        Returns:
            Number of jobs deleted
        """
        cursor = self.conn.cursor()
        
        try:
            # Calculate cutoff date
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
            
            # First, count how many jobs will be deleted
            cursor.execute("SELECT COUNT(*) FROM jobs WHERE first_seen < ?", (cutoff_date,))
            count_to_delete = cursor.fetchone()[0]
            
            if count_to_delete > 0:
                # Delete old jobs
                cursor.execute("DELETE FROM jobs WHERE first_seen < ?", (cutoff_date,))
                
                # Also clean up old search logs
                cursor.execute("DELETE FROM search_logs WHERE search_time < ?", (cutoff_date,))
                
                self.conn.commit()
                logger.info(f"🗑️ Cleaned up {count_to_delete} jobs older than {days_old} days")
            else:
                logger.debug(f"No jobs older than {days_old} days to clean up")
            
            return count_to_delete
            
        except sqlite3.Error as e:
            logger.error(f"Error during database cleanup: {e}")
            self.conn.rollback()
            return 0
        finally:
            cursor.close()
    
    def get_database_size_info(self) -> Dict:
        """Get database size information."""
        cursor = self.conn.cursor()
        
        try:
            # Get job count
            cursor.execute("SELECT COUNT(*) FROM jobs")
            job_count = cursor.fetchone()[0]
            
            # Get oldest and newest jobs
            cursor.execute("SELECT MIN(first_seen), MAX(first_seen) FROM jobs")
            result = cursor.fetchone()
            oldest_job = result[0]
            newest_job = result[1]
            
            # Get database file size
            import os
            db_size = 0
            if os.path.exists(self.db_path):
                db_size = os.path.getsize(self.db_path)
            
            return {
                'job_count': job_count,
                'oldest_job': oldest_job,
                'newest_job': newest_job,
                'database_size_bytes': db_size,
                'database_size_mb': round(db_size / (1024 * 1024), 2)
            }
            
        except sqlite3.Error as e:
            logger.error(f"Error getting database info: {e}")
            return {'error': str(e)}
        finally:
            cursor.close()
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()