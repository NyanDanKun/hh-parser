"""Analyzer for extracting keywords and generating insights from vacancy data."""

from typing import Dict, List, Set
from collections import Counter
import re


class VacancyAnalyzer:
    """Analyzer for vacancy data to extract keywords and competencies."""
    
    def __init__(self, config: Dict):
        """
        Initialize analyzer with configuration.
        
        Args:
            config: Configuration dictionary
        """
        self.min_word_length = config['analysis']['min_word_length']
        self.min_frequency = config['analysis']['min_frequency']
        self.top_keywords = config['analysis']['top_keywords']
        self.stop_words = set(config['analysis']['stop_words'])
        
        # Add common Russian stop words
        self.stop_words.update([
            'это', 'как', 'так', 'для', 'или', 'все', 'что', 'быть',
            'мочь', 'год', 'его', 'весь', 'наш', 'свой', 'один',
            'который', 'если', 'быть', 'может', 'также', 'более',
            'чтобы', 'можно', 'либо', 'рамках', 'должен'
        ])
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of words
        """
        # Convert to lowercase
        text = text.lower()
        
        # Extract words (including words with hyphens)
        words = re.findall(r'\b[а-яёa-z][\w-]*[а-яёa-z]\b|\b[а-яёa-z]\b', text)
        
        # Filter by length and stop words
        words = [
            w for w in words 
            if len(w) >= self.min_word_length 
            and w not in self.stop_words
            and not w.isdigit()
        ]
        
        return words
    
    def extract_keywords(self, vacancies: List[Dict]) -> Counter:
        """
        Extract keywords from vacancy descriptions.
        
        Args:
            vacancies: List of parsed vacancies
            
        Returns:
            Counter with keyword frequencies
        """
        word_counter = Counter()
        
        for vacancy in vacancies:
            # Analyze full text
            full_text = vacancy.get('full_text', '')
            words = self._tokenize(full_text)
            word_counter.update(words)
        
        return word_counter
    
    def extract_skills(self, vacancies: List[Dict]) -> Counter:
        """
        Extract explicitly mentioned skills.
        
        Args:
            vacancies: List of parsed vacancies
            
        Returns:
            Counter with skill frequencies
        """
        skill_counter = Counter()
        
        for vacancy in vacancies:
            skills = vacancy.get('key_skills', [])
            skill_counter.update(skills)
        
        return skill_counter
    
    def analyze_salary_range(self, vacancies: List[Dict]) -> Dict:
        """
        Analyze salary ranges.
        
        Args:
            vacancies: List of parsed vacancies
            
        Returns:
            Dictionary with salary statistics
        """
        salaries_from = []
        salaries_to = []
        vacancies_with_salary = 0
        
        for vacancy in vacancies:
            has_salary = False
            if vacancy.get('salary_from'):
                salaries_from.append(vacancy['salary_from'])
                has_salary = True
            if vacancy.get('salary_to'):
                salaries_to.append(vacancy['salary_to'])
                has_salary = True
            
            if has_salary:
                vacancies_with_salary += 1
        
        stats = {
            'count_with_salary': vacancies_with_salary,  # Fixed: count unique vacancies
            'count_total': len(vacancies),
        }
        
        if salaries_from:
            stats['min_from'] = min(salaries_from)
            stats['max_from'] = max(salaries_from)
            stats['avg_from'] = sum(salaries_from) / len(salaries_from)
        
        if salaries_to:
            stats['min_to'] = min(salaries_to)
            stats['max_to'] = max(salaries_to)
            stats['avg_to'] = sum(salaries_to) / len(salaries_to)
        
        return stats
    
    def analyze_experience(self, vacancies: List[Dict]) -> Counter:
        """
        Analyze required experience levels.
        
        Args:
            vacancies: List of parsed vacancies
            
        Returns:
            Counter with experience level frequencies
        """
        experience_counter = Counter()
        
        for vacancy in vacancies:
            exp = vacancy.get('experience', '')
            if exp:
                experience_counter[exp] += 1
        
        return experience_counter
    
    def get_top_keywords(self, word_counter: Counter, limit: Optional[int] = None) -> List[tuple]:
        """
        Get top keywords by frequency.
        
        Args:
            word_counter: Counter with word frequencies
            limit: Maximum number of keywords to return
            
        Returns:
            List of (word, frequency) tuples
        """
        if limit is None:
            limit = self.top_keywords
        
        # Filter by minimum frequency
        filtered = {
            word: count 
            for word, count in word_counter.items() 
            if count >= self.min_frequency
        }
        
        return Counter(filtered).most_common(limit)
    
    def generate_resume_tips(self, word_counter: Counter, skill_counter: Counter) -> List[str]:
        """
        Generate resume optimization tips based on analysis.
        
        Args:
            word_counter: Keyword frequencies
            skill_counter: Skill frequencies
            
        Returns:
            List of tips
        """
        tips = []
        
        # Top skills
        top_skills = skill_counter.most_common(10)
        if top_skills:
            skills_text = ', '.join([f'"{skill}"' for skill, _ in top_skills[:5]])
            tips.append(f"Включите следующие ключевые навыки: {skills_text}")
        
        # Top keywords
        top_words = self.get_top_keywords(word_counter, 20)
        important_keywords = [word for word, count in top_words if count > len(top_words) * 0.3]
        if important_keywords:
            keywords_text = ', '.join([f'"{word}"' for word in important_keywords[:10]])
            tips.append(f"Используйте эти ключевые слова в описании опыта: {keywords_text}")
        
        return tips
    
    def create_report(self, vacancies: List[Dict]) -> Dict:
        """
        Create comprehensive analysis report.
        
        Args:
            vacancies: List of parsed vacancies
            
        Returns:
            Dictionary with analysis results
        """
        word_counter = self.extract_keywords(vacancies)
        skill_counter = self.extract_skills(vacancies)
        salary_stats = self.analyze_salary_range(vacancies)
        experience_stats = self.analyze_experience(vacancies)
        
        report = {
            'total_vacancies': len(vacancies),
            'top_keywords': self.get_top_keywords(word_counter),
            'top_skills': skill_counter.most_common(self.top_keywords),
            'salary_stats': salary_stats,
            'experience_stats': dict(experience_stats),
            'resume_tips': self.generate_resume_tips(word_counter, skill_counter)
        }
        
        return report


from typing import Optional
