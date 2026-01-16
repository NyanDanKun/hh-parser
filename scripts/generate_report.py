"""Script to generate a comprehensive markdown report."""

import yaml
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from analyzer import VacancyAnalyzer
from storage import VacancyStorage


def generate_markdown_report(report: dict, vacancies: list) -> str:
    """Generate markdown report from analysis."""
    
    md = []
    md.append("# Отчёт по анализу вакансий HH.ru")
    md.append(f"\n**Дата анализа:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"\n**Всего вакансий:** {report['total_vacancies']}")
    md.append("\n---\n")
    
    # Top Keywords
    md.append("## 🔑 Топ-50 ключевых слов\n")
    md.append("Наиболее часто встречающиеся слова в описаниях вакансий:\n")
    md.append("| № | Ключевое слово | Частота |")
    md.append("|---|----------------|---------|")
    for i, (word, count) in enumerate(report['top_keywords'][:50], 1):
        md.append(f"| {i} | {word} | {count} |")
    
    # Top Skills
    md.append("\n## 💼 Топ-30 навыков\n")
    md.append("Наиболее востребованные навыки (из поля key_skills):\n")
    md.append("| № | Навык | Вакансий |")
    md.append("|---|-------|----------|")
    for i, (skill, count) in enumerate(report['top_skills'][:30], 1):
        md.append(f"| {i} | {skill} | {count} |")
    
    # Salary Statistics
    md.append("\n## 💰 Статистика зарплат\n")
    salary_stats = report['salary_stats']
    md.append(f"- **Вакансий с указанной зарплатой:** {salary_stats['count_with_salary']} из {salary_stats['count_total']}\n")
    
    if 'avg_from' in salary_stats:
        md.append("### Зарплата ОТ:")
        md.append(f"- Минимум: **{salary_stats['min_from']:,.0f} руб.**")
        md.append(f"- Максимум: **{salary_stats['max_from']:,.0f} руб.**")
        md.append(f"- Среднее: **{salary_stats['avg_from']:,.0f} руб.**\n")
    
    if 'avg_to' in salary_stats:
        md.append("### Зарплата ДО:")
        md.append(f"- Минимум: **{salary_stats['min_to']:,.0f} руб.**")
        md.append(f"- Максимум: **{salary_stats['max_to']:,.0f} руб.**")
        md.append(f"- Среднее: **{salary_stats['avg_to']:,.0f} руб.**\n")
    
    # Experience
    md.append("## 📈 Требования по опыту\n")
    md.append("| Уровень опыта | Количество вакансий |")
    md.append("|---------------|---------------------|")
    for exp, count in sorted(report['experience_stats'].items(), key=lambda x: x[1], reverse=True):
        if exp:
            md.append(f"| {exp} | {count} |")
    
    # Resume Tips
    md.append("\n## 💡 Рекомендации для оптимизации резюме\n")
    md.append("На основе анализа вакансий, рекомендуем:\n")
    for i, tip in enumerate(report['resume_tips'], 1):
        md.append(f"{i}. {tip}")
    
    # Top Companies
    md.append("\n## 🏢 Топ-20 компаний по количеству вакансий\n")
    company_counts = {}
    for v in vacancies:
        company = v.get('company_name', 'Неизвестно')
        company_counts[company] = company_counts.get(company, 0) + 1
    
    top_companies = sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    md.append("| № | Компания | Вакансий |")
    md.append("|---|----------|----------|")
    for i, (company, count) in enumerate(top_companies, 1):
        md.append(f"| {i} | {company} | {count} |")
    
    return '\n'.join(md)


def main():
    """Main function to generate report."""
    # Load configuration
    config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    print("=" * 60)
    print("HH.ru Report Generator")
    print("=" * 60)
    
    # Initialize components
    storage = VacancyStorage(config['storage']['database'])
    analyzer = VacancyAnalyzer(config)
    
    # Load vacancies
    print("\nЗагрузка данных...")
    vacancies = storage.load_vacancies()
    
    if not vacancies:
        print("\n❌ Вакансии не найдены в базе данных!")
        return
    
    print(f"✅ Загружено {len(vacancies)} вакансий")
    
    # Analyze
    print("Анализ данных...")
    report = analyzer.create_report(vacancies)
    
    # Generate markdown
    print("Генерация отчёта...")
    markdown = generate_markdown_report(report, vacancies)
    
    # Save report
    export_dir = Path(config['storage']['export_dir'])
    report_path = export_dir / 'report.md'
    export_dir.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    print("\n" + "=" * 60)
    print("✅ Отчёт создан успешно!")
    print("=" * 60)
    print(f"Файл: {report_path}")
    print()


if __name__ == '__main__':
    main()
