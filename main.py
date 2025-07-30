from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import stripe
import json

app = Flask(__name__)
CORS(app)

# Set your Stripe secret key
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Credit amount per Stripe Price ID
CREDIT_MAP = {
    "price_1RfxrCBOxFvaa5R8M5cKYvOM": 10,    # Standard
    "price_1RfxrBBOxFvaa5R8Dfvnov1z": 30,    # Premium
    "price_1RfxrBBOxFvaa5R8NGJ1SFHI": -1     # Pro (unlimited)
}

# 📥 Add credits to the user's account
def add_credits(email, price_id):
    try:
        with open("credits.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {"users": {}}

    user = data["users"].get(email, {"credits": 0, "plan": "", "purchases": []})

    credit_amt = CREDIT_MAP.get(price_id, 0)
    if credit_amt == -1:
        user["credits"] = -1
        user["plan"] = "pro"
    else:
        user["credits"] += credit_amt
        if credit_amt == 10:
            user["plan"] = "standard"
        elif credit_amt == 30:
            user["plan"] = "premium"

    user["purchases"].append(price_id)
    data["users"][email] = user

    with open("credits.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"[✔] Added {credit_amt} credits to {email}")

# ✅ Homepage health check
@app.route("/")
def index():
    return "CallRecall Backend is live!"

# ✅ Stripe Checkout session
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
            cancel_url=os.getenv("DOMAIN") + "/cancel.html",
            customer_email=data.get("email")  # optional if you're passing it
        )
        return jsonify({"url": session.url})

    except Exception as e:
        return jsonify(error=str(e)), 403

# ✅ Webhook for successful payments
@app.route("/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError:
        return "Invalid signature", 400
    except Exception as e:
        print("Webhook error:", e)
        return "Webhook error", 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        email = session.get("customer_email")
        line_items = session.get("display_items") or []
        price_id = None

        if line_items:
            price_id = line_items[0].get("price", {}).get("id")
        elif session.get("line_items"):
            price_id = session["line_items"][0]["price"]["id"]

        if email and price_id:
            add_credits(email, price_id)
            print(f"[WEBHOOK] Assigned credits for {email} - {price_id}")
        else:
            print("[WEBHOOK] Missing email or price_id")

    return "", 200
