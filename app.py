import streamlit as st
import json
import os
from datetime import datetime

DB_FILE = "database.json"

# ----------------------------
# Database Helpers
# ----------------------------

def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({"users": {}, "transactions": {}}, f, indent=4)
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)

def get_user(email):
    db = load_db()
    return db["users"].get(email)

def create_user(email, password):
    db = load_db()
    if email in db["users"]:
        return False

    db["users"][email] = {
        "email": email,
        "password": password,
        "balance": 0.0
    }
    db["transactions"][email] = []
    save_db(db)
    return True

def update_balance(email, amount):
    db = load_db()
    db["users"][email]["balance"] = amount
    save_db(db)

def add_transaction(email, entry):
    db = load_db()
    db["transactions"][email].append(entry)
    save_db(db)

# ----------------------------
# Streamlit App UI
# ----------------------------

st.set_page_config(page_title="InstacashTT Wallet (TTD)", layout="wide")

st.markdown(
    "<h1 style='font-size:42px;'>💳 InstacashTT — Digital Wallet (TTD)</h1>",
    unsafe_allow_html=True
)

# Session Initialization
if "user" not in st.session_state:
    st.session_state.user = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None

# ----------------------------
# Registration Page
# ----------------------------
def register():
    st.subheader("Create a New Wallet Account")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Register"):
        if not email or not password:
            st.error("All fields are required.")
        elif create_user(email, password):
            st.success("Account created successfully! You may now log in.")
        else:
            st.error("An account with this email already exists.")

# ----------------------------
# Login Page
# ----------------------------
def login():
    st.subheader("Login to Your Wallet")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = get_user(email)
        if not user:
            st.error("Account not found.")
        elif password != user["password"]:
            st.error("Incorrect password.")
        else:
            st.success("Login successful!")
            st.session_state.user = user
            st.session_state.user_email = email
            st.experimental_rerun()

# ----------------------------
# Wallet Dashboard
# ----------------------------
def dashboard():
    user = st.session_state.user
    email = st.session_state.user_email

    st.markdown(f"### Your Wallet")
    st.markdown(f"**Balance:** ${user['balance']:.2f} TTD")

    st.markdown("---")

    # ------------------------------------
    # SEND MONEY
    # ------------------------------------
    st.subheader("Send Money")

    receiver = st.text_input("Receiver Email")
    amount = st.number_input("Amount", min_value=1.0)

    if st.button("Send"):
        db = load_db()

        if receiver not in db["users"]:
            st.error("Receiver not found.")
        elif amount > user["balance"]:
            st.error("Insufficient balance.")
        else:
            # Update balances
            user["balance"] -= amount
            db["users"][receiver]["balance"] += amount

            # Record transactions
            add_transaction(email, {
                "type": "send",
                "to": receiver,
                "amount": amount,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            add_transaction(receiver, {
                "type": "receive",
                "from": email,
                "amount": amount,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            save_db(db)
            st.success(f"Sent ${amount:.2f} TTD to {receiver}!")
            st.session_state.user = get_user(email)

    st.markdown("---")

    # ------------------------------------
    # TOP UP WALLET
    # ------------------------------------
    st.subheader("Top-Up Wallet")

    top_amount = st.number_input("Top-Up Amount", min_value=1.0, key="top_up_val")

    if st.button("Top-Up"):
        user["balance"] += top_amount

        add_transaction(email, {
            "type": "topup",
            "amount": top_amount,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        update_balance(email, user["balance"])
        st.success(f"Wallet topped up by ${top_amount:.2f} TTD!")

    st.markdown("---")

    # ------------------------------------
    # WALLET TO BANK CASHOUT
    # ------------------------------------
    st.subheader("Cashout to Bank")

    bank_name = st.text_input("Bank Name (ex. RBC, Republic Bank)")
    bank_acc = st.text_input("Bank Account Number")
    cashout_amount = st.number_input("Cashout Amount", min_value=1.0, key="cashout_val")

    if st.button("Cashout Now"):
        if cashout_amount > user["balance"]:
            st.error("Insufficient balance.")
        else:
            user["balance"] -= cashout_amount
            update_balance(email, user["balance"])

            add_transaction(email, {
                "type": "cashout",
                "bank": bank_name,
                "account": bank_acc,
                "amount": cashout_amount,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            st.success(f"Cashout request of ${cashout_amount:.2f} to {bank_name} submitted!")

    st.markdown("---")

    # ------------------------------------
    # BILL PAYMENTS
    # ------------------------------------
    st.subheader("Bill Payments")

    billers = [
        "T&TEC Electricity", "WASA", "TSTT", "Digicel",
        "Flow", "Amplia", "bmobile", "Courts", "Internet"
    ]

    selected_bill = st.selectbox("Select Bill", billers)

    account_number = st.text_input("Account / Phone / Reference Number")
    bill_amount = st.number_input("Bill Amount", min_value=1.0, key="bill_val")

    if st.button("Pay Bill"):
        if bill_amount > user["balance"]:
            st.error("Insufficient wallet balance.")
        else:
            user["balance"] -= bill_amount
            update_balance(email, user["balance"])

            add_transaction(email, {
                "type": "billpayment",
                "biller": selected_bill,
                "ref": account_number,
                "amount": bill_amount,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            st.success(f"Bill payment to {selected_bill} completed!")

    st.markdown("---")

    # ------------------------------------
    # TRANSACTION HISTORY
    # ------------------------------------
    st.subheader("Transaction History")

    db = load_db()
    history = db["transactions"][email]

    for h in reversed(history):
        if h["type"] == "send":
            st.error(f"Sent ${h['amount']} → {h['to']} ({h['timestamp']})")
        elif h["type"] == "receive":
            st.success(f"Received ${h['amount']} ← {h['from']} ({h['timestamp']})")
        elif h["type"] == "topup":
            st.info(f"Topped Up +${h['amount']} ({h['timestamp']})")
        elif h["type"] == "cashout":
            st.warning(f"Cashout ${h['amount']} → {h['bank']} ({h['timestamp']})")
        elif h["type"] == "billpayment":
            st.error(f"Paid {h['biller']} - ${h['amount']} (Ref: {h['ref']})")

    st.markdown("---")
    if st.button("Logout"):
        st.session_state.user = None
        st.session_state.user_email = None
        st.experimental_rerun()

# ----------------------------
# MAIN ROUTER
# ----------------------------
menu = ["Login", "Register"]
choice = st.selectbox("Menu", menu)

if choice == "Login":
    if st.session_state.user:
        dashboard()
    else:
        login()
elif choice == "Register":
    register()
