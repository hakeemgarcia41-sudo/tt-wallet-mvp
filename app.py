import streamlit as st
import json, os
from datetime import datetime

DB_FILE = "database.json"

# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------

def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({"users": {}, "transactions": {}}, f)
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)

def ensure_transaction_key(db, email):
    """Prevents KeyError by ensuring every user has a transaction list."""
    if email not in db["transactions"]:
        db["transactions"][email] = []
        save_db(db)

def create_user(email, password):
    db = load_db()

    if email in db["users"]:
        return False, "User already exists."

    db["users"][email] = {
        "password": password,
        "balance": 1000.0  # initial balance
    }

    db["transactions"][email] = []  # SAFE: ensure key exists
    save_db(db)

    return True, "Registration successful!"

def authenticate(email, password):
    db = load_db()
    if email in db["users"] and db["users"][email]["password"] == password:
        return True
    return False

# ---------------------------------------------------------
# MAIN APP
# ---------------------------------------------------------

st.set_page_config(page_title="InstacashTT Wallet (TTD)", layout="wide")

st.markdown("## 💳 InstacashTT — Digital Wallet (TTD)")

menu = st.selectbox("Menu", ["Login", "Register"])

# ---------------------------------------------------------
# REGISTER
# ---------------------------------------------------------
if menu == "Register":
    st.subheader("Create Your Wallet")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Register"):
        ok, msg = create_user(email, password)
        if ok:
            st.success(msg)
        else:
            st.error(msg)

# ---------------------------------------------------------
# LOGIN
# ---------------------------------------------------------
if menu == "Login":
    st.subheader("Login to Your Wallet")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if authenticate(email, password):
            st.session_state.logged_in = True
            st.session_state.email = email
            st.success("Login successful!")
        else:
            st.error("Invalid login details.")

# ---------------------------------------------------------
# AUTHENTICATED USER DASHBOARD
# ---------------------------------------------------------
if st.session_state.get("logged_in"):

    email = st.session_state.email
    db = load_db()
    ensure_transaction_key(db, email)

    user = db["users"][email]

    st.markdown("## Your Wallet")
    st.markdown(f"### Balance: **${user['balance']} TTD**")

    # ---------------------------------------------------------
    # SEND MONEY
    # ---------------------------------------------------------
    st.subheader("Send Money")

    receiver = st.text_input("Receiver Email")
    amount = st.number_input("Amount", min_value=1.0)

    if st.button("Send"):
        db = load_db()

        if receiver not in db["users"]:
            st.error("Receiver does not exist.")
        elif amount > db["users"][email]["balance"]:
            st.error("Insufficient balance.")
        else:
            # Deduct & Add
            db["users"][email]["balance"] -= amount
            db["users"][receiver]["balance"] += amount

            # Log
            ensure_transaction_key(db, email)
            ensure_transaction_key(db, receiver)

            db["transactions"][email].append({
                "type": "sent",
                "amount": amount,
                "to": receiver,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            db["transactions"][receiver].append({
                "type": "received",
                "amount": amount,
                "from": email,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            save_db(db)
            st.success("Money Sent!")

    # ---------------------------------------------------------
    # BILL PAYMENTS (UPDATED SAFELY)
    # ---------------------------------------------------------
    st.subheader("Bill Payments")

    billers = [
        "T&TEC Electricity",
        "WASA",
        "TSTT",
        "Digicel",
        "Flow",
        "Amplia",
        "bmobile",
        "Courts",
        "Internet"
    ]

    selected_bill = st.selectbox("Select Biller", billers)

    ref_number = st.text_input("Account / Phone / Reference Number")
    bill_amount = st.number_input("Bill Amount (TTD)", min_value=1.0)

    if st.button("Pay Bill"):
        db = load_db()

        if bill_amount > db["users"][email]["balance"]:
            st.error("Insufficient wallet balance.")
        else:
            db["users"][email]["balance"] -= bill_amount

            ensure_transaction_key(db, email)

            db["transactions"][email].append({
                "type": "billpayment",
                "biller": selected_bill,
                "ref": ref_number,
                "amount": bill_amount,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            save_db(db)
            st.success(f"Paid {selected_bill} successfully!")

    # ---------------------------------------------------------
    # TRANSACTION HISTORY
    # ---------------------------------------------------------
    st.subheader("Transaction History")

    db = load_db()
    ensure_transaction_key(db, email)

    for tx in reversed(db["transactions"][email]):
        if tx["type"] == "sent":
            st.error(f"Sent ${tx['amount']} → {tx['to']} ({tx['timestamp']})")

        elif tx["type"] == "received":
            st.success(f"Received ${tx['amount']} ← {tx['from']} ({tx['timestamp']})")

        elif tx["type"] == "billpayment":
            st.warning(f"Bill: {tx['biller']} • ${tx['amount']} • Ref: {tx['ref']} ({tx['timestamp']})")

    # ---------------------------------------------------------
    # LOGOUT
    # ---------------------------------------------------------
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.email = None
        st.experimental_rerun()
