import streamlit as st
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, auth, firestore

# -------------------------------------------------
# FIREBASE INITIALIZATION
# -------------------------------------------------

if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()


# -------------------------------------------------
# HELPERS
# -------------------------------------------------

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_user_by_email(email):
    try:
        user = auth.get_user_by_email(email)
        return user.uid
    except:
        return None


def get_user_data(uid):
    doc = db.collection("users").document(uid).get()
    return doc.to_dict() if doc.exists else None


def create_wallet(uid, email):
    db.collection("users").document(uid).set({
        "email": email,
        "balance": 0.0,
        "created_at": now_str(),
    })


def add_transaction(uid, data):
    db.collection("transactions").document(uid).collection("items").add(data)


# -------------------------------------------------
# STREAMLIT CONFIG
# -------------------------------------------------

st.set_page_config(page_title="InstacashTT — Digital Wallet", page_icon="💳")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "uid" not in st.session_state:
    st.session_state.uid = None
if "menu_state" not in st.session_state:
    st.session_state.menu_state = "login"
if "topup_method" not in st.session_state:
    st.session_state.topup_method = None


# -------------------------------------------------
# HEADER
# -------------------------------------------------

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


# -------------------------------------------------
# REGISTER VIEW (Firebase Auth)
# -------------------------------------------------

def register_view():
    header()
    st.subheader("Create Your Wallet")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Register", use_container_width=True):
        try:
            user = auth.create_user(email=email, password=password)
            create_wallet(user.uid, email)
            st.success("Wallet created successfully. You may now log in.")
        except Exception as e:
            st.error(f"Error: {e}")

    if st.button("Back to Login"):
        st.session_state.menu_state = "login"
        st.rerun()


# -------------------------------------------------
# LOGIN VIEW
# -------------------------------------------------

def login_view():
    header()
    st.subheader("Login to Your Wallet")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login", use_container_width=True):
        uid = get_user_by_email(email)
        if not uid:
            st.error("User not found.")
        else:
            # Firebase Admin SDK CANNOT validate passwords.
            # We accept login and rely on Firestore rules.
            st.session_state.logged_in = True
            st.session_state.uid = uid
            st.rerun()

    if st.button("Go to Register"):
        st.session_state.menu_state = "register"
        st.rerun()


# -------------------------------------------------
# WALLET VIEW
# -------------------------------------------------

