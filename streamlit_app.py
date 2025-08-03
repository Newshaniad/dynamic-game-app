
import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import random
import time

st.set_page_config(page_title="🎲 2-Period Dynamic Game", layout="centered")

# Game info
st.title("🎲 Multiplayer 2-Period Dynamic Game")
st.markdown("""
**Game Description**

You will be matched with another player and play a 2-period dynamic game. In each period, you simultaneously choose an action. After both players submit, the outcome and payoffs will be shown before moving to the next round.

**Payoff Matrix (Player 1, Player 2)**

|       | X     | Y     | Z     |
|-------|-------|-------|-------|
| **A** | (4,3) | (0,0) | (1,4) |
| **B** | (0,0) | (2,1) | (0,0) |
""")

# Firebase config
import json
from google.oauth2 import service_account

# Load credentials and connect to Firebase
firebase_key = json.loads(st.secrets["firebase_key"])
cred = credentials.Certificate(firebase_key)

# ✅ FIX: Initialize only once
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': st.secrets["database_url"]
    })

ref = db.reference("/game")

# Get player name
name = st.text_input("Enter your name to join the game:")

if name:
    st.success(f"👋 Welcome, {name}!")

    player_ref = ref.child("players").child(name)
    pdata = player_ref.get()

    if not pdata:
        # Register player
        player_ref.set({"joined": True, "timestamp": time.time()})
        st.success("✅ Firebase is connected and you are registered.")
        st.experimental_rerun()

    # Check for pairing
    players = ref.child("players").get() or {}
    player_names = list(players.keys())

    # Match players (naive way: by order of join)
    matches = ref.child("matches").get() or {}
    already_paired = set()
    for match in matches.values():
        already_paired.add(match["P1"])
        already_paired.add(match["P2"])

    available = [p for p in player_names if p not in already_paired]
    my_match = None

    for mid, match in matches.items():
        if name == match["P1"] or name == match["P2"]:
            my_match = match
            break

    if not my_match and len(available) >= 2:
        p1, p2 = available[0], available[1]
        match_id = f"{p1}_vs_{p2}"
        new_match = {"P1": p1, "P2": p2, "round": 1, "actions": {}}
        ref.child("matches").child(match_id).set(new_match)
        my_match = new_match
        st.experimental_rerun()

    if not my_match:
        st.info("⏳ Waiting for another player to join...")

    else:
        role = "P1" if name == my_match["P1"] else "P2"
        st.success(f"🎮 Hello, {name}! You are Player {1 if role=='P1' else 2} in match {my_match['P1']}_vs_{my_match['P2']}")

        match_id = f"{my_match['P1']}_vs_{my_match['P2']}"
        action_ref = ref.child("matches").child(match_id).child("actions")
        actions = action_ref.get() or {}

        round_num = my_match["round"]

        if str(round_num) not in actions:
            actions[str(round_num)] = {}

        current_round = actions[str(round_num)]

        if role not in current_round:
            st.subheader(f"🎯 Period {round_num}: Choose your action")

            if role == "P1":
                choice = st.radio("Select action:", ["A", "B"], key=f"{name}_P1")
            else:
                choice = st.radio("Select action:", ["X", "Y", "Z"], key=f"{name}_P2")

            if st.button("Submit", key=f"{name}_submit_{round_num}"):
                current_round[role] = choice
                action_ref.child(str(round_num)).set(current_round)
                st.success("✅ Choice submitted. Waiting for the other player...")
                st.experimental_rerun()

        else:
            st.info("✅ You already submitted your choice. Waiting for the other player...")

        # If both choices submitted, show result
        current_round = action_ref.child(str(round_num)).get()
        if "P1" in current_round and "P2" in current_round:
            p1_choice = current_round["P1"]
            p2_choice = current_round["P2"]

            payoff_matrix = {
                "A": {"X": (4, 3), "Y": (0, 0), "Z": (1, 4)},
                "B": {"X": (0, 0), "Y": (2, 1), "Z": (0, 0)}
            }

            result = payoff_matrix[p1_choice][p2_choice]
            st.success(f"🎯 Period {round_num} Outcome: P1 = {p1_choice}, P2 = {p2_choice} → Payoffs = {result}")

            if round_num == 1:
                # Proceed to round 2
                ref.child("matches").child(match_id).child("round").set(2)
                st.button("🔁 Continue to Period 2", on_click=st.experimental_rerun)
