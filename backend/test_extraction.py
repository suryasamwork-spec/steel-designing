import requests

url = "http://localhost:5001/api/extract-text"
files = {
    'pdf': ('test_valid.pdf', open('test_valid.pdf', 'rb'), 'application/pdf')
}
data = {
    'x': 100,
    'y': 100,
    'width': 200,
    'height': 100,
    'page_num': 0
}

try:
    print(f"Sending request to {url}...")
    response = requests.post(url, files=files, data=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
