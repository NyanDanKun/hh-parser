"""HH.ru API Client for fetching job vacancies."""

import requests
import time
from typing import Dict, List, Optional
from datetime import datetime


class HHAPIClient:
    """Client for interacting with HH.ru API."""
    
    def __init__(self, config: Dict):
        """
        Initialize API client with configuration.
        
        Args:
            config: Configuration dictionary with API settings
        """
        self.base_url = config['api']['base_url']
        self.headers = {
            'User-Agent': config['api']['user_agent']
        }
        self.timeout = config['api']['timeout']
        self.requests_per_second = config['api']['requests_per_second']
        self.last_request_time = 0
        
    def _rate_limit(self):
        """Ensure we don't exceed rate limits."""
        elapsed = time.time() - self.last_request_time
        min_interval = 1.0 / self.requests_per_second
        
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
            
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None, retries: int = 3) -> Dict:
        """
        Make HTTP request to API with retry logic.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            retries: Number of retry attempts
            
        Returns:
            JSON response as dictionary
            
        Raises:
            requests.RequestException: If request fails after retries
        """
        self._rate_limit()
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(retries):
            try:
                response = requests.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt == retries - 1:
                    raise
                print(f"Request failed (attempt {attempt + 1}/{retries}): {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
                
        return {}
    
    def search_vacancies(
        self,
        text: str,
        area: Optional[int] = None,
        period: Optional[int] = None,
        per_page: int = 100,
        page: int = 0,
        experience: Optional[str] = None,
        employment: Optional[str] = None
    ) -> Dict:
        """
        Search for vacancies using HH.ru API.
        
        Args:
            text: Search query text
            area: Area ID (1 - Moscow, 2 - SPb, 113 - Russia)
            period: Number of days to look back
            per_page: Results per page (max 100)
            page: Page number (0-indexed)
            experience: Experience level filter
            employment: Employment type filter
            
        Returns:
            Dictionary with search results
        """
        params = {
            'text': text,
            'per_page': per_page,
            'page': page
        }
        
        if area is not None:
            params['area'] = str(area)  # Convert to string for API
        if period is not None:
            params['period'] = period
        if experience:
            params['experience'] = experience
        if employment:
            params['employment'] = employment
            
        return self._make_request('vacancies', params)
    
    def get_vacancy_details(self, vacancy_id: str) -> Dict:
        """
        Get detailed information about a specific vacancy.
        
        Args:
            vacancy_id: Vacancy ID
            
        Returns:
            Dictionary with vacancy details
        """
        return self._make_request(f'vacancies/{vacancy_id}')
    
    def collect_all_vacancies(
        self,
        text: str,
        area: Optional[int] = None,
        period: Optional[int] = None,
        max_pages: int = 10,
        per_page: int = 100,
        experience: Optional[str] = None,
        employment: Optional[str] = None,
        with_details: bool = True
    ) -> List[Dict]:
        """
        Collect all vacancies matching search criteria.
        
        Args:
            text: Search query
            area: Area ID
            period: Days to look back
            max_pages: Maximum number of pages to fetch
            per_page: Results per page
            experience: Experience filter
            employment: Employment filter
            with_details: Whether to fetch full vacancy details
            
        Returns:
            List of vacancy dictionaries
        """
        all_vacancies = []
        
        for page in range(max_pages):
            print(f"Fetching page {page + 1}/{max_pages}...")
            
            result = self.search_vacancies(
                text=text,
                area=area,
                period=period,
                per_page=per_page,
                page=page,
                experience=experience,
                employment=employment
            )
            
            vacancies = result.get('items', [])
            
            if not vacancies:
                print(f"No more vacancies found (stopped at page {page + 1})")
                break
                
            if with_details:
                # Fetch detailed info for each vacancy
                for vacancy in vacancies:
                    try:
                        detailed = self.get_vacancy_details(vacancy['id'])
                        all_vacancies.append(detailed)
                    except Exception as e:
                        print(f"Failed to fetch details for vacancy {vacancy['id']}: {e}")
                        # Use basic info if details fetch fails
                        all_vacancies.append(vacancy)
            else:
                all_vacancies.extend(vacancies)
                
            # Check if this is the last page
            total_pages = result.get('pages', 1)
            if page + 1 >= total_pages:
                print(f"Reached last page ({total_pages})")
                break
                
        print(f"Collected {len(all_vacancies)} vacancies")
        return all_vacancies
