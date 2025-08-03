
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

# --- PERIOD 1 CHOICE ---
match_ref = db.reference(f"matches/{match_id}")
actions_ref = match_ref.child("period1_actions")

player_action = actions_ref.child(name).get()

if not player_action:
    st.subheader("🎮 Period 1: Make your move")
    
    if role == "P1":
        move = st.radio("Choose your action (Player 1):", ["A", "B"])
    else:
        move = st.radio("Choose your action (Player 2):", ["X", "Y", "Z"])

    if st.button("Submit Move"):
        actions_ref.child(name).set(move)
        st.success("✅ Move submitted. Waiting for other player...")
        st.rerun()
else:
    st.info("✅ You submitted your move. Waiting for your opponent...")

# Check if both moves submitted
actions = actions_ref.get()
if actions and len(actions) == 2:
    p1_move = actions.get(player1)
    p2_move = actions.get(player2)

    # PAYOFF LOGIC
    payoff_matrix = {
        "A": {"X": (4, 3), "Y": (0, 0), "Z": (1, 4)},
        "B": {"X": (0, 0), "Y": (2, 1), "Z": (0, 0)},
    }

    p1_payoff, p2_payoff = payoff_matrix[p1_move][p2_move]

    st.success(f"🎯 Period 1 Result: P1 = {p1_move}, P2 = {p2_move} → Payoffs = ({p1_payoff}, {p2_payoff})")

    # Store result for Period 2 reference
    match_ref.child("period1_result").set({
        "p1_move": p1_move,
        "p2_move": p2_move,
        "p1_payoff": p1_payoff,
        "p2_payoff": p2_payoff
    })

    st.button("🔁 Continue to Period 2", on_click=st.rerun)