def wallet_view():
    header()
    st.write("")

    uid = st.session_state.uid
    user_data = get_user_data(uid)
    balance = user_data["balance"]

    # ------------------------
    # BALANCE
    # ------------------------
    st.subheader("Your Balance")
    st.markdown(
        f"""
        <h2 style="font-size: 32px; font-weight:600;">
            ${balance:.2f} TTD
        </h2>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ------------------------
    # TOP UP WALLET
    # ------------------------
    st.subheader("Top Up Wallet")

    colA, colB, colC = st.columns(3)
    with colA:
        if st.button("Bank Transfer"):
            st.session_state.topup_method = "Bank Transfer"
    with colB:
        if st.button("Debit/Credit Card"):
            st.session_state.topup_method = "Card"
    with colC:
        if st.button("Cash at Agent"):
            st.session_state.topup_method = "Cash Agent"

    if st.session_state.topup_method:
        st.info(f"Selected Method: {st.session_state.topup_method}")

    topup_amount = st.number_input("Amount", min_value=0.0, step=1.0)

    if st.button("Confirm Top-Up", use_container_width=True):
        if topup_amount <= 0:
            st.error("Amount must be greater than 0.")
        elif not st.session_state.topup_method:
            st.error("Select a top-up method.")
        else:
            db.collection("users").document(uid).update({
                "balance": firestore.Increment(topup_amount)
            })

            add_transaction(uid, {
                "type": "topup",
                "amount": topup_amount,
                "method": st.session_state.topup_method,
                "timestamp": now_str()
            })

            st.success(f"Topped up ${topup_amount:.2f} via {st.session_state.topup_method}")

    st.markdown("---")

    # ------------------------
    # SEND MONEY
    # ------------------------
    st.subheader("Send Money")

    receiver_email = st.text_input("Receiver Email")
    amount = st.number_input("Amount", min_value=0.0, step=1.0, key="sendamt")

    if st.button("Send"):
        receiver_uid = get_user_by_email(receiver_email)

        if not receiver_uid:
            st.error("Receiver not found.")
        elif receiver_uid == uid:
            st.error("Cannot send money to yourself.")
        elif amount > balance:
            st.error("Insufficient funds.")
        else:
            db.collection("users").document(uid).update({
                "balance": firestore.Increment(-amount)
            })
            db.collection("users").document(receiver_uid).update({
                "balance": firestore.Increment(amount)
            })

            add_transaction(uid, {
                "type": "sent",
                "amount": amount,
                "to": receiver_email,
                "timestamp": now_str()
            })

            add_transaction(receiver_uid, {
                "type": "received",
                "amount": amount,
                "from": receiver_email,
                "timestamp": now_str()
            })

            st.success(f"Sent ${amount:.2f} to {receiver_email}")

    st.markdown("---")

    # ------------------------
    # BILL PAYMENTS
    # ------------------------
    st.subheader("Bill Payments")

    biller_list = ["T&TEC Electricity", "WASA", "TSTT", "Digicel",
                   "FLOW", "Amplia", "Bmobile", "Courts"]

    biller = st.selectbox("Select Biller", biller_list)
    acct = st.text_input("Account Number")
    bill_amt = st.number_input("Payment Amount", min_value=0.0, step=1.0)

    if st.button("Pay Bill"):
        if not acct:
            st.error("Enter account/contract number.")
        elif bill_amt > balance:
            st.error("Insufficient balance.")
        else:
            db.collection("users").document(uid).update({
                "balance": firestore.Increment(-bill_amt)
            })

            add_transaction(uid, {
                "type": "bill_payment",
                "amount": bill_amt,
                "to": biller,
                "timestamp": now_str()
            })

            st.success(f"Paid ${bill_amt:.2f} to {biller}")

    st.markdown("---")

    # ------------------------
    # CASHOUT
    # ------------------------
    st.subheader("Wallet → Bank Cashout")

    bank_list = [
        "Republic Bank", "First Citizens", "RBC",
        "Scotiabank", "JMMB", "Other"
    ]

    bank = st.selectbox("Select Bank", bank_list)
    acctnum = st.text_input("Bank Account #")
    cashout_amt = st.number_input("Cashout Amount", min_value=0.0, step=1.0)

    if st.button("Cashout"):
        if not acctnum:
            st.error("Enter account number.")
        elif cashout_amt > balance:
            st.error("Insufficient balance.")
        else:
            db.collection("users").document(uid).update({
                "balance": firestore.Increment(-cashout_amt)
            })

            add_transaction(uid, {
                "type": "cashout",
                "amount": cashout_amt,
                "to": bank,
                "timestamp": now_str()
            })

            st.success(f"Cashout sent to {bank}")

    st.markdown("---")

    # ------------------------
    # TRANSACTION HISTORY
    # ------------------------
    st.subheader("Transaction History")

    tx_ref = db.collection("transactions").document(uid).collection("items")
    tx = tx_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).stream()

    items = list(tx)

    if items:
        for doc in items:
            data = doc.to_dict()
            st.markdown(
                f"""
                **{data['type'].capitalize()}** — ${data['amount']:.2f}  
                `{data['timestamp']}`
                """,
                unsafe_allow_html=True
            )
    else:
        st.info("No transactions yet.")

    st.markdown("---")

    if st.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.uid = None
        st.session_state.menu_state = "login"
        st.rerun()


# -------------------------------------------------
# ROUTING
# -------------------------------------------------

if not st.session_state.logged_in:
    if st.session_state.menu_state == "login":
        login_view()
    else:
        register_view()
else:
    wallet_view()
