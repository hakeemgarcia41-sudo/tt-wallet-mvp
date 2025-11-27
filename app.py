import json
import os
from datetime import datetime

import streamlit as st

DB_FILE = "database.json"

# ---------- Database helpers ----------

def init_empty_db():
    """Return a fully initialised, empty DB structure."""
    return {
        "users": {},
        "transactions": {},
        "bill_payments": {},
        "cashouts": {},
        "topups": {},
    }


def load_db():
    """Load DB from disk; if missing or malformed, create a clean one."""
    if not os.path.exists(DB_FILE):
        db = init_empty_db()
        save_db(db)
        return db

    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)
    except Exception:
        # Fallback if file is corrupted
        db = init_empty_db()

    # Ensure all top-level keys exist
    for key in ["users", "transactions", "bill_payments", "cashouts", "topups"]:
        if key not in db or not isinstance(db[key], dict):
            db[key] = {}

    return db


def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2)


def ensure_user_structures(db, email):
    """Make sure per-user lists exist for this email."""
    if email not in db["transactions"]:
        db["transactions"][email] = []
    if email not in db["bill_payments"]:
        db["bill_payments"][email] = []
    if email not in db["cashouts"]:
        db["cashouts"][email] = []
    if email not in db["topups"]:
        db["topups"][email] = []


def create_user(email, password):
    db = load_db()

    if email in db["users"]:
        return False, "User already exists."

    db["users"][email] = {
        "password": password,
        "balance": 0.0,
    }

    ensure_user_structures(db, email)
    save_db(db)
    return True, "Wallet created successfully."


def authenticate(email, password):
    db = load_db()
    user = db["users"].get(email)

    if not user:
        return False, "User not found."

    if user["password"] != password:
        return False, "Invalid login details."

    return True, "Login successful."


def record_transaction(db, email, entry):
    ensure_user_structures(db, email)
    db["transactions"][email].append(entry)


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------- Streamlit UI ----------

st.set_page_config(
    page_title="InstacashTT — Digital Wallet (TTD)",
    page_icon="💳",
    layout="wide",
)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "email" not in st.session_state:
    st.session_state.email = None

st.title("💳 InstacashTT — Digital Wallet (TTD)")

# Menu depends on auth state
if st.session_state.logged_in:
    menu = st.selectbox("Menu", ["Wallet", "Logout"])
else:
    menu = st.selectbox("Menu", ["Login", "Register"])


# ---------- Login ----------

def login_view():
    st.subheader("Login to Your Wallet")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        ok, msg = authenticate(email.strip(), password)
        if ok:
            st.session_state.logged_in = True
            st.session_state.email = email.strip()
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)


# ---------- Register ----------

def register_view():
    st.subheader("Create Your Wallet")

    with st.form("register_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Register")

    if submitted:
        email = email.strip()
        if not email or not password:
            st.error("Please enter both email and password.")
            return

        ok, msg = create_user(email, password)
        if ok:
            st.success(msg + " You can now log in.")
        else:
            st.error(msg)


# ---------- Wallet Dashboard ----------

