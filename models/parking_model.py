import pandas as pd
from sklearn.ensemble import RandomForestRegressor

# Parking dataset
data = {
    "day": [0, 1, 2, 3, 4, 5, 6] * 10,
    "hour": [9, 11, 13, 15, 17, 19, 21] * 10,
    "weather": [0, 0, 1, 0, 1, 0, 0] * 10,
    "event": [0, 0, 0, 0, 1, 1, 0] * 10,
    "occupancy": [35, 40, 45, 50, 65, 85, 55] * 10
}

df = pd.DataFrame(data)

X = df[["day", "hour", "weather", "event"]]
y = df["occupancy"]

# AI model
model = RandomForestRegressor(
    n_estimators=10,
    random_state=42
)

model.fit(X, y)


def predict_occupancy(day, hour, weather, event):

    input_data = pd.DataFrame(
        [[day, hour, weather, event]],
        columns=["day", "hour", "weather", "event"]
    )

    prediction = model.predict(input_data)[0]

    return round(prediction, 2)