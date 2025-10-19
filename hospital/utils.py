from datetime import time, datetime, timedelta


def generate_time_slots(start_time, end_time, slot_duration=60):
    """Generate slots for doctors"""

    slots = []
    current_time = start_time

    while current_time < end_time:
        slots.append(current_time.strftime('%H:%M'))
        # Add slot duration minutes
        current_time = (datetime.combine(datetime.today(), current_time) + timedelta(minutes=slot_duration)).time()

    return slots