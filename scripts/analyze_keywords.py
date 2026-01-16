"""Script to analyze collected vacancies and extract keywords."""

import yaml
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from analyzer import VacancyAnalyzer
from storage import VacancyStorage


def main():
    """Main function to analyze vacancies."""
    # Load configuration
    config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    print("=" * 60)
    print("HH.ru Vacancy Analyzer")
    print("=" * 60)
    
    # Initialize components
    storage = VacancyStorage(config['storage']['database'])
    analyzer = VacancyAnalyzer(config)
    
    # Load vacancies from database
    print("\nЗагрузка вакансий из базы данных...")
    vacancies = storage.load_vacancies()
    
    if not vacancies:
        print("\n❌ Вакансии не найдены в базе данных!")
        print("Сначала запустите collect_vacancies.py для сбора данных.")
        return
    
    print(f"✅ Загружено {len(vacancies)} вакансий")
    
    # Analyze
    print("\nАнализ данных...")
    report = analyzer.create_report(vacancies)
    
    # Display results
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ АНАЛИЗА")
    print("=" * 60)
    
    print(f"\nВсего вакансий проанализировано: {report['total_vacancies']}")
    
    # Top keywords
    print("\n" + "-" * 60)
    print("🔑 ТОП-30 КЛЮЧЕВЫХ СЛОВ")
    print("-" * 60)
    for i, (word, count) in enumerate(report['top_keywords'][:30], 1):
        print(f"{i:2d}. {word:30s} - {count:3d} упоминаний")
    
    # Top skills
    print("\n" + "-" * 60)
    print("💼 ТОП-20 НАВЫКОВ (из key_skills)")
    print("-" * 60)
    for i, (skill, count) in enumerate(report['top_skills'][:20], 1):
        print(f"{i:2d}. {skill:40s} - {count:3d} вакансий")
    
    # Salary statistics
    print("\n" + "-" * 60)
    print("💰 СТАТИСТИКА ПО ЗАРПЛАТАМ")
    print("-" * 60)
    salary_stats = report['salary_stats']
    print(f"Вакансий с указанной зарплатой: {salary_stats['count_with_salary']} из {salary_stats['count_total']}")
    
    if 'avg_from' in salary_stats:
        print(f"\nЗарплата ОТ:")
        print(f"  Минимум: {salary_stats['min_from']:,.0f} руб.")
        print(f"  Максимум: {salary_stats['max_from']:,.0f} руб.")
        print(f"  Среднее:  {salary_stats['avg_from']:,.0f} руб.")
    
    if 'avg_to' in salary_stats:
        print(f"\nЗарплата ДО:")
        print(f"  Минимум: {salary_stats['min_to']:,.0f} руб.")
        print(f"  Максимум: {salary_stats['max_to']:,.0f} руб.")
        print(f"  Среднее:  {salary_stats['avg_to']:,.0f} руб.")
    
    # Experience requirements
    print("\n" + "-" * 60)
    print("📈 ТРЕБОВАНИЯ ПО ОПЫТУ")
    print("-" * 60)
    for exp, count in report['experience_stats'].items():
        if exp:
            print(f"  {exp}: {count} вакансий")
    
    # Resume tips
    print("\n" + "-" * 60)
    print("💡 РЕКОМЕНДАЦИИ ДЛЯ РЕЗЮМЕ")
    print("-" * 60)
    for i, tip in enumerate(report['resume_tips'], 1):
        print(f"{i}. {tip}")
    
    # Save report
    export_dir = Path(config['storage']['export_dir'])
    report_path = export_dir / 'analysis_report.json'
    storage.export_report(report, str(report_path))
    
    print("\n" + "=" * 60)
    print("✅ Анализ завершён!")
    print("=" * 60)
    print(f"Отчёт сохранён: {report_path}")
    print()


if __name__ == '__main__':
    main()
