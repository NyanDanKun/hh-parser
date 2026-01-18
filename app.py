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
sys.path.insert(0, str(Path(__file__).parent / "src"))

from api_client import HHAPIClient
from parser import VacancyParser
from analyzer import VacancyAnalyzer
from storage import VacancyStorage

app = Flask(__name__)

# Global state
collection_status = {
    "running": False,
    "progress": 0,
    "total": 0,
    "current_page": 0,
    "message": "",
}

current_project_id = 1  # Default project


def apply_filters(
    vacancies,
    min_salary=None,
    max_salary=None,
    hide_empty=False,
    include_keywords=None,
    exclude_keywords=None,
    search_in=None,
):
    """
    Apply filters to vacancies list.

    Args:
        vacancies: List of vacancy dictionaries
        min_salary: Minimum salary filter
        max_salary: Maximum salary filter
        hide_empty: Hide vacancies without salary
        include_keywords: List of keywords that MUST be present (AND logic)
        exclude_keywords: List of keywords that MUST NOT be present
        search_in: List of fields to search in ['name', 'description', 'skills', 'full_text']
                   Default: ['full_text'] (searches everywhere)

    Returns:
        Filtered list of vacancies
    """
    filtered = vacancies

    # Salary filters
    if hide_empty:
        filtered = [
            v
            for v in filtered
            if v.get("salary_from") is not None or v.get("salary_to") is not None
        ]

    if min_salary is not None:
        filtered = [
            v
            for v in filtered
            if (v.get("salary_from") and v["salary_from"] >= min_salary)
            or (v.get("salary_to") and v["salary_to"] >= min_salary)
        ]

    if max_salary is not None:
        filtered = [
            v
            for v in filtered
            if (v.get("salary_from") and v["salary_from"] <= max_salary)
            or (v.get("salary_to") and v["salary_to"] <= max_salary)
            or (v.get("salary_from") is None and v.get("salary_to") is None)
        ]

    # Keyword filters
    if include_keywords or exclude_keywords:
        # Default search fields
        if not search_in:
            search_in = ["full_text"]

        def get_searchable_text(vacancy):
            """Get combined text from specified fields."""
            texts = []
            for field in search_in:
                if field == "name":
                    texts.append(vacancy.get("name", ""))
                elif field == "description":
                    texts.append(vacancy.get("description", ""))
                elif field == "skills":
                    skills = vacancy.get("key_skills", [])
                    texts.append(
                        " ".join(skills) if isinstance(skills, list) else str(skills)
                    )
                elif field == "full_text":
                    texts.append(vacancy.get("full_text", ""))
            return " ".join(texts).lower()

        def matches_include(vacancy, keywords):
            """Check if vacancy contains ALL include keywords."""
            if not keywords:
                return True
            text = get_searchable_text(vacancy)
            return all(kw.lower() in text for kw in keywords)

        def matches_exclude(vacancy, keywords):
            """Check if vacancy contains NONE of exclude keywords."""
            if not keywords:
                return True
            text = get_searchable_text(vacancy)
            return not any(kw.lower() in text for kw in keywords)

        # Apply keyword filters
        if include_keywords:
            filtered = [v for v in filtered if matches_include(v, include_keywords)]

        if exclude_keywords:
            filtered = [v for v in filtered if matches_exclude(v, exclude_keywords)]

    return filtered


# Backward compatibility alias
def apply_salary_filters(vacancies, min_salary=None, hide_empty=False):
    """Legacy function - use apply_filters instead."""
    return apply_filters(vacancies, min_salary=min_salary, hide_empty=hide_empty)


def load_config():
    """Load configuration from YAML."""
    config_path = Path(__file__).parent / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@app.route("/")
def index():
    """Render main dashboard."""
    return render_template("index.html")


