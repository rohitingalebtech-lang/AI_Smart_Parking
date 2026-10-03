from database import get_booked_slots


slots = {

    "A1": {"distance": 10, "covered": True, "busy": 30, "size": "normal"},
    "A2": {"distance": 15, "covered": False, "busy": 70, "size": "large"},
    "A3": {"distance": 20, "covered": True, "busy": 40, "size": "normal"},
    "A4": {"distance": 25, "covered": False, "busy": 60, "size": "large"},
    "A5": {"distance": 30, "covered": True, "busy": 50, "size": "normal"},

    "B1": {"distance": 15, "covered": True, "busy": 35, "size": "large"},
    "B2": {"distance": 20, "covered": False, "busy": 45, "size": "normal"},
    "B3": {"distance": 25, "covered": True, "busy": 65, "size": "large"},
    "B4": {"distance": 30, "covered": False, "busy": 55, "size": "normal"},
    "B5": {"distance": 35, "covered": True, "busy": 40, "size": "large"},

    "C1": {"distance": 20, "covered": False, "busy": 50, "size": "normal"},
    "C2": {"distance": 25, "covered": True, "busy": 35, "size": "large"},
    "C3": {"distance": 30, "covered": False, "busy": 45, "size": "normal"},
    "C4": {"distance": 35, "covered": True, "busy": 70, "size": "large"},
    "C5": {"distance": 40, "covered": False, "busy": 30, "size": "normal"}

}


def recommend_slot(
    weather,
    event,
    occupancy,
    vehicle_type="Car"
):

    booked_slots = get_booked_slots()

    best_slot = None
    best_score = -1


    for slot, info in slots.items():

        # Do not recommend booked slots
        if slot in booked_slots:
            continue


        score = 100


        # Distance
        score -= info["distance"] * 0.25


        # Congestion
        score -= info["busy"] * 0.35


        # Rain/weather
        if weather == 1:

            if info["covered"]:
                score += 30

            else:
                score -= 15


        # Special event
        if event == 1:

            score -= info["busy"] * 0.25


        # Current occupancy
        if occupancy >= 80:

            score -= info["busy"] * 0.30

        elif occupancy >= 60:

            score -= info["busy"] * 0.15


        # Vehicle type
        if vehicle_type == "SUV":

            if info["size"] == "large":
                score += 15


        elif vehicle_type == "Bike":

            if info["distance"] <= 25:
                score += 10


        elif vehicle_type == "Car":

            if info["size"] == "normal":
                score += 5


        # Select best slot
        if score > best_score:

            best_score = score
            best_slot = slot


    # No available slot
    if best_slot is None:

        return "FULL", 0


    return best_slot, round(best_score, 2)