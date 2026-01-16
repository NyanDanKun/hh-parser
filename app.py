"""Flask web application for HH.ru Parser."""

from flask import Flask, render_template, jsonify, request, send_file
from pathlib import Path
import yaml
import sys
import threading
import json
from datetime import datetime
import requests

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from api_client import HHAPIClient
from parser import VacancyParser
from analyzer import VacancyAnalyzer
from storage import VacancyStorage

app = Flask(__name__)

# Global state
collection_status = {
    'running': False,
    'progress': 0,
    'total': 0,
    'current_page': 0,
    'message': ''
}

current_project_id = 1  # Default project


def apply_salary_filters(vacancies, min_salary=None, hide_empty=False):
    """Apply salary-based filters to vacancies list."""
    filtered = vacancies
    
    if hide_empty:
        # Remove vacancies without salary information
        filtered = [
            v for v in filtered
            if v.get('salary_from') is not None or v.get('salary_to') is not None
        ]
    
    if min_salary is not None:
        # Keep only vacancies with salary >= min_salary
        filtered = [
            v for v in filtered
            if (v.get('salary_from') and v['salary_from'] >= min_salary) or
               (v.get('salary_to') and v['salary_to'] >= min_salary)
        ]
    
    return filtered


def load_config():
    """Load configuration from YAML."""
    config_path = Path(__file__).parent / 'config' / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@app.route('/')
def index():
    """Render main dashboard."""
    return render_template('index.html')


