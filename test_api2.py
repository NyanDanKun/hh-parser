"""Final test with proper request library."""

import requests

url = "https://api.hh.ru/vacancies"
headers = {'User-Agent': 'HH-Parser/1.0'}

# Try with simpler text query
params = {
    'text': 'руководитель',
    'per_page': 10
}

print("Testing with 'руководитель'...")
response = requests.get(url, headers=headers, params=params, timeout=10)
print(f"URL: {response.url}")
print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"Found: {data.get('found', 0)}")
    print(f"Items: {len(data.get('items', []))}")
else:
    print(f"Error: {response.text[:200]}")
