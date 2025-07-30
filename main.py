from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import stripe

app = Flask(__name__)
CORS(app)

# Load Stripe secret key from environment
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

@app.route("/")
def index():
    return "CallRecall Backend is live!"

@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    try:
        data = request.get_json()

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price": data["priceId"],
                "quantity": 1
            }],
            mode="payment",
            success_url=os.getenv("DOMAIN") + "/success.html",
            cancel_url=os.getenv("DOMAIN") + "/cancel.html"
        )
        return jsonify({"url": session.url})

    except Exception as e:
        return jsonify(error=str(e)), 403