def wallet_view():
    db = load_db()
    email = st.session_state.email
    user = db["users"].get(email)

    if not user:
        st.error("User not found in database.")
        return

    ensure_user_structures(db, email)

    st.subheader("Your Wallet")
    st.metric("Balance", f"${user['balance']:.2f} TTD")

    st.markdown("---")

    # 1. Send Money
    st.subheader("Send Money")

    with st.form("send_money_form"):
        receiver = st.text_input("Receiver Email")
        amount = st.number_input("Amount", min_value=0.0, step=10.0)
        send_submitted = st.form_submit_button("Send")

    if send_submitted:
        receiver = receiver.strip()
        if receiver == email:
            st.error("You cannot send money to yourself.")
        elif receiver not in db["users"]:
            st.error("Receiver not found.")
        elif amount <= 0:
            st.error("Amount must be greater than 0.")
        elif amount > db["users"][email]["balance"]:
            st.error("Insufficient balance.")
        else:
            # Adjust balances
            db["users"][email]["balance"] -= amount
            db["users"][receiver]["balance"] += amount

            ts = now_str()

            # Record for sender
            record_transaction(
                db,
                email,
                {
                    "type": "sent",
                    "amount": amount,
                    "to": receiver,
                    "timestamp": ts,
                },
            )

            # Record for receiver
            record_transaction(
                db,
                receiver,
                {
                    "type": "received",
                    "amount": amount,
                    "from": email,
                    "timestamp": ts,
                },
            )

            save_db(db)
            st.success(f"Sent ${amount:.2f} TTD to {receiver}.")

    st.markdown("---")

    # 2. Top Up Wallet
    st.subheader("Top Up Wallet")

    with st.form("topup_form"):
        topup_method = st.selectbox(
            "Top-up Method",
            ["Bank Transfer", "Credit/Debit Card", "Cash at Agent"],
        )
        topup_amount = st.number_input(
            "Top-up Amount", min_value=0.0, step=10.0, key="topup_amount"
        )
        reference = st.text_input("Reference / Description (optional)")
        topup_submitted = st.form_submit_button("Top Up")

    if topup_submitted:
        if topup_amount <= 0:
            st.error("Amount must be greater than 0.")
        else:
            db["users"][email]["balance"] += topup_amount

            ts = now_str()
            ensure_user_structures(db, email)
            db["topups"][email].append(
                {
                    "method": topup_method,
                    "amount": topup_amount,
                    "reference": reference,
                    "timestamp": ts,
                }
            )

            record_transaction(
                db,
                email,
                {
                    "type": "topup",
                    "amount": topup_amount,
                    "details": topup_method,
                    "timestamp": ts,
                },
            )

            save_db(db)
            st.success(
                f"Wallet topped up by ${topup_amount:.2f} TTD via {topup_method}."
            )

    st.markdown("---")

    # 3. Bill Payments
    st.subheader("Bill Payments")

    BILLERS = [
        "T&TEC Electricity",
        "WASA",
        "TSTT",
        "Digicel",
        "FLOW",
        "Amplia",
        "Bmobile",
        "Courts",
        "Internet",
    ]

    with st.form("bill_pay_form"):
        biller = st.selectbox("Select Bill", BILLERS)
        account_number = st.text_input("Account / Contract Number")
        bill_amount = st.number_input(
            "Payment Amount", min_value=0.0, step=10.0, key="bill_amount"
        )
        bill_submitted = st.form_submit_button("Pay Bill")

    if bill_submitted:
        if not account_number.strip():
            st.error("Please enter an account number.")
        elif bill_amount <= 0:
            st.error("Amount must be greater than 0.")
        elif bill_amount > db["users"][email]["balance"]:
            st.error("Insufficient balance.")
        else:
            db["users"][email]["balance"] -= bill_amount

            ts = now_str()
            ensure_user_structures(db, email)

            db["bill_payments"][email].append(
                {
                    "biller": biller,
                    "account_number": account_number.strip(),
                    "amount": bill_amount,
                    "timestamp": ts,
                }
            )

            record_transaction(
                db,
                email,
                {
                    "type": "bill_payment",
                    "amount": bill_amount,
                    "to": biller,
                    "timestamp": ts,
                },
            )

            save_db(db)
            st.success(
                f"Paid ${bill_amount:.2f} TTD to {biller} "
                f"for account {account_number}."
            )

    st.markdown("---")

    # 4. Wallet → Bank Cashout
    st.subheader("Wallet to Bank Cashout")

    BANKS = [
        "Republic Bank",
        "First Citizens",
        "RBC Royal Bank",
        "Scotiabank",
        "JMMB",
        "Other",
    ]

    with st.form("cashout_form"):
        bank = st.selectbox("Select Bank", BANKS)
        bank_account = st.text_input("Bank Account Number / IBAN")
        cashout_amount = st.number_input(
            "Cashout Amount", min_value=0.0, step=10.0, key="cashout_amount"
        )
        cashout_submitted = st.form_submit_button("Request Cashout")

    if cashout_submitted:
        if not bank_account.strip():
            st.error("Please enter a bank account number.")
        elif cashout_amount <= 0:
            st.error("Amount must be greater than 0.")
        elif cashout_amount > db["users"][email]["balance"]:
            st.error("Insufficient balance.")
        else:
            db["users"][email]["balance"] -= cashout_amount

            ts = now_str()
            ensure_user_structures(db, email)

            db["cashouts"][email].append(
                {
                    "bank": bank,
                    "account": bank_account.strip(),
                    "amount": cashout_amount,
                    "timestamp": ts,
                }
            )

            record_transaction(
                db,
                email,
                {
                    "type": "cashout",
                    "amount": cashout_amount,
                    "to": bank,
                    "timestamp": ts,
                },
            )

            save_db(db)
            st.success(
                f"Cashout of ${cashout_amount:.2f} TTD requested to "
                f"{bank} account {bank_account}."
            )

    st.markdown("---")

    # 5. Transaction History
    st.subheader("Transaction History")

    tx_list = db["transactions"].get(email, [])
    if not tx_list:
        st.info("No transactions yet.")
    else:
        for tx in reversed(tx_list):
            if tx["type"] == "sent":
                st.error(
                    f"Sent ${tx['amount']:.2f} to {tx.get('to')} "
                    f"({tx['timestamp']})"
                )
            elif tx["type"] == "received":
                st.success(
                    f"Received ${tx['amount']:.2f} from {tx.get('from')} "
                    f"({tx['timestamp']})"
                )
            elif tx["type"] == "bill_payment":
                st.warning(
                    f"Bill payment of ${tx['amount']:.2f} to {tx.get('to')} "
                    f"({tx['timestamp']})"
                )
            elif tx["type"] == "topup":
                st.info(
                    f"Top-up of ${tx['amount']:.2f} via "
                    f"{tx.get('details')} ({tx['timestamp']})"
                )
            elif tx["type"] == "cashout":
                st.info(
                    f"Cashout of ${tx['amount']:.2f} to {tx.get('to')} "
                    f"({tx['timestamp']})"
                )
            else:
                st.write(tx)

    st.markdown("---")

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.email = None
        st.rerun()


# ---------- Main routing ----------

if menu == "Login" and not st.session_state.logged_in:
    login_view()
elif menu == "Register" and not st.session_state.logged_in:
    register_view()
elif menu == "Wallet" and st.session_state.logged_in:
    wallet_view()
elif menu == "Logout" and st.session_state.logged_in:
    st.session_state.logged_in = False
    st.session_state.email = None
    st.success("Logged out.")
    st.rerun()
else:
    # Fallback: if state and menu mismatch, send to login
    if not st.session_state.logged_in:
        login_view()
    else:
        wallet_view()