# Project management endpoints
@app.route("/api/projects", methods=["GET"])
def get_projects_list():
    """Get all projects."""
    try:
        config = load_config()
        storage = VacancyStorage(config["storage"]["database"])
        projects = storage.get_projects()

        return jsonify(
            {
                "success": True,
                "projects": projects,
                "current_project_id": current_project_id,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/projects", methods=["POST"])
def create_new_project():
    """Create a new project."""
    try:
        data = request.get_json()
        name = data.get("name", "New Project")
        query = data.get("query", "")

        config = load_config()
        storage = VacancyStorage(config["storage"]["database"])
        project_id = storage.create_project(name, query)

        return jsonify({"success": True, "project_id": project_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/projects/<int:project_id>/switch", methods=["POST"])
def switch_project(project_id):
    """Switch current project."""
    global current_project_id
    current_project_id = project_id

    return jsonify({"success": True, "current_project_id": current_project_id})


@app.route("/api/projects/<int:project_id>", methods=["PUT"])
def update_project_details(project_id):
    """Update project details."""
    try:
        data = request.get_json()
        name = data.get("name")
        query = data.get("query")

        config = load_config()
        storage = VacancyStorage(config["storage"]["database"])
        storage.update_project(project_id, name=name, query=query)

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/projects/<int:project_id>", methods=["DELETE"])
def delete_project_endpoint(project_id):
    """Delete a project."""
    global current_project_id

    try:
        # Don't allow deleting the default project
        if project_id == 1:
            return jsonify(
                {"success": False, "error": "Cannot delete the default project"}
            )

        config = load_config()
        storage = VacancyStorage(config["storage"]["database"])
        storage.delete_project(project_id)

        # Switch to default project if current was deleted
        if current_project_id == project_id:
            current_project_id = 1

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


def parse_filter_params(request_args):
    """Parse filter parameters from request."""
    params = {
        "min_salary": request_args.get("min_salary", type=int),
        "max_salary": request_args.get("max_salary", type=int),
        "hide_empty": request_args.get("hide_empty", "false").lower() == "true",
        "include_keywords": None,
        "exclude_keywords": None,
        "search_in": None,
    }

    # Parse comma-separated keywords
    include_str = request_args.get("include_keywords", "")
    if include_str:
        params["include_keywords"] = [
            kw.strip() for kw in include_str.split(",") if kw.strip()
        ]

    exclude_str = request_args.get("exclude_keywords", "")
    if exclude_str:
        params["exclude_keywords"] = [
            kw.strip() for kw in exclude_str.split(",") if kw.strip()
        ]

    # Parse search_in fields
    search_in_str = request_args.get("search_in", "")
    if search_in_str:
        params["search_in"] = [f.strip() for f in search_in_str.split(",") if f.strip()]

    return params


def has_active_filters(params):
    """Check if any filters are active."""
    return (
        params["min_salary"] is not None
        or params["max_salary"] is not None
        or params["hide_empty"]
        or params["include_keywords"]
        or params["exclude_keywords"]
    )


@app.route("/api/stats")
def get_stats():
    """Get current statistics."""
    try:
        config = load_config()
        storage = VacancyStorage(config["storage"]["database"])

        # Get filter parameters
        filter_params = parse_filter_params(request.args)

        vacancies = storage.load_vacancies(current_project_id)

        if not vacancies:
            return jsonify({"success": True, "total_vacancies": 0, "report": None})

        # Apply all filters
        filtered_vacancies = apply_filters(
            vacancies,
            min_salary=filter_params["min_salary"],
            max_salary=filter_params["max_salary"],
            hide_empty=filter_params["hide_empty"],
            include_keywords=filter_params["include_keywords"],
            exclude_keywords=filter_params["exclude_keywords"],
            search_in=filter_params["search_in"],
        )

        if not filtered_vacancies:
            return jsonify(
                {
                    "success": True,
                    "total_vacancies": 0,
                    "report": None,
                    "filtered": True,
                    "original_count": len(vacancies),
                }
            )

        # Analyze filtered vacancies
        analyzer = VacancyAnalyzer(config)
        report = analyzer.create_report(filtered_vacancies)

        return jsonify(
            {
                "success": True,
                "total_vacancies": len(filtered_vacancies),
                "report": report,
                "filtered": has_active_filters(filter_params),
                "original_count": len(vacancies),
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/vacancies")
def get_vacancies():
    """Get vacancies list with optional filtering."""
    try:
        config = load_config()
        storage = VacancyStorage(config["storage"]["database"])

        # Get filter parameters
        filter_params = parse_filter_params(request.args)

        # Load vacancies for current project
        vacancies = storage.load_vacancies(current_project_id)

        # Apply all filters
        filtered_vacancies = apply_filters(
            vacancies,
            min_salary=filter_params["min_salary"],
            max_salary=filter_params["max_salary"],
            hide_empty=filter_params["hide_empty"],
            include_keywords=filter_params["include_keywords"],
            exclude_keywords=filter_params["exclude_keywords"],
            search_in=filter_params["search_in"],
        )

        # Pagination
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))

        start = (page - 1) * per_page
        end = start + per_page

        paginated = filtered_vacancies[start:end]

        return jsonify(
            {
                "success": True,
                "vacancies": paginated,
                "total": len(filtered_vacancies),
                "page": page,
                "per_page": per_page,
                "pages": (len(filtered_vacancies) + per_page - 1) // per_page,
                "filtered": has_active_filters(filter_params),
                "original_count": len(vacancies),
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/collect", methods=["POST"])
def start_collection():
    """Start vacancy collection."""
    global collection_status, current_project_id

    if collection_status["running"]:
        return jsonify({"success": False, "message": "Collection already running"})

    params = request.get_json() or {}
    query = params.get("query", "руководитель отдела маркетинга")
    area = params.get("area")
    max_pages = params.get("max_pages", 10)
    per_page = params.get("per_page", 20)
    experience = params.get("experience")

    # Project handling
    create_new = params.get("create_new_project", False)
    project_name = params.get("project_name", query)
    target_project_id = current_project_id

    def collect():
        global collection_status, current_project_id
        nonlocal target_project_id

        collection_status["running"] = True
        collection_status["progress"] = 0
        collection_status["message"] = "Starting collection..."

        try:
            config = load_config()
            api_client = HHAPIClient(config)
            storage = VacancyStorage(config["storage"]["database"])

            # Create new project if requested
            if create_new:
                target_project_id = storage.create_project(project_name, query)
                current_project_id = target_project_id  # Switch to new project
                collection_status["message"] = f"Created new project: {project_name}"
                print(f"Created new project ID: {target_project_id}")

            collection_status["message"] = f'Collecting vacancies for "{query}"...'
            raw_vacancies = api_client.collect_all_vacancies(
                text=query,
                area=int(area) if area else None,
                max_pages=max_pages,
                per_page=per_page,
                experience=experience,
                employment=None,
                with_details=True,
            )

            print(f"Collected {len(raw_vacancies)} raw vacancies")

            collection_status["message"] = "Parsing data..."
            parsed_vacancies = VacancyParser.parse_multiple(raw_vacancies)
            print(f"Parsed {len(parsed_vacancies)} vacancies")

            collection_status["message"] = (
                f"Saving to database (project {target_project_id})..."
            )
            print(f"Saving to project_id={target_project_id}")
            storage.save_vacancies(parsed_vacancies, target_project_id)
            print(f"Save completed!")

            collection_status["progress"] = 100
            collection_status["message"] = (
                f"Completed! Collected {len(parsed_vacancies)} vacancies"
            )

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            print(f"ERROR in collection: {error_details}")
            collection_status["message"] = f"Error: {str(e)}"
        finally:
            collection_status["running"] = False

    # Start collection in background
    thread = threading.Thread(target=collect)
    thread.daemon = True
    thread.start()

    return jsonify({"success": True, "message": "Collection started"})


@app.route("/api/status")
def get_status():
    """Get collection status."""
    return jsonify(collection_status)


@app.route("/api/export/<format>")
def export_data(format):
    """Export data in specified format."""
    try:
        config = load_config()
        storage = VacancyStorage(config["storage"]["database"])

        # Load vacancies for current project
        vacancies = storage.load_vacancies(current_project_id)

        if format == "json":
            export_path = storage.export_json(vacancies)
            return send_file(export_path, as_attachment=True)
        elif format == "csv":
            export_path = storage.export_csv(vacancies)
            return send_file(export_path, as_attachment=True)
        else:
            return jsonify({"success": False, "error": "Unsupported format"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
