import requests

URL = "http://localhost:5001/"

try:
    print(f"Pinging {URL}...")
    response = requests.get(URL, timeout=5)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Health Check Failed: {e}")
