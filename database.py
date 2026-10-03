import sqlite3
from datetime import datetime, timedelta, timezone

DATABASE = "parking.db"


def create_database():

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_number TEXT NOT NULL,
            vehicle_type TEXT NOT NULL,
            slot TEXT NOT NULL,
            duration INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            booking_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Add payment status for existing databases
    columns = [
        row[1]
        for row in cursor.execute(
            "PRAGMA table_info(bookings)"
        ).fetchall()
    ]

    if "payment_status" not in columns:
        cursor.execute("""
            ALTER TABLE bookings
            ADD COLUMN payment_status TEXT DEFAULT 'PENDING'
        """)

    conn.commit()
    conn.close()


def remove_expired_bookings():

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, booking_time, duration
        FROM bookings
    """)

    bookings = cursor.fetchall()

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    for booking in bookings:

        booking_id = booking[0]
        booking_time = booking[1]
        duration = booking[2]

        try:

            booking_datetime = datetime.strptime(
                str(booking_time),
                "%Y-%m-%d %H:%M:%S"
            )

            expiry_time = (
                booking_datetime +
                timedelta(hours=duration)
            )

            if now >= expiry_time:

                cursor.execute("""
                    DELETE FROM bookings
                    WHERE id = ?
                """, (booking_id,))

        except Exception:
            pass

    conn.commit()
    conn.close()


def add_booking(
    vehicle_number,
    vehicle_type,
    slot,
    duration,
    amount
):

    remove_expired_bookings()

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM bookings
        WHERE slot = ?
    """, (slot,))

    if cursor.fetchone():

        conn.close()
        return False

    cursor.execute("""
        INSERT INTO bookings
        (
            vehicle_number,
            vehicle_type,
            slot,
            duration,
            amount,
            payment_status
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        vehicle_number,
        vehicle_type,
        slot,
        duration,
        amount,
        "PENDING"
    ))

    booking_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return booking_id


def get_booking_by_id(booking_id):

    remove_expired_bookings()

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM bookings
        WHERE id = ?
    """, (booking_id,))

    booking = cursor.fetchone()

    conn.close()

    return booking


def update_payment_status(booking_id, status):

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE bookings
        SET payment_status = ?
        WHERE id = ?
    """, (status, booking_id))

    conn.commit()
    conn.close()


def get_bookings():

    remove_expired_bookings()

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM bookings
        ORDER BY booking_time DESC
    """)

    bookings = cursor.fetchall()

    conn.close()

    return bookings


def get_booked_slots():

    remove_expired_bookings()

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT slot
        FROM bookings
    """)

    slots = [
        row[0]
        for row in cursor.fetchall()
    ]

    conn.close()

    return slots


def is_slot_available(slot):

    remove_expired_bookings()

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM bookings
        WHERE slot = ?
    """, (slot,))

    result = cursor.fetchone()

    conn.close()

    return result is None


if __name__ == "__main__":

    create_database()

    print("✅ Smart Parking database ready!")