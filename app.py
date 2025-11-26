import streamlit as st
import json
import uuid
from datetime import datetime

# --------------------------
# Load / Save Database
# --------------------------
DB_FILE = "database.json"

def load_db():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {"users": {}}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)

db = load_db()

# --------------------------
# Utility Functions
# --------------------------
def login_user(email, password):
    if email in db["users"] and db["users"][email]["password"] == password:
        st.session_state["user"] = email
        return True, "Login successful!"
    return False, "Invalid login credentials."

def register_user(email, password):
    if email in db["users"]:
        return False, "User already exists."

    db["users"][email] = {
        "password": password,
        "balance": 0.0,
        "transactions": []
    }
    save_db(db)
    return True, "Registration successful! You can now log in."

def record_transaction(user, message):
    db["users"][user]["transactions"].append(message)
    save_db(db)

def send_money(sender, receiver, amount):
    if receiver not in db["users"]:
        return False, "Receiver does not exist."

    if db["users"][sender]["balance"] < amount:
        return False, "Insufficient funds."

    db["users"][sender]["balance"] -= amount
    db["users"][receiver]["balance"] += amount

    timestamp = str(datetime.now())[:19]
    record_transaction(sender, f"Sent ${amount} → {receiver} ({timestamp})")
    record_transaction(receiver, f"Received ${amount} ← {sender} ({timestamp})")

    return True, "Transfer successful."

def top_up_wallet(user, amount):
    db["users"][user]["balance"] += amount
    timestamp = str(datetime.now())[:19]
    record_transaction(user, f"Topped Up ${amount} ({timestamp})")
    return True, "Top-up successful!"

def pay_bill(user, bill_type, amount):
    if db["users"][user]["balance"] < amount:
        return False, "Insufficient balance to pay bill."

    db["users"][user]["balance"] -= amount
    timestamp = str(datetime.now())[:19]
    record_transaction(user, f"Bill Payment: {bill_type} – ${amount} ({timestamp})")
    return True, "Bill payment successful!"

def cashout_to_bank(user, amount, bank):
    if db["users"][user]["balance"] < amount:
        return False, "Insufficient funds to cash out."

    db["users"][user]["balance"] -= amount
    timestamp = str(datetime.now())[:19]
    record_transaction(user, f"Cashout to {bank}: ${amount} ({timestamp})")
    return True, "Cashout request submitted."

# --------------------------
# App UI
# --------------------------
st.set_page_config(page_title="InstacashTT Wallet", layout="wide")
st.title("💳 InstacashTT — Digital Wallet (TTD)")

if "user" not in st.session_state:
    st.session_state["user"] = None

menu = st.selectbox("Menu", ["Login", "Register"] if st.session_state["user"] is None else ["Wallet", "Logout"])

# --------------------------
# Login
# --------------------------
if menu == "Login" and st.session_state["user"] is None:
    st.subheader("Login to Your Wallet")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        ok, msg = login_user(email, password)
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

# --------------------------
# Register
# --------------------------
elif menu == "Register" and st.session_state["user"] is None:
    st.subheader("Create a New Wallet")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Register"):
        ok, msg = register_user(email, password)
        if ok:
            st.success(msg)
        else:
            st.error(msg)

# --------------------------
# Wallet Dashboard
# --------------------------
elif menu == "Wallet" and st.session_state["user"] is not None:
    user = st.session_state["user"]
    user_data = db["users"][user]

    st.header("Your Wallet")
    st.subheader(f"Balance: ${user_data['balance']:.2f} TTD")

    st.write("---")

    # ----------------------
    # SEND MONEY
    # ----------------------
    st.subheader("Send Money")
    receiver = st.text_input("Receiver Email")
    amount = st.number_input("Amount (TTD)", min_value=1.0, step=1.0)

    if st.button("Send"):
        ok, msg = send_money(user, receiver, amount)
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

    st.write("---")

    # ----------------------
    # TOP UP WALLET
    # ----------------------
    st.subheader("Top Up Wallet")
    topup = st.number_input("Top-Up Amount", min_value=1.0, step=1.0)

    if st.button("Top Up"):
        ok, msg = top_up_wallet(user, topup)
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

    st.write("---")

    # ----------------------
    # BILL PAYMENT
    # ----------------------
    st.subheader("Bill Payments")
    bill_type = st.selectbox("Select Bill", ["T&TEC Electricity", "TSTT", "Digicel", "FLOW", "WASA", "Internet"])
    bill_amount = st.number_input("Bill Amount", min_value=1.0, step=1.0)

    if st.button("Pay Bill"):
        ok, msg = pay_bill(user, bill_type, bill_amount)
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

    st.write("---")

    # ----------------------
    # CASHOUT TO BANK
    # ----------------------
    st.subheader("Wallet → Bank Cashout")
    bank = st.selectbox("Select Bank", ["Republic Bank", "RBC Royal Bank", "Scotiabank", "First Citizens (FCB)", "JMMB"])
    cash_amount = st.number_input("Cashout Amount", min_value=1.0, step=1.0)

    if st.button("Cash Out"):
        ok, msg = cashout_to_bank(user, cash_amount, bank)
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

    st.write("---")

    # ----------------------
    # TRANSACTION HISTORY
    # ----------------------
    st.subheader("Transaction History")

    for tx in reversed(user_data["transactions"]):
        st.info(tx)

# --------------------------
# Logout
# --------------------------
elif menu == "Logout":
    st.session_state["user"] = None
    st.success("Logged out successfully!")
    st.rerun()
