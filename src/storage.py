"""Storage module for saving and loading vacancy data."""

import sqlite3
import json
import csv
from typing import List, Dict
from pathlib import Path
from datetime import datetime


class VacancyStorage:
    """Storage handler for vacancy data."""
    
    def __init__(self, db_path: str):
        """
        Initialize storage with database path.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if we need migration (old schema without projects)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects'")
        needs_migration = cursor.fetchone() is None
        
        if needs_migration:
            print("Migrating database to new schema with projects...")
            
            # Backup old vacancies
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vacancies'")
            if cursor.fetchone():
                cursor.execute("ALTER TABLE vacancies RENAME TO vacancies_old")
                cursor.execute("ALTER TABLE skills RENAME TO skills_old")
        
        # Projects table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                query TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # Create default project if it doesn't exist
        cursor.execute('SELECT COUNT(*) FROM projects WHERE id = 1')
        if cursor.fetchone()[0] == 0:
            now = datetime.now().isoformat()
            cursor.execute(
                'INSERT INTO projects (id, name, query, created_at, updated_at) VALUES (?, ?, ?, ?, ?)',
                (1, 'Default Project', '', now, now)
            )
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vacancies (
                id TEXT,
                project_id INTEGER,
                name TEXT,
                url TEXT,
                published_at TEXT,
                created_at TEXT,
                company_name TEXT,
                company_url TEXT,
                area TEXT,
                experience TEXT,
                employment TEXT,
                schedule TEXT,
                salary_from INTEGER,
                salary_to INTEGER,
                salary_currency TEXT,
                salary_gross BOOLEAN,
                description TEXT,
                full_text TEXT,
                fetched_at TEXT,
                PRIMARY KEY (id, project_id),
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS skills (
                vacancy_id TEXT,
                project_id INTEGER,
                skill TEXT,
                FOREIGN KEY (vacancy_id, project_id) REFERENCES vacancies(id, project_id)
            )
        ''')
        
        # Migrate old data if needed
        if needs_migration:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vacancies_old'")
            if cursor.fetchone():
                print("Migrating old vacancies to Default Project...")
                
                # Copy vacancies
                cursor.execute('''
                    INSERT INTO vacancies 
                    SELECT id, 1 as project_id, name, url, published_at, created_at,
                           company_name, company_url, area, experience, employment, schedule,
                           salary_from, salary_to, salary_currency, salary_gross,
                           description, full_text, fetched_at
                    FROM vacancies_old
                ''')
                
                # Copy skills
                cursor.execute('''
                    INSERT INTO skills
                    SELECT vacancy_id, 1 as project_id, skill
                    FROM skills_old
                ''')
                
                # Drop old tables
                cursor.execute("DROP TABLE vacancies_old")
                cursor.execute("DROP TABLE skills_old")
                
                print("Migration completed!")
        
        conn.commit()
        conn.close()
    
    def save_vacancies(self, vacancies: List[Dict], project_id: int = 1):
        """
        Save vacancies to database for a specific project.
        
        Args:
            vacancies: List of parsed vacancy dictionaries
            project_id: ID of the project to save vacancies to
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        fetched_at = datetime.now().isoformat()
        
        for vacancy in vacancies:
            # Insert vacancy
            cursor.execute('''
                INSERT OR REPLACE INTO vacancies VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            ''', (
                vacancy.get('id'),
                project_id,
                vacancy.get('name'),
                vacancy.get('url'),
                vacancy.get('published_at'),
                vacancy.get('created_at'),
                vacancy.get('company_name'),
                vacancy.get('company_url'),
                vacancy.get('area'),
                vacancy.get('experience'),
                vacancy.get('employment'),
                vacancy.get('schedule'),
                vacancy.get('salary_from'),
                vacancy.get('salary_to'),
                vacancy.get('salary_currency'),
                vacancy.get('salary_gross'),
                vacancy.get('description'),
                vacancy.get('full_text'),
                fetched_at
            ))
            
            # Delete existing skills for this vacancy and project
            cursor.execute(
                'DELETE FROM skills WHERE vacancy_id = ? AND project_id = ?',
                (vacancy.get('id'), project_id)
            )
            
            # Insert skills
            for skill in vacancy.get('key_skills', []):
                cursor.execute(
                    'INSERT INTO skills VALUES (?, ?, ?)',
                    (vacancy.get('id'), project_id, skill)
                )
        
        conn.commit()
        conn.close()
        print(f"Saved {len(vacancies)} vacancies to project {project_id}")
    
    def load_vacancies(self, project_id: int = 1) -> List[Dict]:
        """
        Load vacancies for a specific project from database.
        
        Args:
            project_id: ID of the project to load vacancies from
            
        Returns:
            List of vacancy dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM vacancies WHERE project_id = ?', (project_id,))
        rows = cursor.fetchall()
        
        vacancies = []
        for row in rows:
            vacancy = dict(row)
            
            # Load skills for this vacancy and project
            cursor.execute(
                'SELECT skill FROM skills WHERE vacancy_id = ? AND project_id = ?',
                (vacancy['id'], project_id)
            )
            skills = [skill[0] for skill in cursor.fetchall()]
            vacancy['key_skills'] = skills
            
            vacancies.append(vacancy)
        
        conn.close()
        return vacancies
    
    # Project management methods
    def create_project(self, name: str, query: str = '') -> int:
        """Create a new project and return its ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        cursor.execute(
            'INSERT INTO projects (name, query, created_at, updated_at) VALUES (?, ?, ?, ?)',
            (name, query, now, now)
        )
        project_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return project_id
    
    def get_projects(self) -> List[Dict]:
        """Get all projects."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT p.*, COUNT(DISTINCT v.id) as vacancy_count
            FROM projects p
            LEFT JOIN vacancies v ON p.id = v.project_id
            GROUP BY p.id
            ORDER BY p.updated_at DESC
        ''')
        projects = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return projects
    
    def get_project(self, project_id: int) -> Dict:
        """Get a single project by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row is None:
            return None
        return dict(row)
    
    def update_project(self, project_id: int, name: str = None, query: str = None):
        """Update project details."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if name is not None:
            updates.append('name = ?')
            params.append(name)
        if query is not None:
            updates.append('query = ?')
            params.append(query)
        
        updates.append('updated_at = ?')
        params.append(datetime.now().isoformat())
        params.append(project_id)
        
        cursor.execute(
            f'UPDATE projects SET {', '.join(updates)} WHERE id = ?',
            params
        )
        
        conn.commit()
        conn.close()
    
    def delete_project(self, project_id: int):
        """Delete a project and all its vacancies."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Delete skills
        cursor.execute('DELETE FROM skills WHERE project_id = ?', (project_id,))
        # Delete vacancies
        cursor.execute('DELETE FROM vacancies WHERE project_id = ?', (project_id,))
        # Delete project
        cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))
        
        conn.commit()
        conn.close()
    
    def export_to_json(self, vacancies: List[Dict], output_path: str):
        """
        Export vacancies to JSON file.
        
        Args:
            vacancies: List of vacancy dictionaries
            output_path: Path to output JSON file
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(vacancies, f, ensure_ascii=False, indent=2)
        
        print(f"Exported {len(vacancies)} vacancies to {output_path}")
    
    def export_to_csv(self, vacancies: List[Dict], output_path: str):
        """
        Export vacancies to CSV file.
        
        Args:
            vacancies: List of vacancy dictionaries
            output_path: Path to output CSV file
        """
        if not vacancies:
            print("No vacancies to export")
            return
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Define CSV columns
        columns = [
            'id', 'name', 'company_name', 'area', 'experience',
            'salary_from', 'salary_to', 'salary_currency',
            'url', 'published_at'
        ]
        
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(vacancies)
        
        print(f"Exported {len(vacancies)} vacancies to {output_path}")
    
    def export_report(self, report: Dict, output_path: str):
        """
        Export analysis report to JSON file.
        
        Args:
            report: Analysis report dictionary
            output_path: Path to output JSON file
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"Exported report to {output_path}")
