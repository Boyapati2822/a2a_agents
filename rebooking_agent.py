import httpx
import time


failed_calls = 0
BREAKER_LIMIT = 3
dead_letters = []

def get_card(client=httpx):
    response = client.get("http://localhost:8001/.well-known/agent-card.json")
    return response.json()


def send_message(text, client=httpx):
    global failed_calls
    if failed_calls >= BREAKER_LIMIT:
        dead_letters.append(text)
        return None
    card = get_card(client)
    part = {"kind": "text", "text": text}
    message = {"role":"user", "messageId":"m-1", "parts": [part]}
    body = {"jsonrpc": "2.0", "id": 1, "method": "message/send", "params": {"message": message}}
    for attempt in range(3):
        response = client.post(card["url"], json=body)
        if response.status_code == 200:
            failed_calls = 0
            return response.json()
        time.sleep(1)
    failed_calls += 1
    dead_letters.append(text)
    return None

def replay_dead_letters(client=httpx):
    global failed_calls
    failed_calls = 0
    waiting = dead_letters.copy()
    dead_letters.clear()
    for text in waiting:
        send_message(text, client)

if __name__ == "__main__":
    reply = send_message("Book a seat on UA200")
    state = reply["result"]["status"]["state"]
    text = reply["result"]["artifacts"][0]["parts"][0]["text"]
    print(state, text)
