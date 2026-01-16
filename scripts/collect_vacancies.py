"""Script to collect vacancies from HH.ru API."""

import yaml
import sys
from pathlib import Path
from tqdm import tqdm

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from api_client import HHAPIClient
from parser import VacancyParser
from storage import VacancyStorage


def main():
    """Main function to collect vacancies."""
    # Load configuration
    config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    print("=" * 60)
    print("HH.ru Vacancy Collector")
    print("=" * 60)
    
    # Initialize components
    api_client = HHAPIClient(config)
    storage = VacancyStorage(config['storage']['database'])
    
    # Get search parameters
    search_config = config['search']
    
    print(f"\nПоисковый запрос: '{search_config['query']}'")
    print(f"Регион: {search_config.get('area', 'Все')}")
    print(f"Максимум страниц: {search_config['max_pages']}")
    print()
    
    # Collect vacancies
    print("Начинаем сбор вакансий...\n")
    
    raw_vacancies = api_client.collect_all_vacancies(
        text=search_config['query'],
        area=search_config.get('area'),
        max_pages=search_config['max_pages'],
        per_page=search_config['per_page'],
        experience=search_config.get('experience'),
        employment=search_config.get('employment'),
        with_details=True
    )
    
    if not raw_vacancies:
        print("\n❌ Вакансии не найдены!")
        return
    
    print(f"\n✅ Собрано {len(raw_vacancies)} вакансий")
    
    # Parse vacancies
    print("\nПарсинг данных...")
    parsed_vacancies = VacancyParser.parse_multiple(raw_vacancies)
    
    # Save to database
    print("Сохранение в базу данных...")
    storage.save_vacancies(parsed_vacancies)
    
    # Export to JSON
    export_dir = Path(config['storage']['export_dir'])
    json_path = export_dir / 'vacancies.json'
    storage.export_to_json(parsed_vacancies, str(json_path))
    
    # Export to CSV
    csv_path = export_dir / 'vacancies.csv'
    storage.export_to_csv(parsed_vacancies, str(csv_path))
    
    print("\n" + "=" * 60)
    print("✅ Сбор данных завершён успешно!")
    print("=" * 60)
    print(f"\nВакансий собрано: {len(parsed_vacancies)}")
    print(f"База данных: {config['storage']['database']}")
    print(f"JSON экспорт: {json_path}")
    print(f"CSV экспорт: {csv_path}")
    print()


if __name__ == '__main__':
    main()
