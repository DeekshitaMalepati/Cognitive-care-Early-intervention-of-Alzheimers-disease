from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from keras.models import load_model
from keras.preprocessing import image
from keras.metrics import AUC
from PIL import Image
import numpy as np
import pyrebase
import os
from config import firebase_config

app = Flask(__name__)
firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()
db = firebase.database()

dependencies = {"auc_roc": AUC}
person = {"is_logged_in": False, "name": "", "email": "", "uid": ""}

verbose_name = {
    0: "Mild Demented",
    1: "Moderate Demented",
    2: "Non Demented",
    3: "Very Mild Demented",
}

# Select model
model = load_model(r"adp.h5", compile=False)

model.make_predict_function()


def predict_label(img_path):
    test_image = image.load_img(img_path,target_size=(180, 180))
    from keras.applications.mobilenet_v2 import preprocess_input

    x = image.img_to_array(test_image)
    import numpy as np
    x = np.expand_dims(x, axis=0)
    img_data = preprocess_input(x)

    predict_x = model.predict(img_data)
    classes_x = np.argmax(predict_x, axis=1)

    return verbose_name[classes_x[0]]


@app.route("/login")
def login():
    return render_template("login.html")


@app.route('/logout')
def logout():
    person["is_logged_in"] = False
    return redirect("/")


@app.route("/signup")
def signup():
    return render_template("register.html")


@app.route("/", methods=["GET", "POST"])
def main():
    return render_template("index.html", person=person)


@app.route("/submit", methods=["GET", "POST"])
def get_output():
    if request.method == "POST":
        img = request.files["my_image"]

        img_path ="static/tests/" + img.filename
        img.save(img_path)

        predict_result = predict_label(img_path)

    if person["is_logged_in"]:
        data = {
            "result": predict_result,
            "image_path": img_path,
            "created_at": str(datetime.now().strftime("%Y-%m-%d")),
        }
        db.child("alzheimer_results").child(person["uid"]).push(data)

    return render_template(
        "index.html", prediction=predict_result, img_path=img_path, person=person
    )


@app.route("/previous-results", methods=["GET", "POST"])
def previous_results():
    if person["is_logged_in"]:
        data = db.child("alzheimer_results").get()
        results = data.val()[person["uid"]]
        return render_template("previous_results.html", results=results, person=person)
    return render_template("index.html", person=person)


@app.route("/auth/token", methods=["POST", "GET"])
def token():
    if request.method == "POST":
        result = request.form
        email, password = result["email"], result["password"]
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            person["is_logged_in"] = True
            person["email"] = user["email"]
            person["uid"] = user["localId"]

            data = db.child("users").get()
            person["name"] = data.val()[person["uid"]]["name"]

            user = auth.refresh(user["refreshToken"])
            user_id = user["idToken"]
            session["usr"] = user_id


            return redirect(url_for("main"))
        except:
            return redirect(url_for("login"))
    else:
        if person["is_logged_in"]:
            return redirect(url_for("main"))
        else:
            return redirect(url_for("login"))


@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        result = request.form
        email, password, name = result["email"], result["password"], result["name"]
        try:
            auth.create_user_with_email_and_password(email, password)
            user = auth.sign_in_with_email_and_password(email, password)

            person["is_logged_in"] = True
            person["email"] = user["email"]
            person["uid"] = user["localId"]
            person["name"] = name

            data = {"name": name, "email": email}
            db.child("users").child(person["uid"]).set(data)

            user = auth.refresh(user["refreshToken"])
            user_id = user["idToken"]
            session["usr"] = user_id


            return redirect(url_for("main"))
        except:
            return redirect(url_for("signup"))
    else:
        if person["is_logged_in"]:
            return redirect(url_for("main"))
        else:
            return redirect(url_for("signup"))


if __name__ == "__main__":
    app.run(debug=True)