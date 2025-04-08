import json

booking_id = "lwhefkj32bkj"
message = f'{{"booking_id": "{booking_id}"}}'
data = json.loads(message)
booking_id = data.get("booking_id")
print(booking_id)
