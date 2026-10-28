from seat_agent import receive_message
from fastapi.testclient import TestClient
import seat_agent
from rebooking_agent import send_message
import rebooking_agent


def test_booking_completes():
    body = {"jsonrpc": "2.0", "id": 1, "method": "message/send",
            "params": {"message": {"role": "user", "messageId": "m-1",
                       "parts": [{"kind": "text", "text": "Book a seat on UA200"}]}}}
    reply = receive_message(body)
    assert reply["result"]["status"]["state"] == "completed"

def test_unknown_flight_fails():
    body = {"jsonrpc": "2.0", "id": 1, "method": "message/send",
            "params": {"message": {"role": "user", "messageId": "m-2",
                                   "parts": [{"kind": "text", "text": "Book a seat on ABC123"}]}}}
    reply = receive_message(body)
    assert reply["result"]["status"]["state"] == "failed"

def test_sold_out_fails():
    body = {"jsonrpc": "2.0", "id": 1, "method": "message/send",
            "params": {"message": {"role": "user", "messageId": "m-3",
                                   "parts": [{"kind": "text", "text": "Book a seat on UA300"}]}}}
    first = receive_message(body)
    body["params"]["message"]["messageId"] = "m-4"
    second = receive_message(body)
    assert first["result"]["status"]["state"] == "completed"
    assert second["result"]["status"]["state"] == "failed"

def test_duplicate_returns_same_reply():
    body = {"jsonrpc": "2.0", "id": 1, "method": "message/send",
            "params": {"message": {"role": "user", "messageId": "m-5",
                                   "parts": [{"kind": "text", "text": "Book a seat on UA200"}]}}}
    first = receive_message(body)
    second = receive_message(body)
    assert first == second

def test_retry_then_success():
    seat_agent.processed.clear()
    seat_agent.free_seats["UA200"] = ["10c"]
    seat_agent.fail_next = 2
    reply = send_message("Book a seat on UA200", client=TestClient(seat_agent.app))
    assert reply["result"]["status"]["state"] == "completed"
    assert seat_agent.fail_next == 0

def test_outage_breaker_and_recovery():
    seat_agent.processed.clear()
    seat_agent.free_seats["UA200"] = ["10c"]
    rebooking_agent.failed_calls = 0
    rebooking_agent.dead_letters.clear()
    client = TestClient(seat_agent.app)

    seat_agent.fail_next = 100
    for i in range(4):
        send_message("Book a seat on UA200", client=client)
    assert rebooking_agent.failed_calls == 3
    assert len(rebooking_agent.dead_letters) == 4

    seat_agent.fail_next = 0
    rebooking_agent.replay_dead_letters(client)
    assert rebooking_agent.dead_letters == []
    assert seat_agent.free_seats["UA200"] == []
