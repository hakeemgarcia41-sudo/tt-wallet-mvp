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
        with open(DB_FILE, "r") as f:
            db = json.load(f)
    except:
        db = init_empty_db()

    for key in ["users", "transactions", "bill_payments", "cashouts", "topups"]:
        if key not in db:
            db[key] = {}

    return db

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

def ensure_user_structures(db, email):
    for section in ["transactions", "bill_payments", "cashouts", "topups"]:
        if email not in db[section]:
            db[section][email] = []

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
    if email not in db["users"]:
        return False, "User not found."

    if db["users"][email]["password"] != password:
        return False, "Invalid login details."

    return True, ""

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ---------- Streamlit Config ----------
st.set_page_config(page_title="InstacashTT — Digital Wallet", page_icon="💳")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "email" not in st.session_state:
    st.session_state.email = None
if "menu_state" not in st.session_state:
    st.session_state.menu_state = "login"

# ---------- Header UI ----------
def header():
    col1, col2 = st.columns([1, 8])
    with col1:
        st.image("InstacashTT.png", width=70)
    with col2:
        st.markdown(
            """
            <h1 style="margin-top:15px;">
                InstacashTT — Digital Wallet (TTD)
            </h1>
            """,
            unsafe_allow_html=True,
        )

# ---------- Login ----------
def login_view():
    header()
    st.subheader("Login to Your Wallet")

    col = st.container()
    with col:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login", key="login_button", use_container_width=True):
            ok, msg = authenticate(email, password)
            if ok:
                st.session_state.logged_in = True
                st.session_state.email = email
                st.rerun()
            else:
                st.error(msg)

        if st.button("Go to Register", key="go_register"):
            st.session_state.menu_state = "register"
            st.rerun()

# ---------- Register ----------
def register_view():
    header()
    st.subheader("Create Your Wallet")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Register", key="register_button", use_container_width=True):
        ok, msg = create_user(email, password)
        if ok:
            st.success("Wallet created. You may now log in.")
        else:
            st.error(msg)

    if st.button("Back to Login", key="back_login"):
        st.session_state.menu_state = "login"
        st.rerun()

