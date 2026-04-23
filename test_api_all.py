import urllib.request
import glob
import json

url = 'http://127.0.0.1:8000/api/upload'
boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
headers = {'Content-Type': f'multipart/form-data; boundary={boundary}'}

for img_path in glob.glob('Data_test_eng/images/*.*'):
    try:
        with open(img_path, 'rb') as f:
            file_content = f.read()

        data = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="file"; filename="{img_path}"\r\n'
            f'Content-Type: image/jpeg\r\n\r\n'
        ).encode('utf-8') + file_content + f'\r\n--{boundary}--\r\n'.encode('utf-8')

        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode())
            print(f"{img_path}: Status {response.status}, Texts: {len(res.get('texts', []))}")
    except Exception as e:
        print(f"{img_path}: ERROR {e}")
