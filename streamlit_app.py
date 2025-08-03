
import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import time
import random
import json

# --- Firebase Setup ---
if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(st.secrets["firebase_key"]))
    firebase_admin.initialize_app(cred, {
        'databaseURL': st.secrets["database_url"]
    })

ref = db.reference("/players")

# --- Game Description ---
st.title("🎲 2-Period Dynamic Game")

st.markdown("""
**Game Description**  
You will be matched with another player and play a **2-period dynamic game**.  
In each period, you simultaneously choose an action.  
After both players submit, the **outcome and payoffs** will be shown before moving to the next round.

**Payoff Matrix (Player 1, Player 2):**

|     | X       | Y       | Z       |
|-----|---------|---------|---------|
| A   | (4, 3)  | (0, 0)  | (1, 4)  |
| B   | (0, 0)  | (2, 1)  | (0, 0)  |
""")

# --- Name Entry ---
player_name = st.text_input("Enter your name to join the game:")

if player_name:
    st.success(f"👋 Welcome, {player_name}!")

    player_ref = ref.child(player_name)
    player_data = player_ref.get()

    if not player_data:
        player_ref.set({
            "joined": True,
            "timestamp": time.time(),
            "role": "",
            "opponent": "",
            "choice1": "",
            "choice2": "",
            "result1": "",
            "result2": ""
        })

    all_players = ref.get()
    waiting_players = [p for p in all_players if not all_players[p]["opponent"] and p != player_name]

    if not player_data["opponent"]:
        if waiting_players:
            opponent = waiting_players[0]
            role = "P2"
            opp_role = "P1"
            match_id = f"{opponent}_vs_{player_name}"
            # Set opponents
            ref.child(player_name).update({"opponent": opponent, "role": role})
            ref.child(opponent).update({"opponent": player_name, "role": opp_role})
            st.session_state.match_id = match_id
        else:
            st.info("⏳ Waiting for another player to join...")
            st.stop()
    else:
        opponent = player_data["opponent"]
        match_id = f"{player_name}_vs_{opponent}" if player_data["role"] == "P1" else f"{opponent}_vs_{player_name}"
        st.session_state.match_id = match_id

    st.success(f"🎮 Hello, {player_name}! You are **{player_data['role']}** in match **{st.session_state.match_id}**")

    # --- Period 1 ---
    st.subheader("🔁 Period 1: Choose your action")

    choice_options_p1 = ["A", "B"] if player_data["role"] == "P1" else ["X", "Y", "Z"]
    player_choice = st.radio("Your action:", choice_options_p1, key="period1_choice")
    if st.button("✅ Submit Choice"):
        ref.child(player_name).update({"choice1": player_choice})
        st.success(f"✅ Choice submitted: {player_choice}")

    # Wait for both choices
    updated = ref.child(player_name).get()
    opponent_data = ref.child(opponent).get()

    if updated["choice1"] and opponent_data["choice1"]:
        p1_action = updated["choice1"] if player_data["role"] == "P1" else opponent_data["choice1"]
        p2_action = updated["choice1"] if player_data["role"] == "P2" else opponent_data["choice1"]

        payoff_matrix = {
            ("A", "X"): (4, 3), ("A", "Y"): (0, 0), ("A", "Z"): (1, 4),
            ("B", "X"): (0, 0), ("B", "Y"): (2, 1), ("B", "Z"): (0, 0),
        }
        result = payoff_matrix.get((p1_action, p2_action), (0, 0))

        if player_data["role"] == "P1":
            ref.child(player_name).update({"result1": result[0]})
            ref.child(opponent).update({"result1": result[1]})
            st.session_state.result = result[0]
        else:
            st.session_state.result = result[1]

        st.success(f"🎯 Period 1 Result: P1 = {p1_action}, P2 = {p2_action} → Payoffs = {result}")

        if st.button("➡️ Proceed to Period 2"):
            st.session_state.period2 = True
            st.experimental_rerun()
    else:
        st.info("⌛ Waiting for both players to submit their choices for Period 1...")