# ---------- Wallet View ----------
def wallet_view():
    db = load_db()
    email = st.session_state.email
    user = db["users"][email]

    header()
    st.write("")

    # Center UI
    container = st.container()
    with container:
        st.subheader("Your Balance")
        st.markdown(f"""
            <h2 style="font-size: 32px; font-weight:600;">
                ${user['balance']:.2f} TTD
            </h2>
        """, unsafe_allow_html=True)

        st.markdown("---")

          # ---------- TOP UP WALLET ----------
        st.subheader("Top Up Wallet")

        # Initialize session state variable
        if "topup_method" not in st.session_state:
            st.session_state.topup_method = None

        colA, colB, colC = st.columns(3)

        with colA:
            if st.button("Bank Transfer", key="topup_bank"):
                st.session_state.topup_method = "Bank Transfer"

        with colB:
            if st.button("Debit/Credit Card", key="topup_card"):
                st.session_state.topup_method = "Card"

        with colC:
            if st.button("Cash at Agent", key="topup_cash"):
                st.session_state.topup_method = "Cash Agent"

        # Show selection visually
        if st.session_state.topup_method:
            st.info(f"Selected Method: {st.session_state.topup_method}")

        # Amount input (must have unique key)
        topup_amount = st.number_input(
            "Amount", 
            min_value=0.0, 
            step=1.0, 
            key="topup_amount_input"
        )

        # Confirm Top-Up
        if st.button("Confirm Top-Up", key="confirm_topup", use_container_width=True):
            if topup_amount <= 0:
                st.error("Amount must be greater than 0.")
            elif st.session_state.topup_method is None:
                st.error("Select a top-up method.")
            else:
                user["balance"] += topup_amount
                ts = now_str()
                ensure_user_structures(db, email)

                db["topups"][email].append({
                    "method": st.session_state.topup_method,
                    "amount": topup_amount,
                    "timestamp": ts
                })

                save_db(db)
                st.success(
                    f"Topped up ${topup_amount:.2f} via {st.session_state.topup_method}"
                )
                
        # ---------- SEND MONEY ----------
        st.subheader("Send Money")
        with st.container():
            receiver = st.text_input("Receiver Email", key="send_receiver")
            amount = st.number_input("Amount", min_value=0.0, step=1.0, key="send_amount")
            if st.button("Send", key="send_button"):
                receiver = receiver.strip()
                if receiver == email:
                    st.error("You can't send money to yourself.")
                elif receiver not in db["users"]:
                    st.error("Receiver not found.")
                elif amount <= 0:
                    st.error("Amount must be greater than 0.")
                elif amount > user["balance"]:
                    st.error("Insufficient funds.")
                else:
                    user["balance"] -= amount
                    db["users"][receiver]["balance"] += amount

                    ts = now_str()
                    ensure_user_structures(db, email)
                    ensure_user_structures(db, receiver)

                    db["transactions"][email].append({
                        "type": "sent", "amount": amount, "to": receiver, "timestamp": ts
                    })

                    db["transactions"][receiver].append({
                        "type": "received", "amount": amount, "from": email, "timestamp": ts
                    })

                    save_db(db)
                    st.success(f"Sent ${amount:.2f} to {receiver}")

        st.markdown("---")

        # ---------- BILL PAYMENTS ----------
        st.subheader("Bill Payments")

        biller_list = ["T&TEC Electricity", "WASA", "TSTT", "Digicel",
                       "FLOW", "Amplia", "Bmobile", "Courts"]

        biller = st.selectbox("Select Biller", biller_list)
        acct = st.text_input("Account Number", key="bill_acct")
        bill_amt = st.number_input("Payment Amount", min_value=0.0, step=1.0, key="bill_amt")

        if st.button("Pay Bill", key="bill_pay_btn"):
            if not acct:
                st.error("Enter account/contract number.")
            elif bill_amt > user["balance"]:
                st.error("Insufficient balance.")
            else:
                user["balance"] -= bill_amt
                ts = now_str()
                ensure_user_structures(db, email)

                db["bill_payments"][email].append({
                    "biller": biller,
                    "account_number": acct,
                    "amount": bill_amt,
                    "timestamp": ts
                })

                db["transactions"][email].append({
                    "type": "bill_payment",
                    "amount": bill_amt,
                    "to": biller,
                    "timestamp": ts
                })

                save_db(db)
                st.success(f"Paid ${bill_amt:.2f} to {biller}")

        st.markdown("---")

        # ---------- CASHOUT ----------
        st.subheader("Wallet → Bank Cashout")

        bank_list = ["Republic Bank", "First Citizens", "RBC",
                     "Scotiabank", "JMMB", "Other"]

        bank = st.selectbox("Select Bank", bank_list)
        acctnum = st.text_input("Bank Account #", key="acctnum")
        cashout_amt = st.number_input("Cashout Amount", min_value=0.0, step=1.0, key="cashout_amt")

        if st.button("Cashout", key="cashout_btn"):
            if not acctnum:
                st.error("Enter account number.")
            elif cashout_amt > user["balance"]:
                st.error("Insufficient balance.")
            else:
                user["balance"] -= cashout_amt
                ts = now_str()
                ensure_user_structures(db, email)

                db["cashouts"][email].append({
                    "bank": bank,
                    "account": acctnum,
                    "amount": cashout_amt,
                    "timestamp": ts
                })

                db["transactions"][email].append({
                    "type": "cashout",
                    "amount": cashout_amt,
                    "to": bank,
                    "timestamp": ts
                })

                save_db(db)
                st.success(f"Cashout sent to {bank}")

        st.markdown("---")

        # ---------- TRANSACTION HISTORY ----------
        st.subheader("Transaction History")
        tx_list = db["transactions"].get(email, [])

        if tx_list:
            for tx in reversed(tx_list):
                st.markdown(
                    f"""
                    **{tx['type'].capitalize()}** — ${tx['amount']:.2f}  
                    `{tx['timestamp']}`
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("No transactions yet.")

        st.markdown("---")

        if st.button("Logout", key="logout_button", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.email = None
            st.session_state.menu_state = "login"
            st.rerun()

# ---------- Routing ----------
if not st.session_state.logged_in:
    if st.session_state.menu_state == "login":
        login_view()
    else:
        register_view()
else:
    wallet_view()
