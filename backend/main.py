from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import random
from typing import List
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_connections: List[WebSocket] = []

class DataGenerator:
    def __init__(self):
        self.value = 50

    async def generate_data(self):
        change = random.uniform(-5, 5)
        self.value = max(0, min(100, self.value + change))
        return round(self.value, 2)

data_generator = DataGenerator()

async def broadcast_data():
    while True:
        data = await data_generator.generate_data()
        if active_connections:
            await asyncio.gather(
                *[connection.send_json({"value": data}) for connection in active_connections]
            )
        await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(broadcast_data())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = f"Client said: {data}"
            await websocket.send_json({"message": message})
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)

@app.get("/current_value")
async def get_current_value():
    return {"value": round(data_generator.value, 2)}

class UpdateValue(BaseModel):
    new_value: float

@app.post("/update_value")
async def update_value(update: UpdateValue):
    if 0 <= update.new_value <= 100:
        data_generator.value = update.new_value
        return {"message": "Value updated successfully"}
    else:
        raise HTTPException(status_code=400, detail="Value must be between 0 and 100")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)