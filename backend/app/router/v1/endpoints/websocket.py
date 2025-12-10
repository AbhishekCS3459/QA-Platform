from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import json

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                if connection in self.active_connections:
                    self.active_connections.remove(connection)

manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        welcome_msg = json.dumps({
            "type": "connection",
            "message": "Connected to WebSocket",
            "status": "connected"
        })
        await manager.send_personal_message(welcome_msg, websocket)
        
        while True:
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                message_data = {"type": "message", "content": data}
            
            response = json.dumps({
                "type": "echo",
                "original": message_data,
                "message": "Message received"
            })
            await manager.send_personal_message(response, websocket)
            
            if message_data.get("broadcast", False):
                broadcast_msg = json.dumps({
                    "type": "broadcast",
                    "data": message_data,
                    "sender": "server"
                })
                await manager.broadcast(broadcast_msg)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        disconnect_msg = json.dumps({
            "type": "disconnect",
            "message": "A client disconnected"
        })
        await manager.broadcast(disconnect_msg)

