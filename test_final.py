"""Test exact same parameters as in our collection script."""

import requests

url = "https://api.hh.ru/vacancies"
headers = {'User-Agent': 'HH-Parser/1.0 (your.email@example.com)'}

params = {
    'text': 'руководитель отдела маркетинга',
    'area': '1',
    'per_page': 100,
    'page': 0
}

print("Testing exact parameters...")
print(f"Params: {params}")
response = requests.get(url, headers=headers, params=params, timeout=10)
print(f"\nURL: {response.url}")
print(f"Status: {response.status_code}\n")

if response.status_code == 200:
    data = response.json()
    print(f"✅ SUCCESS!")
    print(f"Found: {data.get('found', 0)} total")
    print(f"Returned: {len(data.get('items', []))} items")
    print(f"Pages: {data.get('pages', 0)}")
    if data.get('items'):
        print(f"\nFirst 3 vacancies:")
        for i, item in enumerate(data['items'][:3], 1):
            print(f"  {i}. {item.get('name', 'N/A')}")
else:
    print(f"❌ ERROR!")
    print(f"Response: {response.text[:500]}")
