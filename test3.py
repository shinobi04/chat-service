from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
for i in range(10):
    response = client.post("/chat/gemma4")
    print(i, response.status_code, response.text)
