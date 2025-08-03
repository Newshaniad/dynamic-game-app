
import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import json
import random
import time

st.set_page_config(page_title="🎲 2-Period Dynamic Game", layout="centered")

st.title("🎲 Multiplayer 2-Period Dynamic Game")

# --- Game Description ---
st.markdown("""
**Game Description**  
You will be matched with another player and play a 2-period dynamic game. In each period, you simultaneously choose an action. After both players submit, the outcome and payoffs will be shown before moving to the next round.

**Payoff Matrix (Player 1, Player 2)**:
```
        X       Y       Z
A   (4, 3)   (0, 0)   (1, 4)
B   (0, 0)   (2, 1)   (0, 0)
```
""", unsafe_allow_html=True)

# --- Firebase Setup ---
if "firebase_initialized" not in st.session_state:
    cred = credentials.Certificate(json.loads(st.secrets["firebase_key"]))
    firebase_admin.initialize_app(cred, {
        'databaseURL': st.secrets["database_url"]
    })
    st.session_state.firebase_initialized = True

name = st.text_input("Enter your name to join the game:")
if name:
    st.success(f"👋 Welcome, {name}!")
    player_ref = db.reference(f"players/{name}")
    player_ref.set({"joined": True, "timestamp": time.time()})

    # Check if already matched
    existing_matches = db.reference("matches").get() or {}
    match_id = None
    for m_id, m_data in existing_matches.items():
        if name in m_data.values():
            match_id = m_id
            role = [r for r, n in m_data.items() if n == name][0]
            break

    # If not matched, try to find another unmatched player
    if not match_id:
        players = db.reference("players").get() or {}
        waiting = [p for p in players if p != name]
        if waiting:
            opponent = waiting[0]
            match_id = f"{opponent}_vs_{name}"
            db.reference(f"matches/{match_id}").set({"P1": opponent, "P2": name})
            role = "P2"
        else:
            st.info("⏳ Waiting for another player to join...")
            st.stop()

    st.success(f"🎮 Hello, {name}! You are Player {1 if role == 'P1' else 2} in match {match_id}")

    # Save session info
    st.session_state.name = name
    st.session_state.role = role
    st.session_state.match_id = match_id

# --- Period 1 Actions ---
if "match_id" in st.session_state:
    match_id = st.session_state.match_id
    role = st.session_state.role

    if "round" not in st.session_state:
        st.session_state.round = 1

    if st.session_state.round == 1:
        st.subheader("🎮 Period 1: Choose your action")

        if role == "P1":
            action1 = st.radio("Choose your action (Player 1):", ["A", "B"], key="p1_action")
            if st.button("Submit Action"):
                db.reference(f"games/{match_id}/actions/period1/P1").set(action1)
                st.success("✅ Action submitted. Waiting for Player 2...")
                st.rerun()

        elif role == "P2":
            action2 = st.radio("Choose your action (Player 2):", ["X", "Y", "Z"], key="p2_action")
            if st.button("Submit Action"):
                db.reference(f"games/{match_id}/actions/period1/P2").set(action2)
                st.success("✅ Action submitted. Waiting for Player 1...")
                st.rerun()

        # Check if both actions submitted
        actions = db.reference(f"games/{match_id}/actions/period1").get()
        if actions and "P1" in actions and "P2" in actions:
            a1 = actions["P1"]
            a2 = actions["P2"]

            payoff_matrix = {
                "A": {"X": (4,3), "Y": (0,0), "Z": (1,4)},
                "B": {"X": (0,0), "Y": (2,1), "Z": (0,0)}
            }
            payoff = payoff_matrix[a1][a2]
            st.success(f"🎯 Period 1 Outcome: P1 = {a1}, P2 = {a2} → Payoffs = {payoff}")
            db.reference(f"games/{match_id}/results/period1").set({"P1": a1, "P2": a2, "payoff": payoff})
            st.session_state.round = 2
            st.rerun()
