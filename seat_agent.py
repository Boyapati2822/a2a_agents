import os
from fastapi import FastAPI, HTTPException
from mangum import Mangum

app = FastAPI()
handler = Mangum(app)


@app.get("/.well-known/agent-card.json")
def agent_card():
    return {
        "name": "Seat Agent",
        "description": "Books seats on flights",
        "url": os.environ.get("AGENT_URL", "http://localhost:8001"),
        "version": "1.0",
        "skills": [
            {
                "id": "book_seat",
                "name": "Book seat",
                "description": "Books a seat for a PNR on a flight",
            }
        ],
    }


processed = {}
bookings = []
free_seats = {"UA200": ["10c", "20b"], "UA300": ["10b"]}
fail_next = 0


@app.post("/")
def receive_message(request: dict):
    global fail_next
    if fail_next > 0:
        fail_next = fail_next - 1
        raise HTTPException(status_code=503)

    text = request["params"]["message"]["parts"][0]["text"]

    messageId = request["params"]["message"]["messageId"]
    if messageId in processed:
        return processed[messageId]

    Flight = None
    for f in free_seats:
        if f in text:
            Flight = f

    if Flight is None:
        return send_response(request, "failed", "flight is not available")
    elif free_seats[Flight]:
        seat = free_seats[Flight].pop(0)
        return send_response(request, "completed", f"Seat {seat} booked on {Flight}")
    else:
        return send_response(request, "failed", "Booking is not completed")


def send_response(request, state, text):
    reply = {
        "jsonrpc": "2.0",
        "id": request["id"],
        "result": {
            "id": "task-1",
            "status": {"state": state},
            "artifacts": [{"parts": [{"kind": "text", "text": text}]}],
        },
    }
    processed[request["params"]["message"]["messageId"]] = reply
    return reply
