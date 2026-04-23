import urllib.request
import urllib.parse
import json

url = 'http://127.0.0.1:8000/api/upload'
boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
headers = {'Content-Type': f'multipart/form-data; boundary={boundary}'}

with open('Data_test_eng/images/7.jpg', 'rb') as f:
    file_content = f.read()

data = (
    f'--{boundary}\r\n'
    f'Content-Disposition: form-data; name="file"; filename="7.jpg"\r\n'
    f'Content-Type: image/jpeg\r\n\r\n'
).encode('utf-8') + file_content + f'\r\n--{boundary}--\r\n'.encode('utf-8')

req = urllib.request.Request(url, data=data, headers=headers, method='POST')
try:
    with urllib.request.urlopen(req) as response:
        print("Status:", response.status)
        res = json.loads(response.read().decode())
        print("Texts:", res.get("texts"))
        print("Message:", res.get("message"))
except Exception as e:
    print("Error:", e)
