import json
import os
from datetime import datetime
import streamlit as st

DB_FILE = "database.json"

# ---------- Database Helpers ----------

def init_empty_db():
    return {
        "users": {},
        "transactions": {},
        "bill_payments": {},
        "cashouts": {},
        "topups": {},
    }

def load_db():
    if not os.path.exists(DB_FILE):
        db = init_empty_db()
        save_db(db)
        return db

    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)
    except:
        db = init_empty_db()

    for key in ["users", "transactions", "bill_payments", "cashouts", "topups"]:
        if key not in db or not isinstance(db[key], dict):
            db[key] = {}

    return db

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2)

def ensure_user_structures(db, email):
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

    db["users"][email] = {"password": password, "balance": 0.0}
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


# ------------------- STREAMLIT UI -------------------

st.set_page_config(
    page_title="InstacashTT — Digital Wallet (TTD)",
    page_icon="InstacashTT.png",
    layout="wide"
)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "email" not in st.session_state:
    st.session_state.email = None

# Load logo
try:
    st.image("InstacashTT.png", width=120)
except:
    st.warning("Logo missing: Place InstacashTT.png in the same folder as app.py")

st.title("InstacashTT — Digital Wallet (TTD)")


# ---------------------- LOGIN VIEW ----------------------

def login_view():
    st.subheader("Login to Your Wallet")

    col1, col2 = st.columns(2)
    if col1.button("Login", key="login_button_switch"):
        st.session_state.menu_state = "login"
    if col2.button("Register", key="register_button_switch"):
        st.session_state.menu_state = "register"

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", key="login_submit")

    if submitted:
        ok, msg = authenticate(email.strip(), password)
        if ok:
            st.session_state.logged_in = True
            st.session_state.email = email.strip()
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)


# ---------------------- REGISTER VIEW ----------------------

def register_view():
    st.subheader("Create Your Wallet")

    col1, col2 = st.columns(2)
    if col1.button("Login", key="login_button_switch2"):
        st.session_state.menu_state = "login"
    if col2.button("Register", key="register_button_switch2"):
        st.session_state.menu_state = "register"

    with st.form("register_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Register", key="register_submit")

    if submitted:
        ok, msg = create_user(email.strip(), password)
        if ok:
            st.success(msg + " You can now log in.")
        else:
            st.error(msg)


# ---------------------- WALLET VIEW ----------------------

