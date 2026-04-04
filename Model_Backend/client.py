import requests

url = "https://abcd1234.ngrok-free.app/analyze"

files = {
    "file": open("test_images/test_prohibited.jpg", "rb")
}

res = requests.post(url, files=files)

print(res.json())