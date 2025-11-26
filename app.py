import streamlit as st
import json
from datetime import datetime

# ================================
# LOAD & SAVE DATABASE
# ================================
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

# ================================
# STYLE CONFIGURATION (ROYAL BLUE)
# ================================
PRIMARY = "#0047AB"
SECONDARY = "#1E90FF"
BG = "#F5F7FB"

st.markdown(f"""
    <style>
        body {{
            background-color: {BG};
        }}
        .balance-card {{
            background-color: {PRIMARY};
            padding: 25px;
            border-radius: 15px;
            color: white;
            font-size: 28px;
            text-align: center;
            font-weight: bold;
            box-shadow: 0px 4px 10px rgba(0,0,0,0.15);
        }}
        .quick-btn {{
            background-color: {SECONDARY};
            padding: 10px 15px;
            border-radius: 10px;
            color: white;
            text-align: center;
            font-weight: bold;
            cursor: pointer;
            margin-bottom: 10px;
        }}
        .quick-btn:hover {{
            background-color: {PRIMARY};
        }}
    </style>
""", unsafe_allow_html=True)

# ================================
# AUTH / REGISTER FUNCTIONS
# ================================
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


def login_user(email, password):
    if email not in db["users"]:
        return False, "User not found."

    if db["users"][email]["password"] != password:
        return False, "Incorrect password."

    st.session_state["logged_in"] = True
    st.session_state["email"] = email
    return True, "Login successful!"

# ================================
# TRANSACTION FUNCTIONS
# ================================
def log_transaction(user, tx):
    db["users"][user]["transactions"].append(tx)
    save_db(db)

def send_money(sender, receiver, amount):
    if receiver not in db["users"]:
        return False, "Receiver not found."

    if db["users"][sender]["balance"] < amount:
        return False, "Insufficient funds."

    db["users"][sender]["balance"] -= amount
    db["users"][receiver]["balance"] += amount

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_transaction(sender, {
        "type": "SEND",
        "amount": amount,
        "to": receiver,
        "time": timestamp
    })

    log_transaction(receiver, {
        "type": "RECEIVE",
        "amount": amount,
        "from": sender,
        "time": timestamp
    })

    save_db(db)
    return True, "Money sent successfully!"

def top_up(user, amount):
    db["users"][user]["balance"] += amount

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_transaction(user, {
        "type": "TOPUP",
        "amount": amount,
        "time": timestamp
    })

    save_db(db)
    return True, "Wallet topped up!"

def bill_pay(user, biller, account, amount):
    if db["users"][user]["balance"] < amount:
        return False, "Insufficient balance."

    db["users"][user]["balance"] -= amount

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_transaction(user, {
        "type": "BILL",
        "biller": biller,
        "account": account,
        "amount": amount,
        "time": timestamp
    })

    save_db(db)
    return True, f"Bill payment to {biller} successful!"

def cashout(user, bank, account, amount):
    if db["users"][user]["balance"] < amount:
        return False, "Insufficient balance."

    db["users"][user]["balance"] -= amount

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_transaction(user, {
        "type": "CASHOUT",
        "bank": bank,
        "account": account,
        "amount": amount,
        "time": timestamp
    })

    save_db(db)
    return True, "Cashout successful!"

# ================================
# DASHBOARD UI
# ================================
def dashboard():
    user = st.session_state["email"]
    data = db["users"][user]

    st.markdown(f"<div class='balance-card'>Balance: ${data['balance']} TTD</div>", unsafe_allow_html=True)
    st.write("")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Send Money"):
            st.session_state["page"] = "send"
            st.rerun()
        if st.button("Top-Up Wallet"):
            st.session_state["page"] = "topup"
            st.rerun()

    with col2:
        if st.button("Bill Payments"):
            st.session_state["page"] = "bill"
            st.rerun()
        if st.button("Cashout to Bank"):
            st.session_state["page"] = "cashout"
            st.rerun()

    st.write("### Recent Transactions")

    for tx in reversed(db["users"][user]["transactions"][-10:]):
        if tx["type"] == "SEND":
            st.error(f"Sent ${tx['amount']} → {tx['to']} ({tx['time']})")
        elif tx["type"] == "RECEIVE":
            st.success(f"Received ${tx['amount']} ← {tx['from']} ({tx['time']})")
        elif tx["type"] == "TOPUP":
            st.info(f"Top-Up: +${tx['amount']} ({tx['time']})")
        elif tx["type"] == "BILL":
            st.warning(f"Bill Paid: {tx['biller']} - ${tx['amount']} ({tx['time']})")
        elif tx["type"] == "CASHOUT":
            st.error(f"Cashout: {tx['bank']} - ${tx['amount']} ({tx['time']})")

    st.write("---")
    if st.button("Logout"):
        st.session_state["logged_in"] = False
        st.rerun()


# ================================
# PAGE ROUTER
# ================================
def router():
    page = st.session_state.get("page", "dashboard")

    if page == "dashboard":
        dashboard()

    elif page == "send":
        st.header("Send Money")
        receiver = st.text_input("Receiver Email")
        amount = st.number_input("Amount", min_value=1.0)

        if st.button("Send"):
            ok, msg = send_money(st.session_state["email"], receiver, amount)
            st.success(msg) if ok else st.error(msg)

    elif page == "topup":
        st.header("Top-Up Wallet")
        amount = st.number_input("Top-Up Amount", min_value=5.0)

        if st.button("Add Funds"):
            ok, msg = top_up(st.session_state["email"], amount)
            st.success(msg)

    elif page == "bill":
        st.header("Bill Payments")

        billers = ["T&TEC", "WASA", "FLOW", "DIGICEL", "Bmobile", "Courts"]
        biller = st.selectbox("Select Biller", billers)
        account = st.text_input("Account / Phone Number")
        amount = st.number_input("Amount", min_value=1.0)

        if st.button("Pay Bill"):
            ok, msg = bill_pay(st.session_state["email"], biller, account, amount)
            st.success(msg) if ok else st.error(msg)

    elif page == "cashout":
        st.header("Cashout to Bank")

        banks = [
            "Republic Bank", "RBC", "Scotiabank",
            "First Citizens", "JMMB",
            "Eastern Credit Union", "TECU Credit Union",
            "Venture Credit Union", "Community Credit Union",
            "Police Credit Union"
        ]

        bank = st.selectbox("Select Bank", banks)
        account = st.text_input("Bank Account Number")
        amount = st.number_input("Amount", min_value=1.0)

        if st.button("Cashout"):
            ok, msg = cashout(st.session_state["email"], bank, account, amount)
            st.success(msg) if ok else st.error(msg)

# ================================
# MAIN APP
# ================================
st.title("InstacashTT — Digital Wallet (TTD)")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

menu = st.selectbox("Menu", ["Login", "Register", "Dashboard", "Top-Up Wallet", "Bill Payments", "Cashout to Bank"])

if not st.session_state["logged_in"]:
    if menu == "Login":
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            ok, msg = login_user(email, password)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    elif menu == "Register":
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Register"):
            ok, msg = register_user(email, password)
            st.success(msg) if ok else st.error(msg)

else:
    if menu == "Dashboard":
        st.session_state["page"] = "dashboard"
        router()
    elif menu == "Top-Up Wallet":
        st.session_state["page"] = "topup"
        router()
    elif menu == "Bill Payments":
        st.session_state["page"] = "bill"
        router()
    elif menu == "Cashout to Bank":
        st.session_state["page"] = "cashout"
        router()
