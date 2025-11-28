import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import random
import string
import time

# --------------------------------------------
# FIREBASE INITIALIZATION
# --------------------------------------------
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_key.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --------------------------------------------
# 2FA / EMAIL OTP (DEBUG MODE)
# --------------------------------------------
def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(email, otp):
    """
    Placeholder function.
    Replace with Gmail API or SendGrid for production.
    """
    print(f"[DEBUG] OTP sent to {email}: {otp}")

# --------------------------------------------
# HELPERS
# --------------------------------------------
def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_user(email):
    return db.collection("users").document(email).get()

def create_user(email, password):
    ref = db.collection("users").document(email)
    if ref.get().exists:
        return False, "User already exists."

    ref.set({
        "email": email,
        "password": password,
        "balance": 0.0,
        "created_at": now_str()
    })
    return True, "Wallet created successfully."

def authenticate(email, password):
    doc = get_user(email)
    if not doc.exists:
        return False, "User not found."

    data = doc.to_dict()
    if data["password"] != password:
        return False, "Incorrect password."

    return True, ""

# --------------------------------------------
# OTP (Option C)
# --------------------------------------------
def send_login_otp(email):
    otp = generate_otp()
    expiry = datetime.now() + timedelta(minutes=5)

    db.collection("otps").document(email).set({
        "otp": otp,
        "expires": expiry.timestamp()
    })

    send_otp_email(email, otp)
    return otp

def verify_otp(email, otp_input):
    doc = db.collection("otps").document(email).get()

    if not doc.exists:
        return False, "No OTP found."

    data = doc.to_dict()

    if otp_input != data["otp"]:
        return False, "Incorrect OTP."

    if time.time() > data["expires"]:
        return False, "OTP expired."

    return True, ""

# --------------------------------------------
# WiPay Hosted Checkout Placeholder (Option A)
# --------------------------------------------
def create_wipay_checkout(amount, email, method):
    placeholder_wipay_url = "https://sandbox.wipaycaribbean.com/checkout"
    return_url = "https://instacash.streamlit.app"  # placeholder return URL

    return (
        f"{placeholder_wipay_url}?"
        f"amount={amount}&email={email}&method={method}&return_url={return_url}"
    )

def open_new_tab(url):
    st.markdown(
        f"""
        <script>
            window.open("{url}", "_blank").focus();
        </script>
        """,
        unsafe_allow_html=True
    )

# --------------------------------------------
# STREAMLIT CONFIG
# --------------------------------------------
st.set_page_config(page_title="InstacashTT Digital Wallet", page_icon="💳")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "email" not in st.session_state:
    st.session_state.email = None
if "pending_otp" not in st.session_state:
    st.session_state.pending_otp = False

# --------------------------------------------
# HEADER
# --------------------------------------------
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
            unsafe_allow_html=True
        )

# --------------------------------------------
# LOGIN VIEW
# --------------------------------------------
def login_view():
    header()
    st.subheader("Login to Your Wallet")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        ok, msg = authenticate(email, password)
        if not ok:
            st.error(msg)
            return

        send_login_otp(email)
        st.session_state.pending_otp = True
        st.session_state.email = email
        st.success("OTP sent! Check your email.")
        st.rerun()

    if st.session_state.pending_otp:
        otp_input = st.text_input("Enter OTP")
        if st.button("Verify OTP"):
            ok, msg = verify_otp(st.session_state.email, otp_input)
            if ok:
                st.session_state.logged_in = True
                st.session_state.pending_otp = False
                st.success("Login successful!")
                st.rerun()
            else:
                st.error(msg)

# --------------------------------------------
# REGISTER VIEW
# --------------------------------------------
def register_view():
    header()
    st.subheader("Create Your Wallet")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Register"):
        ok, msg = create_user(email, password)
        if ok:
            st.success("Wallet created successfully. You may now log in.")
        else:
            st.error(msg)

# --------------------------------------------
# WALLET VIEW (UI unchanged)
# --------------------------------------------
def wallet_view():
    header()

    user_doc = get_user(st.session_state.email)
    user = user_doc.to_dict()

    st.subheader("Your Balance")
    st.markdown(
        f"""
        <h2 style="font-size:32px;font-weight:600;">
            ${user['balance']:.2f} TTD
        </h2>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    # --------------------------------------------
    # TOP UP — via WiPay Hosted Page
    # --------------------------------------------
    st.subheader("Top Up Wallet")

    colA, colB, colC = st.columns(3)

    if "topup_method" not in st.session_state:
        st.session_state.topup_method = None

    with colA:
        if st.button("Bank Transfer"):
            st.session_state.topup_method = "bank"

    with colB:
        if st.button("Debit/Credit Card"):
            st.session_state.topup_method = "card"

    with colC:
        if st.button("Cash at Agent"):
            st.session_state.topup_method = "cash"

    st.info(f"Selected: {st.session_state.topup_method}")

    topup_amount = st.number_input("Amount", min_value=0.0)

    if st.button("Proceed to Payment"):
        url = create_wipay_checkout(
            amount=topup_amount,
            email=st.session_state.email,
            method=st.session_state.topup_method
        )

        open_new_tab(url)

        # DEMO MODE: AUTO-CREDIT WALLET
        db.collection("users").document(st.session_state.email).update({
            "balance": firestore.Increment(topup_amount)
        })

        db.collection("transactions").add({
            "type": "topup",
            "email": st.session_state.email,
            "amount": topup_amount,
            "method": st.session_state.topup_method,
            "timestamp": now_str()
        })

        st.success("Top-up successful! (Demo Mode)")

    st.markdown("---")

    # --------------------------------------------
    # SEND MONEY
    # --------------------------------------------
    st.subheader("Send Money")

    receiver = st.text_input("Receiver Email")
    amount = st.number_input("Amount to Send", min_value=0.0)

    if st.button("Send"):
        receiver_doc = get_user(receiver)
        if not receiver_doc.exists:
            st.error("Receiver not found.")
        elif amount > user["balance"]:
            st.error("Insufficient funds.")
        else:
            # Deduct from sender
            db.collection("users").document(st.session_state.email).update({
                "balance": user["balance"] - amount
            })

            # Add to receiver
            db.collection("users").document(receiver).update({
                "balance": firestore.Increment(amount)
            })

            db.collection("transactions").add({
                "type": "transfer",
                "from": st.session_state.email,
                "to": receiver,
                "amount": amount,
                "timestamp": now_str()
            })

            st.success(f"Sent ${amount:.2f} to {receiver}")

    st.markdown("---")

    # --------------------------------------------
    # LOGOUT
    # --------------------------------------------
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.email = None
        st.rerun()

# --------------------------------------------
# ROUTING
# --------------------------------------------
if not st.session_state.logged_in:
    choice = st.radio("Menu", ["Login", "Register"])
    if choice == "Login":
        login_view()
    else:
        register_view()
else:
    wallet_view()
