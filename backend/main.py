import asyncio
import logging
import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from agency_manager import AgencyManager
from constants import DATA_DIR

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)

app = FastAPI()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        # logging.FileHandler(DATA_DIR / "logs.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

agency_manager = AgencyManager()


@app.post("/create_agency")
async def create_agency():
    agency_id = uuid.uuid4().hex
    await agency_manager.create_agency(agency_id)
    return {"agency_id": agency_id}


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}  # session_id: websocket

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_message(self, message: str, session_id: str):
        websocket = self.active_connections[session_id]
        await websocket.send_text(message)


ws_manager = ConnectionManager()


@app.websocket("/ws/{agency_id}")
async def websocket_endpoint(websocket: WebSocket, agency_id: str):
    """Send messages to and from CEO of the given agency."""

    logger.info(f"WebSocket connected for agency_id: {agency_id}")
    await ws_manager.connect(websocket, agency_id)

    agency = agency_manager.get_agency(agency_id=agency_id)
    if not agency:
        await ws_manager.send_message("Agency not found", agency_id)
        ws_manager.disconnect(agency_id)
        await websocket.close(code=1003)
        return

    try:
        while True:
            user_message = await websocket.receive_text()
            try:
                if not user_message.strip():
                    await ws_manager.send_message("message not provided", agency_id)
                    ws_manager.disconnect(agency_id)
                    await websocket.close(code=1003)
                    return

                gen = await asyncio.to_thread(agency.get_completion, message=user_message, yield_messages=True)
                for response in gen:
                    response_text = response.get_formatted_content()
                    await ws_manager.send_message(response_text, agency_id)

            except Exception:
                logger.exception(f"Error in websocket_endpoint for agency_id: {agency_id}")
                ws_manager.disconnect(agency_id)
                await websocket.close(code=1003)

    except WebSocketDisconnect:
        ws_manager.disconnect(agency_id)
        logger.info(f"WebSocket disconnected for agency_id: {agency_id}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
