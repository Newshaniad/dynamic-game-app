
import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import json
import time
import random

st.set_page_config(page_title="🎲 2-Period Dynamic Game")

st.title("🎲 Multiplayer 2-Period Dynamic Game")

# Game description
st.markdown("""
**Game Description**  
You will be matched with another player and play a 2-period dynamic game. In each period, you simultaneously choose an action.  
After both players submit, the outcome and payoffs will be shown before moving to the next round.

**Payoff Matrix (Player 1, Player 2):**

|     | X       | Y       | Z       |
|-----|---------|---------|---------|
| A   | (4, 3)  | (0, 0)  | (1, 4)  |
| B   | (0, 0)  | (2, 1)  | (0, 0)  |
""")

# Firebase credentials and config
firebase_key = st.secrets["firebase_key"]
database_url = st.secrets["database_url"]

if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(firebase_key))
    firebase_admin.initialize_app(cred, {
        'databaseURL': database_url
    })

name = st.text_input("Enter your name to join the game:")

if name:
    st.success(f"👋 Welcome, {name}!")

    player_ref = db.reference(f"players/{name}")
    player_data = player_ref.get()

    if not player_data:
        player_ref.set({
            "joined": True,
            "timestamp": time.time()
        })
        st.write("✅ Firebase is connected and you are registered.")

    match_ref = db.reference("matches")
    match_data = match_ref.get() or {}

    # Check if player already matched
    already_matched = False
    for match_id, info in match_data.items():
        if name in info.get("players", []):
            role = "Player 1" if info["players"][0] == name else "Player 2"
            st.success(f"🎮 Hello, {name}! You are {role} in match {match_id}")
            already_matched = True
            break

    if not already_matched:
        unmatched = [p for p in db.reference("players").get().keys()
                     if not any(p in m.get("players", []) for m in match_data.values())
                     and p != name]

        if unmatched:
            partner = unmatched[0]
            pair = sorted([name, partner])
            match_id = f"{pair[0]}_vs_{pair[1]}"
            match_ref.child(match_id).set({"players": pair})
            role = "Player 1" if pair[0] == name else "Player 2"
            st.success(f"🎮 Hello, {name}! You are {role} in match {match_id}")
        else:
            st.info("⏳ Waiting for another player to join...")
            with st.spinner("Checking for match..."):
                timeout = 30
                for i in range(timeout):
                    match_data = match_ref.get() or {}
                    for match_id, info in match_data.items():
                        if name in info.get("players", []):
                            role = "Player 1" if info["players"][0] == name else "Player 2"
                            st.success(f"🎮 Hello, {name}! You are {role} in match {match_id}")
                            st.rerun()
                    time.sleep(2)


# --- Round 1 Logic ---

# ------------------------
# ROUND 1 - PLAYER ACTIONS
# ------------------------

# Define period 1 choices
st.subheader("🎯 Period 1: Choose Your Action")

if "round1_done" not in st.session_state:
    st.session_state.round1_done = False

if not st.session_state.round1_done:
    if role == "P1":
        p1_choice = st.radio("Player 1: Choose A or B", ["A", "B"], key="p1_choice_r1")
    else:
        p2_choice = st.radio("Player 2: Choose X, Y, or Z", ["X", "Y", "Z"], key="p2_choice_r1")

    if st.button("Submit Period 1 Choice"):
        if role == "P1":
            db.reference(f"games/{match_id}/round1/P1").set(st.session_state.p1_choice_r1)
        else:
            db.reference(f"games/{match_id}/round1/P2").set(st.session_state.p2_choice_r1)
        st.success("✅ Choice submitted. Waiting for your opponent...")
        st.session_state.round1_done = True
        st.rerun()

# Display results once both players submitted
round1_ref = db.reference(f"games/{match_id}/round1")
round1_data = round1_ref.get()
if round1_data and "P1" in round1_data and "P2" in round1_data:
    st.success(f"🎯 Period 1 Outcome: P1 = {round1_data['P1']}, P2 = {round1_data['P2']}")
    payoff_matrix = {
        ("A", "X"): (4, 3),
        ("A", "Y"): (0, 0),
        ("A", "Z"): (1, 4),
        ("B", "X"): (0, 0),
        ("B", "Y"): (2, 1),
        ("B", "Z"): (0, 0),
    }
    p1_payoff, p2_payoff = payoff_matrix.get((round1_data["P1"], round1_data["P2"]), (0, 0))
    st.write(f"💰 Payoffs → Player 1: {p1_payoff}, Player 2: {p2_payoff}")
    st.session_state.round1_outcome = {
        "P1": round1_data["P1"],
        "P2": round1_data["P2"],
        "payoff": (p1_payoff, p2_payoff)
    }
