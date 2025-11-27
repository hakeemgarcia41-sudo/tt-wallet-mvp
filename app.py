import streamlit as st
import json
from datetime import datetime

DB_FILE = "database.json"


# ------------------------------------------------
# ----------- DATABASE HELPERS -------------------
# ------------------------------------------------

def load_db():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {"users": {}, "transactions": {}, "bill_payments": {}, "cashouts": {}, "topups": {}}


def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)


def ensure_user_sections(db, email):
    """Ensures user keys exist to avoid KeyErrors."""
    if email not in db["transactions"]:
        db["transactions"][email] = []
    if email not in db["bill_payments"]:
        db["bill_payments"][email] = []
    if email not in db["cashouts"]:
        db["cashouts"][email] = []
    if email not in db["topups"]:
        db["topups"][email] = []
    return db


# ------------------------------------------------
# ----------- AUTH & WALLET LOGIC ----------------
# ------------------------------------------------

def create_user(email, password):
    db = load_db()

    if email in db["users"]:
        return False, "User already exists."

    db["users"][email] = {"password": password, "balance": 0.0}

    db = ensure_user_sections(db, email)
    save_db(db)

    return True, "Wallet created successfully!"


def authenticate(email, password):
    db = load_db()
    if email not in db["users"]:
        return False, "Invalid login details."

    if db["users"][email]["password"] != password:
        return False, "Invalid login details."

    return True, "Login successful."


def send_money(sender, receiver, amount):
    db = load_db()
    if receiver not in db["users"]:
        return False, "Receiver not found."

    if db["users"][sender]["balance"] < amount:
        return False, "Insufficient balance."

    # update balances
    db["users"][sender]["balance"] -= amount
    db["users"][receiver]["balance"] += amount

    # record transactions
    db = ensure_user_sections(db, sender)
    db = ensure_user_sections(db, receiver)

    timestamp = str(datetime.now())

    db["transactions"][sender].append({
        "type": "sent",
        "amount": amount,
        "to": receiver,
        "timestamp": timestamp
    })

    db["transactions"][receiver].append({
        "type": "received",
        "amount": amount,
        "from": sender,
        "timestamp": timestamp
    })

    save_db(db)
    return True, "Transaction completed."


def top_up(email, amount):
    db = load_db()
    db["users"][email]["balance"] += amount

    db = ensure_user_sections(db, email)
    db["topups"][email].append({
        "amount": amount,
        "timestamp": str(datetime.now())
    })

    save_db(db)
    return True, "Wallet topped up!"


def pay_bill(email, biller, account_number, amount):
    db = load_db()

    if db["users"][email]["balance"] < amount:
        return False, "Insufficient funds."

    db["users"][email]["balance"] -= amount

    db = ensure_user_sections(db, email)

    db["bill_payments"][email].append({
        "biller": biller,
        "account_number": account_number,
        "amount": amount,
        "timestamp": str(datetime.now())
    })

    save_db(db)
    return True, "Bill payment successful."


def cashout(email, bank, account_number, amount):
    db = load_db()

    if db["users"][email]["balance"] < amount:
        return False, "Insufficient funds."

    db["users"][email]["balance"] -= amount

    db = ensure_user_sections(db, email)

    db["cashouts"][email].append({
        "bank": bank,
        "account_number": account_number,
        "amount": amount,
        "timestamp": str(datetime.now())
    })

    save_db(db)
    return True, "Cashout request submitted."


# ------------------------------------------------
# -------------------- UI ------------------------
# ------------------------------------------------

st.set_page_config(page_title="InstacashTT Wallet", layout="wide")

st.title("💳 InstacashTT — Digital Wallet (TTD)")

menu = st.selectbox("Menu", ["Login", "Register", "Wallet"])

# SESSION
if "user" not in st.session_state:
    st.session_state.user = None


# ------------------------------------------------
# ------------------ REGISTER --------------------
# ------------------------------------------------

if menu == "Register":
    st.subheader("Create Your Wallet")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Register"):
        ok, msg = create_user(email, password)
        if ok:
            st.success(msg)
            st.session_state.user = email
            st.rerun()
        else:
            st.error(msg)


# ------------------------------------------------
# ------------------ LOGIN -----------------------
# ------------------------------------------------

elif menu == "Login":
    st.subheader("Login to Your Wallet")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        ok, msg = authenticate(email, password)
        if ok:
            st.success(msg)
            st.session_state.user = email
            st.rerun()
        else:
            st.error(msg)


# ------------------------------------------------
# ------------------ WALLET -----------------------
# ------------------------------------------------

elif menu == "Wallet":
    if not st.session_state.user:
        st.warning("Please login first.")
        st.stop()

    email = st.session_state.user
    db = load_db()

    st.subheader("Your Wallet")

    balance = db["users"][email]["balance"]
    st.write(f"**Balance:** ${balance} TTD")
    st.divider()

    # ---------- SEND MONEY ----------
    st.subheader("Send Money")

    receiver = st.text_input("Receiver Email")
    amount_send = st.number_input("Amount", min_value=1.0)

    if st.button("Send"):
        ok, msg = send_money(email, receiver, amount_send)
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

    st.divider()

    # ---------- TOP UP ----------
    st.subheader("Top Up Wallet")

    amount_topup = st.number_input("Top-Up Amount", min_value=1.0)

    if st.button("Top Up"):
        ok, msg = top_up(email, amount_topup)
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

    st.divider()

    # ---------- BILL PAYMENTS ----------
    st.subheader("Bill Payments")

    biller_list = [
        "T&TEC Electricity",
        "TSTT",
        "Digicel",
        "FLOW",
        "WASA",
        "Internet",
        "Amplia",
        "Bmobile",
        "Courts"
    ]

    biller = st.selectbox("Select Biller", biller_list)
    account_no = st.text_input("Account Number")
    bill_amount = st.number_input("Amount to Pay", min_value=1.0)

    if st.button("Pay Bill"):
        ok, msg = pay_bill(email, biller, account_no, bill_amount)
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

    st.divider()

    # ---------- CASHOUT ----------
    st.subheader("Wallet → Bank Cashout")

    bank = st.selectbox("Select Bank", ["RBC", "Republic Bank", "Scotiabank", "First Citizens"])
    bank_account = st.text_input("Bank Account Number")
    amount_cashout = st.number_input("Cashout Amount", min_value=1.0)

    if st.button("Cash Out"):
        ok, msg = cashout(email, bank, bank_account, amount_cashout)
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

    st.divider()

    # ---------- TRANSACTION HISTORY ----------
    st.subheader("Transaction History")

    db = load_db()
    ensure_user_sections(db, email)

    # Show money transfers
    for t in db["transactions"][email]:
        if t["type"] == "sent":
            st.error(f"Sent ${t['amount']} → {t['to']} ({t['timestamp']})")
        else:
            st.success(f"Received ${t['amount']} ← {t['from']} ({t['timestamp']})")

    st.divider()

    # Logout
    if st.button("Logout"):
        st.session_state.user = None
        st.rerun()