# Project management endpoints
@app.route('/api/projects', methods=['GET'])
def get_projects_list():
    """Get all projects."""
    try:
        config = load_config()
        storage = VacancyStorage(config['storage']['database'])
        projects = storage.get_projects()
        
        return jsonify({
            'success': True,
            'projects': projects,
            'current_project_id': current_project_id
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/projects', methods=['POST'])
def create_new_project():
    """Create a new project."""
    try:
        data = request.get_json()
        name = data.get('name', 'New Project')
        query = data.get('query', '')
        
        config = load_config()
        storage = VacancyStorage(config['storage']['database'])
        project_id = storage.create_project(name, query)
        
        return jsonify({
            'success': True,
            'project_id': project_id
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/projects/<int:project_id>/switch', methods=['POST'])
def switch_project(project_id):
    """Switch current project."""
    global current_project_id
    current_project_id = project_id
    
    return jsonify({
        'success': True,
        'current_project_id': current_project_id
    })


@app.route('/api/projects/<int:project_id>', methods=['PUT'])
def update_project_details(project_id):
    """Update project details."""
    try:
        data = request.get_json()
        name = data.get('name')
        query = data.get('query')
        
        config = load_config()
        storage = VacancyStorage(config['storage']['database'])
        storage.update_project(project_id, name=name, query=query)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
def delete_project_endpoint(project_id):
    """Delete a project."""
    global current_project_id
    
    try:
        # Don't allow deleting the default project
        if project_id == 1:
            return jsonify({
                'success': False,
                'error': 'Cannot delete the default project'
            })
        
        config = load_config()
        storage = VacancyStorage(config['storage']['database'])
        storage.delete_project(project_id)
        
        # Switch to default project if current was deleted
        if current_project_id == project_id:
            current_project_id = 1
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/stats')
def get_stats():
    """Get current statistics."""
    try:
        config = load_config()
        storage = VacancyStorage(config['storage']['database'])
        
        # Get filter parameters
        min_salary = request.args.get('min_salary', type=int)
        hide_empty = request.args.get('hide_empty', 'false').lower() == 'true'
        
        vacancies = storage.load_vacancies(current_project_id)
        
        if not vacancies:
            return jsonify({
                'success': True,
                'total_vacancies': 0,
                'report': None
            })
        
        # Apply filters
        filtered_vacancies = apply_salary_filters(vacancies, min_salary, hide_empty)
        
        if not filtered_vacancies:
            return jsonify({
                'success': True,
                'total_vacancies': 0,
                'report': None,
                'filtered': True,
                'original_count': len(vacancies)
            })
        
        # Analyze filtered vacancies
        analyzer = VacancyAnalyzer(config)
        report = analyzer.create_report(filtered_vacancies)
        
        return jsonify({
            'success': True,
            'total_vacancies': len(filtered_vacancies),
            'report': report,
            'filtered': min_salary is not None or hide_empty,
            'original_count': len(vacancies)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/vacancies')
def get_vacancies():
    """Get vacancies list with optional filtering."""
    try:
        config = load_config()
        storage = VacancyStorage(config['storage']['database'])
        
        # Get filter parameters
        min_salary = request.args.get('min_salary', type=int)
        hide_empty = request.args.get('hide_empty', 'false').lower() == 'true'
        
        # Load vacancies for current project
        vacancies = storage.load_vacancies(current_project_id)
        
        # Apply filters
        filtered_vacancies = apply_salary_filters(vacancies, min_salary, hide_empty)
            
        # Pagination
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        start = (page - 1) * per_page
        end = start + per_page
        
        paginated = filtered_vacancies[start:end]
        
        return jsonify({
            'success': True,
            'vacancies': paginated,
            'total': len(filtered_vacancies),
            'page': page,
            'per_page': per_page,
            'pages': (len(filtered_vacancies) + per_page - 1) // per_page,
            'filtered': min_salary is not None or hide_empty,
            'original_count': len(vacancies)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/collect', methods=['POST'])
def start_collection():
    """Start vacancy collection."""
    global collection_status, current_project_id
    
    if collection_status['running']:
        return jsonify({
            'success': False,
            'message': 'Collection already running'
        })
    
    params = request.get_json() or {}
    query = params.get('query', 'руководитель отдела маркетинга')
    area = params.get('area')
    max_pages = params.get('max_pages', 10)
    per_page = params.get('per_page', 20)
    experience = params.get('experience')
    
    # Project handling
    create_new = params.get('create_new_project', False)
    project_name = params.get('project_name', query)
    target_project_id = current_project_id
    
    def collect():
        global collection_status, current_project_id
        nonlocal target_project_id
        
        collection_status['running'] = True
        collection_status['progress'] = 0
        collection_status['message'] = 'Starting collection...'
        
        try:
            config = load_config()
            api_client = HHAPIClient(config)
            storage = VacancyStorage(config['storage']['database'])
            
            # Create new project if requested
            if create_new:
                target_project_id = storage.create_project(project_name, query)
                current_project_id = target_project_id  # Switch to new project
                collection_status['message'] = f'Created new project: {project_name}'
                print(f"Created new project ID: {target_project_id}")
            
            collection_status['message'] = f'Collecting vacancies for "{query}"...'
            raw_vacancies = api_client.collect_all_vacancies(
                text=query,
                area=int(area) if area else None,
                max_pages=max_pages,
                per_page=per_page,
                experience=experience,
                employment=None,
                with_details=True
            )
            
            print(f"Collected {len(raw_vacancies)} raw vacancies")
            
            collection_status['message'] = 'Parsing data...'
            parsed_vacancies = VacancyParser.parse_multiple(raw_vacancies)
            print(f"Parsed {len(parsed_vacancies)} vacancies")
            
            collection_status['message'] = f'Saving to database (project {target_project_id})...'
            print(f"Saving to project_id={target_project_id}")
            storage.save_vacancies(parsed_vacancies, target_project_id)
            print(f"Save completed!")
            
            collection_status['progress'] = 100
            collection_status['message'] = f'Completed! Collected {len(parsed_vacancies)} vacancies'
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"ERROR in collection: {error_details}")
            collection_status['message'] = f'Error: {str(e)}'
        finally:
            collection_status['running'] = False
    
    # Start collection in background
    thread = threading.Thread(target=collect)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': 'Collection started'
    })


@app.route('/api/status')
def get_status():
    """Get collection status."""
    return jsonify(collection_status)


@app.route('/api/export/<format>')
def export_data(format):
    """Export data in specified format."""
    try:
        config = load_config()
        storage = VacancyStorage(config['storage']['database'])
        
        # Load vacancies for current project
        vacancies = storage.load_vacancies(current_project_id)
        
        if format == 'json':
            export_path = storage.export_json(vacancies)
            return send_file(export_path, as_attachment=True)
        elif format == 'csv':
            export_path = storage.export_csv(vacancies)
            return send_file(export_path, as_attachment=True)
        else:
            return jsonify({
                'success': False,
                'error': 'Unsupported format'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
