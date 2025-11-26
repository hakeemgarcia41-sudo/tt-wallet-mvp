import streamlit as st
import json
import os
from datetime import datetime

DB_FILE = "database.json"

# ---------------------------------------------------------
# Load & Save Database
# ---------------------------------------------------------
def load_db():
    if not os.path.exists(DB_FILE):
        return {"users": {}}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)

# ---------------------------------------------------------
# Register User
# ---------------------------------------------------------
def register_user():
    st.subheader("Create a New Wallet Account")

    email = st.text_input("Email")
    name = st.text_input("Full Name")
    password = st.text_input("Password", type="password")

    if st.button("Register"):
        db = load_db()

        if email in db["users"]:
            st.error("This email is already registered.")
            return

        db["users"][email] = {
            "name": name,
            "password": password,
            "balance": 100.00,
            "transactions": []
        }

        save_db(db)
        st.success("Account created successfully! You can now log in.")

# ---------------------------------------------------------
# Login
# ---------------------------------------------------------
def login():
    st.subheader("Login to Your Wallet")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        db = load_db()

        if email not in db["users"]:
            st.error("Account not found.")
            return

        if db["users"][email]["password"] != password:
            st.error("Incorrect password.")
            return

        st.session_state.logged_in = True
        st.session_state.email = email
        st.success("Login successful!")
        st.experimental_rerun()

# ---------------------------------------------------------
# Send Money
# ---------------------------------------------------------
def send_money():
    st.subheader("Send Money")

    db = load_db()
    sender = st.session_state.email
    sender_data = db["users"][sender]

    recipient = st.text_input("Receiver Email")
    amount = st.number_input("Amount (TTD)", min_value=1.0, step=1.0)

    if st.button("Send"):
        if recipient not in db["users"]:
            st.error("Receiver not found.")
            return

        if sender_data["balance"] < amount:
            st.error("Insufficient balance.")
            return

        # Process transfer
        sender_data["balance"] -= amount
        db["users"][recipient]["balance"] += amount

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Transaction records
        sender_data["transactions"].append({
            "type": "sent",
            "amount": amount,
            "to": recipient,
            "time": timestamp
        })

        db["users"][recipient]["transactions"].append({
            "type": "received",
            "amount": amount,
            "from": sender,
            "time": timestamp
        })

        save_db(db)
        st.success(f"Successfully sent ${amount} TTD to {recipient}!")

# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------
def dashboard():
    db = load_db()
    email = st.session_state.email
    user = db["users"][email]

    st.title("💳 InstacashTT — Your Digital Wallet")

    st.subheader("Wallet Overview")
    st.write(f"**Name:** {user['name']}")
    st.write(f"**Email:** {email}")
    st.write(f"**Balance:** ${user['balance']:.2f}")

    st.markdown("---")

    # Send money section
    send_money()

    st.markdown("---")
    st.subheader("📜 Transaction History")

    if not user["transactions"]:
        st.info("No transactions yet.")
    else:
        for tx in reversed(user["transactions"]):
            if tx["type"] == "sent":
                st.error(f"Sent ${tx['amount']} to {tx['to']} — {tx['time']}")
            else:
                st.success(f"Received ${tx['amount']} from {tx['from']} — {tx['time']}")

    st.markdown("---")
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.experimental_rerun()

# ---------------------------------------------------------
# Main App UI
# ---------------------------------------------------------
def main():
    st.set_page_config(page_title="InstacashTT Wallet", layout="wide")

    st.title("💳 InstacashTT — Digital Wallet (TTD)")

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        menu = ["Login", "Register"]
        choice = st.selectbox("Menu", menu)

        if choice == "Login":
            login()
        else:
            register_user()
    else:
        dashboard()

if __name__ == "__main__":
    main()
