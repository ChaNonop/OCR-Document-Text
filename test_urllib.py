import urllib.request
import urllib.parse

url = 'http://127.0.0.1:8000/api/upload'
boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
headers = {'Content-Type': f'multipart/form-data; boundary={boundary}'}

with open('blank.jpg', 'rb') as f:
    file_content = f.read()

data = (
    f'--{boundary}\r\n'
    f'Content-Disposition: form-data; name="file"; filename="blank.jpg"\r\n'
    f'Content-Type: image/jpeg\r\n\r\n'
).encode('utf-8') + file_content + f'\r\n--{boundary}--\r\n'.encode('utf-8')

req = urllib.request.Request(url, data=data, headers=headers, method='POST')
try:
    with urllib.request.urlopen(req) as response:
        print("Status:", response.status)
        print("Response:", response.read().decode())
except Exception as e:
    print("Error:", e)
