import sys
try:
    import fastapi
    print("✅ fastapi imported")
except ImportError as e:
    print(f"❌ fastapi error: {e}")

try:
    import uvicorn
    print("✅ uvicorn imported")
except ImportError as e:
    print(f"❌ uvicorn error: {e}")

try:
    import easyocr
    print("✅ easyocr imported")
except ImportError as e:
    print(f"❌ easyocr error: {e}")

import socket
def check_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

port = 5000
if check_port(port):
    print(f"❌ Port {port} is ALREADY IN USE")
else:
    print(f"✅ Port {port} is available")

print("System path:", sys.path)
