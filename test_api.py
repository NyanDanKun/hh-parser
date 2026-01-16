"""Test script to debug HH.ru API connection."""

import requests
import json

# Test simple API request
url = "https://api.hh.ru/vacancies"
headers = {
    'User-Agent': 'HH-Parser/1.0 (test@example.com)'
}

# Try simple search
params = {
    'text': 'маркетинг',
    'per_page': 10,
    'page': 0,
    'area': 1
}

print("Testing HH.ru API...")
print(f"URL: {url}")
print(f"Params: {params}")
print()

try:
    response = requests.get(url, headers=headers, params=params, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response URL: {response.url}")
    print()
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Found {data.get('found', 0)} total vacancies")
        print(f"Returned {len(data.get('items', []))} items")
        if data.get('items'):
            print(f"\nFirst vacancy: {data['items'][0].get('name', 'N/A')}")
    else:
        print("❌ Error!")
        print(f"Response: {response.text[:500]}")
        
except Exception as e:
    print(f"❌ Exception: {e}")
    import traceback
    traceback.print_exc()
