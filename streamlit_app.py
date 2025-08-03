
import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import json
import time

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(st.secrets["firebase_key"]))
    firebase_admin.initialize_app(cred, {
        'databaseURL': st.secrets["database_url"]
    })

ref = db.reference("games")

# UI
st.title("🎲 Multiplayer 2-Period Dynamic Game")

st.markdown("""
### Game Description
You will be matched with another player and play a 2-period dynamic game.
In each period, you simultaneously choose an action.
After both players submit, the outcome and payoffs will be shown before moving to the next round.
""")

st.markdown("""
**Payoff Matrix (Player 1, Player 2):**

|       | X      | Y      | Z      |
|-------|--------|--------|--------|
| **A** | (4, 3) | (0, 0) | (1, 4) |
| **B** | (0, 0) | (2, 1) | (0, 0) |
""")

name = st.text_input("Enter your name to join the game:")
if name:
    st.success(f"👋 Welcome, {name}!")

    # Game logic placeholder: simulate result display
    period = 1
    p1_choice = "A"
    p2_choice = "Z"
    payoff_p1, payoff_p2 = 1, 4

    st.markdown(f"""
    ### 🎯 Period {period} Outcome:
    - Player 1: {p1_choice}
    - Player 2: {p2_choice}
    - Payoffs: ({payoff_p1}, {payoff_p2})
    """)

    # Example total payoff
    total_p1 = 5
    total_p2 = 6

    st.markdown(f"""
    ### 🧾 Final Payoffs:
    - Player 1: {total_p1}
    - Player 2: {total_p2}
    """)
