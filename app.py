import streamlit as st
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore, auth

# -----------------------------
# FIREBASE INITIALIZATION
# -----------------------------
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# -----------------------------
# HELPERS
# -----------------------------
def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# -------- USER FUNCTIONS --------
def create_user(email, password):
    try:
        # Create Firebase Auth account
        user = auth.create_user(email=email, password=password)

        # Create Firestore wallet entry
        db.collection("users").document(user.uid).set({
            "email": email,
            "balance": 0.0,
            "created_at": now_str()
        })

        return True, "Wallet created successfully."

    except Exception as e:
        return False, f"Error: {str(e)}"


def authenticate(email, password):
    """
    Firebase Admin cannot validate passwords directly.
    For MVP testing, we only verify if the user exists.
    """
    try:
        user = auth.get_user_by_email(email)
        return True, user.uid
    except:
        return False, "Invalid login credentials."


def get_user(uid):
    doc = db.collection("users").document(uid).get()
    return doc.to_dict() if doc.exists else None


def update_balance(uid, new_balance):
    db.collection("users").document(uid).update({"balance": new_balance})


def add_transaction(uid, data):
    db.collection("transactions").document(uid).collection("records").add(data)


def get_transactions(uid):
    docs = db.collection("transactions").document(uid).collection("records").order_by(
        "timestamp", direction=firestore.Query.DESCENDING
    ).stream()

    return [d.to_dict() for d in docs]


# -----------------------------
# STREAMLIT SETUP
# -----------------------------
st.set_page_config(page_title="InstacashTT — Digital Wallet", page_icon="💳")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "uid" not in st.session_state:
    st.session_state.uid = None

if "email" not in st.session_state:
    st.session_state.email = None

if "menu_state" not in st.session_state:
    st.session_state.menu_state = "login"

# -----------------------------
# HEADER
# -----------------------------
def header():
    col1, col2 = st.columns([1, 8])
    with col1:
        st.image("InstacashTT.png", width=70)
    with col2:
        st.markdown("""
            <h1 style="margin-top:15px;">
                InstacashTT — Digital Wallet (TTD)
            </h1>
        """, unsafe_allow_html=True)


# -----------------------------
# LOGIN VIEW
# -----------------------------
def login_view():
    header()
    st.subheader("Login to Your Wallet")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login", key="login_button", use_container_width=True):
        ok, result = authenticate(email, password)
        if ok:
            st.session_state.logged_in = True
            st.session_state.email = email
            st.session_state.uid = result
            st.rerun()
        else:
            st.error(result)

    if st.button("Go to Register", key="go_register"):
        st.session_state.menu_state = "register"
        st.rerun()


# -----------------------------
# REGISTER VIEW
# -----------------------------
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


# -----------------------------
# WALLET VIEW
# -----------------------------
def wallet_view():
    uid = st.session_state.uid
    user = get_user(uid)

    header()
    st.write("")

    st.subheader("Your Balance")
    st.markdown(
        f"""<h2 style="font-size: 32px; font-weight:600;">
            ${user['balance']:.2f} TTD
        </h2>""",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # ---------------- TOP UP ----------------
    st.subheader("Top Up Wallet")

    if "topup_method" not in st.session_state:
        st.session_state.topup_method = None

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

    topup_amount = st.number_input(
        "Amount", min_value=0.0, step=1.0, key="topup_amount_input"
    )

    if st.button("Confirm Top-Up", use_container_width=True):
        if topup_amount <= 0:
            st.error("Amount must be greater than 0.")
        elif st.session_state.topup_method is None:
            st.error("Select a top-up method.")
        else:
            new_balance = user["balance"] + topup_amount
            update_balance(uid, new_balance)

            add_transaction(uid, {
                "type": "Topup",
                "amount": topup_amount,
                "method": st.session_state.topup_method,
                "timestamp": now_str()
            })

            st.success(
                f"Topped up ${topup_amount:.2f} via {st.session_state.topup_method}"
            )

    st.markdown("---")

    # ---------------- SEND MONEY ----------------
    st.subheader("Send Money")

    receiver_email = st.text_input("Receiver Email", key="send_receiver")
    amount = st.number_input("Amount", min_value=0.0, step=1.0, key="send_amount")

    if st.button("Send", key="send_button"):
        receiver_email = receiver_email.strip()
        if receiver_email == st.session_state.email:
            st.error("You can't send money to yourself.")
        else:
            try:
                receiver_user = auth.get_user_by_email(receiver_email)
                receiver_uid = receiver_user.uid
            except:
                st.error("Receiver not found.")
                return

            if amount <= 0:
                st.error("Amount must be greater than 0.")
            elif amount > user["balance"]:
                st.error("Insufficient funds.")
            else:
                update_balance(uid, user["balance"] - amount)

                receiver_data = get_user(receiver_uid)
                update_balance(receiver_uid, receiver_data["balance"] + amount)

                timestamp = now_str()

                add_transaction(uid, {
                    "type": "Sent",
                    "amount": amount,
                    "to": receiver_email,
                    "timestamp": timestamp
                })

                add_transaction(receiver_uid, {
                    "type": "Received",
                    "amount": amount,
                    "from": st.session_state.email,
                    "timestamp": timestamp
                })

                st.success(f"Sent ${amount:.2f} to {receiver_email}")

    st.markdown("---")

    # ---------------- BILL PAYMENTS ----------------
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
            new_balance = user["balance"] - bill_amt
            update_balance(uid, new_balance)

            add_transaction(uid, {
                "type": "Bill_payment",
                "amount": bill_amt,
                "to": biller,
                "account": acct,
                "timestamp": now_str()
            })

            st.success(f"Paid ${bill_amt:.2f} to {biller}")

    st.markdown("---")

    # ---------------- CASHOUT ----------------
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
            update_balance(uid, user["balance"] - cashout_amt)

            add_transaction(uid, {
                "type": "Cashout",
                "amount": cashout_amt,
                "bank": bank,
                "account": acctnum,
                "timestamp": now_str()
            })

            st.success(f"Cashout sent to {bank}")

    st.markdown("---")

    # ---------------- HISTORY ----------------
    st.subheader("Transaction History")

    tx_list = get_transactions(uid)

    if tx_list:
        for tx in tx_list:
            st.markdown(
                f"""
                **{tx['type']}** — ${tx['amount']:.2f}  
                `{tx['timestamp']}`
                """,
                unsafe_allow_html=True
            )
    else:
        st.info("No transactions yet.")

    st.markdown("---")

    # ---------------- LOGOUT ----------------
    if st.button("Logout", key="logout_button", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.email = None
        st.session_state.uid = None
        st.session_state.menu_state = "login"
        st.rerun()


# -----------------------------
# ROUTING
# -----------------------------
if not st.session_state.logged_in:
    if st.session_state.menu_state == "login":
        login_view()
    else:
        register_view()
else:
    wallet_view()
