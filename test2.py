from fastapi.testclient import TestClient
from app.main import app
import os

client = TestClient(app)

# We need a dummy file for the UploadFile
with open("test.txt", "w") as f:
    f.write("hello")

files = {'file': ('test.txt', open('test.txt', 'rb'), 'text/plain')}
data = {'content': 'what is name in this file ?'}

response = client.post("/chat/gemma4", data=data, files=files)
print("Response:", response.status_code, response.text)
