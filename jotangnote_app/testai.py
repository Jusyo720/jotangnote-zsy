import requests

url = "http://127.0.0.1:5001/chat"   

payload = {
    "message": "帮我查一下 ID 为 1 的笔记内容",  
    "session_id": "test_session_1"            
}

try:
    response = requests.post(url, json=payload)
    print("状态码:", response.status_code)
    if response.status_code == 200:
        print("AI 回复:", response.json().get("reply"))
    else:
        print("出错内容:", response.text)
except Exception as e:
    print("连接失败:", e)