def wallet_view():
    db = load_db()
    email = st.session_state.email
    user = db["users"].get(email)

    ensure_user_structures(db, email)

    st.subheader("Your Wallet")
    st.metric("Balance", f"${user['balance']:.2f} TTD")

    st.markdown("---")

    # ------------------- SEND MONEY -------------------
    st.subheader("Send Money")

    with st.form("send_money_form"):
        receiver = st.text_input("Receiver Email")
        amount = st.number_input("Amount", min_value=0.0, step=10.0)
        send_submitted = st.form_submit_button("Send", key="send_money_btn")

    if send_submitted:
        receiver = receiver.strip()

        if receiver == email:
            st.error("You cannot send money to yourself.")
        elif receiver not in db["users"]:
            st.error("Receiver not found.")
        elif amount <= 0:
            st.error("Amount must be greater than 0.")
        elif amount > user["balance"]:
            st.error("Insufficient balance.")
        else:
            db["users"][email]["balance"] -= amount
            db["users"][receiver]["balance"] += amount

            ts = now_str()

            record_transaction(
                db, email,
                {"type": "sent", "amount": amount, "to": receiver, "timestamp": ts}
            )

            record_transaction(
                db, receiver,
                {"type": "received", "amount": amount, "from": email, "timestamp": ts}
            )

            save_db(db)
            st.success(f"Sent ${amount:.2f} TTD to {receiver}.")

    st.markdown("---")

    # ------------------- TOP UP -------------------
    st.subheader("Top Up Wallet")

    with st.form("topup_form"):
        topup_method = st.selectbox("Top-up Method", ["Bank Transfer", "Credit/Debit Card", "Cash at Agent"])
        topup_amount = st.number_input("Top-up Amount", min_value=0.0, step=10.0)
        reference = st.text_input("Reference")
        topup_submit = st.form_submit_button("Top Up", key="topup_btn")

    if topup_submit:
        if topup_amount <= 0:
            st.error("Amount must be greater than 0.")
        else:
            db["users"][email]["balance"] += topup_amount
            ts = now_str()

            db["topups"][email].append(
                {"method": topup_method, "amount": topup_amount, "reference": reference, "timestamp": ts}
            )

            record_transaction(
                db, email,
                {"type": "topup", "amount": topup_amount, "details": topup_method, "timestamp": ts}
            )

            save_db(db)
            st.success(f"Topped up ${topup_amount:.2f} via {topup_method}.")

    st.markdown("---")

    # ------------------- BILL PAYMENTS -------------------
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
        "Internet"
    ]

    with st.form("bill_form"):
        biller = st.selectbox("Select Bill", BILLERS)
        account_number = st.text_input("Account Number")
        bill_amount = st.number_input("Payment Amount", min_value=0.0, step=10.0)
        bill_submit = st.form_submit_button("Pay Bill", key="bill_btn")

    if bill_submit:
        if not account_number.strip():
            st.error("Account number required.")
        elif bill_amount <= 0:
            st.error("Invalid amount.")
        elif bill_amount > user["balance"]:
            st.error("Insufficient balance.")
        else:
            user["balance"] -= bill_amount
            ts = now_str()

            db["bill_payments"][email].append(
                {"biller": biller, "account_number": account_number.strip(),
                 "amount": bill_amount, "timestamp": ts}
            )

            record_transaction(
                db, email,
                {"type": "bill_payment", "amount": bill_amount, "to": biller, "timestamp": ts}
            )

            save_db(db)
            st.success(f"Paid ${bill_amount:.2f} to {biller}.")

    st.markdown("---")

    # ------------------- CASHOUT -------------------
    st.subheader("Wallet to Bank Cashout")

    BANKS = [
        "Republic Bank",
        "First Citizens",
        "RBC Royal Bank",
        "Scotiabank",
        "JMMB",
        "Other"
    ]

    with st.form("cashout_form"):
        bank = st.selectbox("Select Bank", BANKS)
        account = st.text_input("Bank Account Number")
        cashout_amount = st.number_input("Cashout Amount", min_value=0.0, step=10.0)
        cashout_submit = st.form_submit_button("Request Cashout", key="cashout_btn")

    if cashout_submit:
        if not account.strip():
            st.error("Enter your bank account number.")
        elif cashout_amount <= 0:
            st.error("Invalid amount.")
        elif cashout_amount > user["balance"]:
            st.error("Insufficient balance.")
        else:
            user["balance"] -= cashout_amount
            ts = now_str()

            db["cashouts"][email].append(
                {"bank": bank, "account": account.strip(), "amount": cashout_amount, "timestamp": ts}
            )

            record_transaction(
                db, email,
                {"type": "cashout", "amount": cashout_amount, "to": bank, "timestamp": ts}
            )

            save_db(db)
            st.success(f"Cashout request submitted to {bank}.")

    st.markdown("---")

    # ------------------- TRANSACTION HISTORY -------------------
    st.subheader("Transaction History")

    tx_list = db["transactions"].get(email, [])
    if not tx_list:
        st.info("No transactions yet.")
    else:
        for tx in reversed(tx_list):
            if tx["type"] == "sent":
                st.error(f"Sent ${tx['amount']:.2f} to {tx['to']} ({tx['timestamp']})")
            elif tx["type"] == "received":
                st.success(f"Received ${tx['amount']:.2f} from {tx['from']} ({tx['timestamp']})")
            elif tx["type"] == "bill_payment":
                st.warning(f"Bill payment ${tx['amount']:.2f} to {tx['to']} ({tx['timestamp']})")
            elif tx["type"] == "topup":
                st.info(f"Top-up ${tx['amount']:.2f} via {tx['details']} ({tx['timestamp']})")
            elif tx["type"] == "cashout":
                st.info(f"Cashout ${tx['amount']:.2f} to {tx['to']} ({tx['timestamp']})")

    st.markdown("---")

    # ------------------- LOGOUT -------------------
    if st.button("Logout", key="logout_bottom", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.email = None
        st.rerun()


# ---------------------- ROUTING ----------------------

if "menu_state" not in st.session_state:
    st.session_state.menu_state = "login"

if not st.session_state.logged_in:
    if st.session_state.menu_state == "login":
        login_view()
    else:
        register_view()
else:
    wallet_view()
