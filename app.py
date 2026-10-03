from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from datetime import datetime, timedelta

from models.parking_model import predict_occupancy
from models.recommendation import recommend_slot

from database import (
    create_database,
    add_booking,
    get_bookings,
    get_booking_by_id,
    update_payment_status,
    get_booked_slots,
    is_slot_available
)

app = Flask(__name__)

create_database()

# ==================================================
# PARKING CONFIGURATION
# ==================================================

VALID_SLOTS = [
    "A1", "A2", "A3", "A4", "A5",
    "B1", "B2", "B3", "B4", "B5",
    "C1", "C2", "C3", "C4", "C5"
]

TOTAL_SLOTS = len(VALID_SLOTS)


# ==================================================
# LEGACY PAGE REDIRECTS
# ==================================================

@app.before_request
def redirect_old_pages():

    old_path = request.path.rstrip("/")

    if old_path == "/static/my_booking.html":
        return redirect(url_for("my_booking"))

    if old_path in [
        "/static/admin.html",
        "/static/dashboard.html",
        "/static/ai_recommendation.html",
        "/static/live_parking.html",
        "/static/dynamic_pricing.html"
    ]:
        return redirect(url_for("owner"))

    if old_path == "/static/booking.html":
        return redirect(url_for("booking"))


# ==================================================
# PRICE CALCULATION
# ==================================================

def calculate_price(
    occupancy,
    duration,
    weather=0,
    event=0
):

    if occupancy >= 80:
        hourly_price = 80

    elif occupancy >= 60:
        hourly_price = 60

    else:
        hourly_price = 40

    if weather == 1:
        hourly_price += 10

    if event == 1:
        hourly_price += 10

    total_amount = hourly_price * duration

    return hourly_price, total_amount


# ==================================================
# HOME
# ==================================================

@app.route("/", methods=["GET", "POST"])
def home():

    prediction = None
    recommended_slot = None
    score = None
    price = None

    if request.method == "POST":

        try:

            day = int(request.form["day"])
            hour = int(request.form["hour"])
            weather = int(request.form["weather"])
            event = int(request.form["event"])

            vehicle_type = request.form.get(
                "vehicle_type",
                "Car"
            )

            prediction = predict_occupancy(
                day,
                hour,
                weather,
                event
            )

            recommended_slot, score = recommend_slot(
                weather,
                event,
                prediction,
                vehicle_type
            )

            price, _ = calculate_price(
                prediction,
                1,
                weather,
                event
            )

        except Exception as error:

            print(
                "Prediction error:",
                error
            )

    return render_template(
        "index.html",
        prediction=prediction,
        recommended_slot=recommended_slot,
        score=score,
        price=price
    )


# ==================================================
# FIND PARKING
# ==================================================

@app.route("/parking")
def parking():

    return render_template(
        "parking.html"
    )


# ==================================================
# BOOKING PAGE
# ==================================================

@app.route("/booking")
def booking():

    selected_slot = request.args.get(
        "slot",
        ""
    )

    parking_name = request.args.get(
        "parking",
        "SmartPark Station"
    )

    return render_template(
        "booking.html",
        selected_slot=selected_slot,
        parking_name=parking_name,
        valid_slots=VALID_SLOTS
    )


# ==================================================
# MY BOOKING
# ==================================================

@app.route("/my-booking")
def my_booking():

    return send_from_directory(
        app.static_folder,
        "my_booking.html"
    )


# ==================================================
# OWNER + AI CENTER
# ==================================================

@app.route("/owner")
def owner():

    return render_template(
        "owner.html"
    )


# ==================================================
# PARKING STATUS API
# ==================================================

@app.route(
    "/api/parking-status",
    methods=["GET"]
)
def parking_status():

    booked_slots = get_booked_slots()

    booked_slots = [
        slot
        for slot in booked_slots
        if slot in VALID_SLOTS
    ]

    occupied = len(booked_slots)

    available = (
        TOTAL_SLOTS -
        occupied
    )

    return jsonify({
        "total": TOTAL_SLOTS,
        "occupied": occupied,
        "available": available,
        "reserved": 0,
        "booked_slots": booked_slots
    })


# ==================================================
# BOOKING API
# ==================================================

@app.route(
    "/api/book",
    methods=["POST"]
)
def book():

    try:

        data = request.get_json()

        if not data:

            return jsonify({
                "success": False,
                "message":
                "No booking information received."
            }), 400

        vehicle_number = data.get(
            "vehicle_number"
        )

        vehicle_type = data.get(
            "vehicle_type"
        )

        slot = data.get(
            "slot"
        )

        duration = int(
            data.get("duration")
        )

        if (
            not vehicle_number
            or not vehicle_type
            or not slot
        ):

            return jsonify({
                "success": False,
                "message":
                "Please fill all booking details."
            }), 400

        vehicle_number = (
            vehicle_number
            .strip()
            .upper()
        )

        slot = (
            slot
            .strip()
            .upper()
        )

        if len(vehicle_number) < 4:

            return jsonify({
                "success": False,
                "message":
                "Please enter a valid vehicle number."
            }), 400

        if duration < 1 or duration > 4:

            return jsonify({
                "success": False,
                "message":
                "Parking duration must be between 1 and 4 hours."
            }), 400

        if slot not in VALID_SLOTS:

            return jsonify({
                "success": False,
                "message":
                "Invalid parking slot."
            }), 400

        if not is_slot_available(slot):

            return jsonify({
                "success": False,
                "message":
                f"Slot {slot} is already booked."
            }), 409

        booked_slots = get_booked_slots()

        booked_slots = [
            s
            for s in booked_slots
            if s in VALID_SLOTS
        ]

        occupancy = (
            len(booked_slots)
            /
            TOTAL_SLOTS
        ) * 100

        hourly_price, amount = calculate_price(
            occupancy,
            duration
        )

        booking_id = add_booking(
            vehicle_number,
            vehicle_type,
            slot,
            duration,
            amount
        )

        if not booking_id:

            return jsonify({
                "success": False,
                "message":
                f"Slot {slot} became unavailable."
            }), 409

        return jsonify({
            "success": True,
            "message":
            "Booking created successfully.",
            "booking_id":
            booking_id,
            "vehicle_number":
            vehicle_number,
            "vehicle_type":
            vehicle_type,
            "slot":
            slot,
            "duration":
            duration,
            "hourly_price":
            hourly_price,
            "amount":
            amount
        })

    except (
        TypeError,
        ValueError
    ):

        return jsonify({
            "success": False,
            "message":
            "Please enter valid booking details."
        }), 400

    except Exception as error:

        print(
            "Booking error:",
            error
        )

        return jsonify({
            "success": False,
            "message":
            "Unable to process booking."
        }), 500


