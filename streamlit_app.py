
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


# --- Period 1 Gameplay ---
st.subheader("🎯 Period 1: Choose your action")
if "actions" not in st.session_state:
    st.session_state.actions = {}

player1_options = ["A", "B"]
player2_options = ["X", "Y", "Z"]
payoff_matrix = {
    "A": {"X": (4, 3), "Y": (0, 0), "Z": (1, 4)},
    "B": {"X": (0, 0), "Y": (2, 1), "Z": (0, 0)}
}

# Check for match info and show input
if match:
    match_ref = db.reference(f"games/{match}")
    match_data = match_ref.get() or {}

    role = "P1" if player_name == match.split("_vs_")[0] else "P2"

    if role == "P1":
        choice = st.radio("Select your action (A or B):", player1_options, key="p1_choice")
    else:
        choice = st.radio("Select your action (X, Y, or Z):", player2_options, key="p2_choice")

    if st.button("Submit Period 1 Choice"):
        match_ref.child(role).set(choice)
        st.success("✅ Choice submitted. Waiting for your match partner...")

    # Check if both choices are in
    p1 = match_data.get("P1")
    p2 = match_data.get("P2")
    if p1 and p2:
        st.success(f"🎯 Period 1 Outcome: P1 = {p1}, P2 = {p2} → Payoffs = {payoff_matrix[p1][p2]}")
        match_ref.child("p1_payoff").set(payoff_matrix[p1][p2][0])
        match_ref.child("p2_payoff").set(payoff_matrix[p1][p2][1])
        match_ref.child("round").set(2)
        st.button("Proceed to Period 2", on_click=st.rerun)

# --- Period 2 Gameplay ---
if match and match_data.get("round") == 2:
    st.subheader("🔁 Period 2: Choose again based on Period 1 outcome")
    if role == "P1":
        choice2 = st.radio("Period 2 - Select your action (A or B):", player1_options, key="p1_choice2")
    else:
        choice2 = st.radio("Period 2 - Select your action (X, Y, or Z):", player2_options, key="p2_choice2")

    if st.button("Submit Period 2 Choice"):
        match_ref.child(role + "_2").set(choice2)
        st.success("✅ Choice submitted. Waiting for partner...")

    p1_2 = match_data.get("P1_2")
    p2_2 = match_data.get("P2_2")
    if p1_2 and p2_2:
        st.success(f"🎯 Period 2 Outcome: P1 = {p1_2}, P2 = {p2_2} → Payoffs = {payoff_matrix[p1_2][p2_2]}")
        total_p1 = match_data.get("p1_payoff", 0) + payoff_matrix[p1_2][p2_2][0]
        total_p2 = match_data.get("p2_payoff", 0) + payoff_matrix[p1_2][p2_2][1]
st.markdown(f"""### 🧾 Final Payoffs:"""
- Player 1: {total_p1}
- Player 2: {total_p2}")
        match_ref.child("done").set(True)
