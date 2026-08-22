import requests
import time

# First login to get session
session = requests.Session()
url = 'http://127.0.0.1:5000/login'
data = {'email': 'test@example.com', 'password': 'password123'}
r = session.post(url, data=data, allow_redirects=False)
print('Login:', r.status_code)

# Test /api/chat
chat_url = 'http://127.0.0.1:5000/api/chat'
test_questions = [
    'What is the attendance policy?',
    'What are the hostel rules and timings?',
    'What is K-HUB?'
]

for q in test_questions:
    print('\n--- Question:', q, '---')
    r = session.post(chat_url, json={'message': q, 'session_id': 'test-session-1'})
    print('Status:', r.status_code)
    if r.status_code == 200:
        result = r.json()
        answer = result.get("answer", "")
        print('Answer length:', len(answer))
        print('Answer preview:', repr(answer[:200]))
        sources = result.get('sources', [])
        print('Sources count:', len(sources))
        for s in sources:
            doc = s.get('doc', 'N/A')
            page = s.get('page', 'N/A')
            print('  -', doc, 'Page', page)
    else:
        print('Error:', r.text)