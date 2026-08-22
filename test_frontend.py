import requests
session = requests.Session()
session.post('http://127.0.0.1:5000/login', 
                  data={'email': 'test@example.com', 'password': 'newpass123'},
                  allow_redirects=False)
r = session.get('http://127.0.0.1:5000/chat')
print('Status:', r.status_code)
print('Contains local-db.js:', 'local-db.js' in r.text)
print('Contains module script:', 'type="module"' in r.text)