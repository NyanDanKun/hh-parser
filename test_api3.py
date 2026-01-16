"""Test with area parameter."""

import requests

url = "https://api.hh.ru/vacancies"  
headers = {'User-Agent': 'HH-Parser/1.0'}

# Try with area
params = {
    'text': 'руководитель маркетинга',
    'area': '1',  # Try as string
    'per_page': 10
}

print("Testing with 'руководитель маркетинга' and area=1...")
response = requests.get(url, headers=headers, params=params, timeout=10)
print(f"URL: {response.url}")
print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"✅ Found: {data.get('found', 0)}")
    print(f"Items: {len(data.get('items', []))}")
    if data.get('items'):
        print(f"\nFirst vacancy: {data['items'][0]['name']}")
else:
    print(f"Error: {response.text[:300]}")
