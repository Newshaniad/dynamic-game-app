
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



# Define actions
actions_p1 = ["A", "B"]
actions_p2 = ["X", "Y", "Z"]
payoff_matrix = {
    ("A", "X"): (4, 3), ("A", "Y"): (0, 0), ("A", "Z"): (1, 4),
    ("B", "X"): (0, 0), ("B", "Y"): (2, 1), ("B", "Z"): (0, 0),
}

match_ref = db.reference(f"matches/{match_id}")
game_state = match_ref.get() or {}

# Period 1
if "period1" not in game_state:
    st.subheader("🎮 Period 1: Make your choice")
    if role == "P1":
        choice = st.radio("Choose your action:", actions_p1, key="p1_period1")
    else:
        choice = st.radio("Choose your action:", actions_p2, key="p2_period1")

    if st.button("Submit Period 1 Choice"):
        match_ref.child("period1").child(role).set(choice)
        st.success("✅ Choice submitted. Waiting for your opponent...")

    # Check if both choices are in
    pdata = match_ref.child("period1").get()
    if pdata and "P1" in pdata and "P2" in pdata:
        p1_choice = pdata["P1"]
        p2_choice = pdata["P2"]
        outcome = payoff_matrix[(p1_choice, p2_choice)]
        match_ref.child("period1").child("payoff").set(outcome)
        st.success(f"🎯 Period 1 Outcome: P1 = {p1_choice}, P2 = {p2_choice} → Payoffs = {outcome}")
        st.rerun()

# Period 2
elif "period2" not in game_state:
    st.subheader("🎮 Period 2: Based on Period 1 outcome")
    last_choices = game_state["period1"]
    if "payoff" in last_choices:
        outcome = last_choices["payoff"]
        st.info(f"📊 Period 1: P1 = {last_choices['P1']}, P2 = {last_choices['P2']} → Payoffs = {outcome}")

    if role == "P1":
        choice = st.radio("Choose your action:", actions_p1, key="p1_period2")
    else:
        choice = st.radio("Choose your action:", actions_p2, key="p2_period2")

    if st.button("Submit Period 2 Choice"):
        match_ref.child("period2").child(role).set(choice)
        st.success("✅ Period 2 choice submitted. Waiting for opponent...")

    # Show results if both submitted
    pdata = match_ref.child("period2").get()
    if pdata and "P1" in pdata and "P2" in pdata:
        p1_choice = pdata["P1"]
        p2_choice = pdata["P2"]
        outcome = payoff_matrix[(p1_choice, p2_choice)]
        match_ref.child("period2").child("payoff").set(outcome)
        st.success(f"🎯 Period 2 Outcome: P1 = {p1_choice}, P2 = {p2_choice} → Payoffs = {outcome}")
        st.balloons()
