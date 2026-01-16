"""Parser for extracting structured data from HH.ru vacancy responses."""

from typing import Dict, Optional, List
import re


class VacancyParser:
    """Parser for HH.ru vacancy data."""
    
    @staticmethod
    def clean_html(text: Optional[str]) -> str:
        """
        Remove HTML tags from text.
        
        Args:
            text: Text with possible HTML tags
            
        Returns:
            Clean text without HTML
        """
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Decode common HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&quot;', '"')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    @staticmethod
    def parse_vacancy(vacancy_data: Dict) -> Dict:
        """
        Extract structured information from vacancy data.
        
        Args:
            vacancy_data: Raw vacancy data from API
            
        Returns:
            Parsed and normalized vacancy information
        """
        # Basic information
        parsed = {
            'id': vacancy_data.get('id'),
            'name': vacancy_data.get('name', ''),
            'url': vacancy_data.get('alternate_url', ''),
            'published_at': vacancy_data.get('published_at', ''),
            'created_at': vacancy_data.get('created_at', ''),
        }
        
        # Salary information
        salary = vacancy_data.get('salary')
        if salary:
            parsed['salary_from'] = salary.get('from')
            parsed['salary_to'] = salary.get('to')
            parsed['salary_currency'] = salary.get('currency')
            parsed['salary_gross'] = salary.get('gross')
        else:
            parsed['salary_from'] = None
            parsed['salary_to'] = None
            parsed['salary_currency'] = None
            parsed['salary_gross'] = None
        
        # Company information
        employer = vacancy_data.get('employer', {})
        parsed['company_name'] = employer.get('name', '')
        parsed['company_url'] = employer.get('alternate_url', '')
        
        # Area
        area = vacancy_data.get('area', {})
        parsed['area'] = area.get('name', '')
        
        # Experience
        experience = vacancy_data.get('experience', {})
        parsed['experience'] = experience.get('name', '')
        
        # Employment type
        employment = vacancy_data.get('employment', {})
        parsed['employment'] = employment.get('name', '')
        
        # Schedule
        schedule = vacancy_data.get('schedule', {})
        parsed['schedule'] = schedule.get('name', '')
        
        # Description and requirements
        description = vacancy_data.get('description', '')
        parsed['description'] = VacancyParser.clean_html(description)
        
        # Key skills
        key_skills = vacancy_data.get('key_skills', [])
        parsed['key_skills'] = [skill.get('name', '') for skill in key_skills]
        
        # Professional roles
        professional_roles = vacancy_data.get('professional_roles', [])
        parsed['professional_roles'] = [role.get('name', '') for role in professional_roles]
        
        # Combine all text for analysis
        text_parts = [
            parsed['name'],
            parsed['description'],
            ' '.join(parsed['key_skills'])
        ]
        parsed['full_text'] = ' '.join(filter(None, text_parts))
        
        return parsed
    
    @staticmethod
    def parse_multiple(vacancies: List[Dict]) -> List[Dict]:
        """
        Parse multiple vacancies.
        
        Args:
            vacancies: List of raw vacancy data
            
        Returns:
            List of parsed vacancies
        """
        return [VacancyParser.parse_vacancy(v) for v in vacancies]