# ==================================================
# ALL BOOKINGS API
# ==================================================

@app.route(
    "/api/bookings",
    methods=["GET"]
)
def bookings():

    data = get_bookings()

    bookings_list = []

    for booking in data:

        bookings_list.append({
            "id": booking[0],
            "vehicle_number": booking[1],
            "vehicle_type": booking[2],
            "slot": booking[3],
            "duration": booking[4],
            "amount": booking[5],
            "booking_time": booking[6],
            "payment_status": booking[7]
        })

    return jsonify(
        bookings_list
    )


# ==================================================
# PAYMENT
# ==================================================

@app.route(
    "/payment/<int:booking_id>"
)
def payment(booking_id):

    booking_data = get_booking_by_id(
        booking_id
    )

    if not booking_data:

        return "Booking not found.", 404

    return render_template(
        "payment.html",
        booking=booking_data
    )


# ==================================================
# COMPLETE DEMO PAYMENT
# ==================================================

@app.route(
    "/api/payment/<int:booking_id>",
    methods=["POST"]
)
def complete_payment(booking_id):

    booking_data = get_booking_by_id(
        booking_id
    )

    if not booking_data:

        return jsonify({
            "success": False,
            "message":
            "Booking not found."
        }), 404

    update_payment_status(
        booking_id,
        "PAID"
    )

    return jsonify({
        "success": True,
        "message":
        "Demo payment completed.",
        "booking_id":
        booking_id
    })


# ==================================================
# CONFIRMATION
# ==================================================

@app.route(
    "/confirmation/<int:booking_id>"
)
def confirmation(booking_id):

    booking_data = get_booking_by_id(
        booking_id
    )

    if not booking_data:

        return "Booking not found.", 404

    booking_time = datetime.strptime(
        str(booking_data[6]),
        "%Y-%m-%d %H:%M:%S"
    )

    expiry_time = (
        booking_time
        +
        timedelta(
            hours=booking_data[4]
        )
    )

    booking = {

        "id":
        booking_data[0],

        "reference":
        f"SP-{booking_data[0]:05d}",

        "vehicle_number":
        booking_data[1],

        "vehicle_type":
        booking_data[2],

        "slot":
        booking_data[3],

        "duration":
        booking_data[4],

        "amount":
        booking_data[5],

        "booking_time":
        booking_data[6],

        "expiry_time":
        expiry_time.strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

        "payment_status":
        booking_data[7]
    }

    return render_template(
        "confirmation.html",
        booking=booking
    )


# ==================================================
# AI OCCUPANCY PREDICTION
# ==================================================

@app.route(
    "/api/ai-predict",
    methods=["POST"]
)
def ai_predict():

    try:

        data = request.get_json()

        day = int(
            data.get("day", 0)
        )

        hour = int(
            data.get("hour", 9)
        )

        weather = int(
            data.get("weather", 0)
        )

        event = int(
            data.get("event", 0)
        )

        prediction = predict_occupancy(
            day,
            hour,
            weather,
            event
        )

        return jsonify({

            "success": True,

            "prediction":
            prediction

        })

    except Exception as error:

        print(
            "AI prediction error:",
            error
        )

        return jsonify({

            "success": False,

            "message":
            "Unable to generate prediction."

        }), 400


# ==================================================
# AI SLOT RECOMMENDATION
# ==================================================

@app.route(
    "/api/ai-recommend",
    methods=["POST"]
)
def ai_recommend():

    try:

        data = request.get_json()

        vehicle_type = data.get(
            "vehicle_type",
            "Car"
        )

        weather = int(
            data.get("weather", 0)
        )

        event = int(
            data.get("event", 0)
        )

        booked_slots = get_booked_slots()

        occupancy = (
            len(booked_slots)
            /
            TOTAL_SLOTS
        ) * 100

        slot, score = recommend_slot(

            weather,
            event,
            occupancy,
            vehicle_type

        )

        if slot == "FULL":

            return jsonify({

                "success": False,

                "message":
                "All parking slots are occupied."

            })

        return jsonify({

            "success": True,

            "slot":
            slot,

            "score":
            score

        })

    except Exception as error:

        print(
            "AI recommendation error:",
            error
        )

        return jsonify({

            "success": False,

            "message":
            "Unable to generate recommendation."

        }), 400


# ==================================================
# START SERVER
# ==================================================

if __name__ == "__main__":

    app.run(
        debug=False,
        use_reloader=False
    )