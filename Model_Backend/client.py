import requests

url = "https://anthropographic-similarly-darleen.ngrok-free.dev/"

files = {
    "file": open("test_images/test_prohibited.jpg", "rb")
}

res = requests.post(url, files=files)

print(res.json())