import streamlit as st
import json
from datetime import datetime

# ----------------------------
# Load and Save Database
# ----------------------------
def load_db():
    try:
        with open("database.json", "r") as f:
            return json.load(f)
    except:
        return {"users": {}}

def save_db(data):
    with open("database.json", "w") as f:
        json.dump(data, f, indent=4)

db = load_db()

# ----------------------------
# Register User
# ----------------------------
def register_user(email, password):
    if email in db["users"]:
        return False, "User already exists."

    db["users"][email] = {
        "password": password,
        "balance": 1000.0,
        "transactions": []
    }
    save_db(db)
    return True, "Registration successful!"

# ----------------------------
# Login Function
# ----------------------------
def login_user(email, password):
    if email not in db["users"]:
        return False, "User not found."
    if db["users"][email]["password"] != password:
        return False, "Incorrect password."

    st.session_state["logged_in"] = True
    st.session_state["email"] = email
    return True, "Login successful!"

# ----------------------------
# Send Money
# ----------------------------
def send_money(sender, receiver, amount):
    if receiver not in db["users"]:
        return False, "Receiver not found."

    if db["users"][sender]["balance"] < amount:
        return False, "Insufficient funds."

    # Update balances
    db["users"][sender]["balance"] -= amount
    db["users"][receiver]["balance"] += amount

    # Log Transactions
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db["users"][sender]["transactions"].append({
        "type": "sent",
        "to": receiver,
        "amount": amount,
        "time": timestamp
    })

    db["users"][receiver]["transactions"].append({
        "type": "received",
        "from": sender,
        "amount": amount,
        "time": timestamp
    })

    save_db(db)
    return True, "Transaction successful!"

# ----------------------------
# Wallet Dashboard
# ----------------------------
def dashboard():
    st.header("Your Wallet")

    user = st.session_state["email"]
    data = db["users"][user]

    st.subheader(f"Balance: ${data['balance']} TTD")

    st.write("---")

    st.subheader("Send Money")

    receiver = st.text_input("Receiver Email")
    amount = st.number_input("Amount", min_value=1.0)

    if st.button("Send"):
        success, msg = send_money(user, receiver, amount)
        if success:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

    st.write("---")
    st.subheader("Transaction History")

    for tx in reversed(db["users"][user]["transactions"]):
        if tx["type"] == "sent":
            st.error(f"Sent ${tx['amount']} → {tx['to']} ({tx['time']})")
        else:
            st.success(f"Received ${tx['amount']} ← {tx['from']} ({tx['time']})")

    st.write("---")
    if st.button("Logout"):
        st.session_state["logged_in"] = False
        st.rerun()

# ----------------------------
# Main UI
# ----------------------------
st.title("InstacashTT — Digital Wallet (TTD)")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

menu = st.selectbox("Menu", ["Login", "Register"])

# LOGIN PAGE
if not st.session_state["logged_in"]:

    if menu == "Login":
        st.header("Login to Your Wallet")

        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            success, msg = login_user(email, password)
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    # REGISTER PAGE
    if menu == "Register":
        st.header("Create Your Wallet")

        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Register"):
            ok, msg = register_user(email, password)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

# If logged in → show dashboard
if st.session_state["logged_in"]:
    dashboard()
