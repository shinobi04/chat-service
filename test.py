from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
response = client.post("/chat/gemma4")
print("Response:", response.status_code, response.text)
