import asyncio
import websockets
import json
import openai
import uuid
import random
import string

# API 키 설정
openai.api_key = "API키 알아서 잘 넣자"

# 토큰 생성 함수
def generate_token(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# 초기 토큰 목록 생성
token_list = [generate_token() for _ in range(100)]

async def gpt_response(prompt):
   model_engine = "text-davinci-002"
   try:
        response = openai.Completion.create(
            engine=model_engine,
            prompt=prompt,
            max_tokens=50,
            n=1,
            stop=None,
            temperature=0.5,
        )
        message = response.choices[0].text.strip()
        return message
   except Exception as e:
       print(f"GPT API 에러: {e}")
       return "죄송합니다. 문제가 발생했습니다."

connected_clients = {}
chatrooms = {}

async def websocket_handler(websocket, path):
    token = await websocket.recv()
    if token in token_list:
        connected_clients[token] = websocket
        await websocket.send(json.dumps({"status": "Y"}))
    else:
        await websocket.send(json.dumps({"status": "N"}))
        return

    try:
        while True:
            data = await websocket.recv()
            message = json.loads(data)

            if message["action"] == "create_chatroom":
                chatroom_id = str(uuid.uuid4())
                chatrooms[chatroom_id] = {
                    "owner": token,
                    "clients": [],
                    "password": message.get("password", "")
                }
                connected_clients[token].send(json.dumps({"chatroom_id": chatroom_id}))

            elif message["action"] == "join_chatroom":
                chatroom_id = message["chatroom_id"]
                chatroom_password = message.get("password", "")
                if chatroom_id in chatrooms and chatrooms[chatroom_id]["password"] == chatroom_password:
                    chatrooms[chatroom_id]["clients"].append(token)
                    connected_clients[token].send(json.dumps({"message": f"{chatroom_id} 채팅방에 입장하였습니다."}))
                else:
                    connected_clients[token].send(json.dumps({"error": "잘못된 채팅방 ID 또는 비밀번호입니다."}))

            elif message["action"] == "delete_chatroom":
                chatroom_id = message["chatroom_id"]
                if chatroom_id in chatrooms and chatrooms[chatroom_id]["owner"] == token:
                    del chatrooms[chatroom_id]
                    connected_clients[token].send(json.dumps({"message": f"{chatroom_id} 채팅방이 삭제되었습니다."}))
                else:
                    connected_clients[token].send(json.dumps({"error": "채팅방을 삭제할 권한이 없습니다."}))

            elif message["action"] == "send_message":
                chatroom_id = message["chatroom_id"]
                if token in chatrooms[chatroom_id]["clients"]:
                    user_message = message["message"]
                    gpt_message = await gpt_response(user_message)
                    gpt_data = {"message": f"GPT: {gpt_message}"}
                    for client_token in chatrooms[chatroom_id]["clients"]:
                        if client_token != token:
                            connected_clients[client_token].send(json.dumps(gpt_data))
                else:
                    connected_clients[token].send(json.dumps({"error": "채팅방에 입장하지 않았습니다."}))
    except websockets.ConnectionClosed:
        del connected_clients[token]

start_server = websockets.serve(websocket_handler, "localhost", 8765)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
