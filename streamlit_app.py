
import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import time
import random
import json

# Load Firebase credentials
cred = credentials.Certificate(json.loads(st.secrets["firebase_key"]))
try:
    firebase_admin.initialize_app(cred, {
        'databaseURL': st.secrets["database_url"]
    })
except ValueError:
    pass

st.title("🎲 Multiplayer 2-Period Dynamic Game")

st.markdown("""
### Game Description
You will be matched with another player and play a 2-period dynamic game.
In each period, you simultaneously choose an action. After both players submit, 
the outcome and payoffs will be shown before moving to the next round.

### Payoff Matrix (Player 1, Player 2):

|       | X       | Y       | Z       |
|-------|---------|---------|---------|
| **A** | (4, 3)  | (0, 0)  | (1, 4)  |
| **B** | (0, 0)  | (2, 1)  | (0, 0)  |
""")

# Player name input
player_name = st.text_input("Enter your name to join the game:")
if player_name:
    st.success(f"👋 Welcome, {player_name}!")
    player_ref = db.reference(f"players/{player_name}")
    player_data = player_ref.get()

    if not player_data:
        player_ref.set({"joined": True, "timestamp": time.time(), "period": 1, "submitted": False})

    all_players = db.reference("players").get() or {}
    unmatched = [p for p in all_players if "match" not in all_players[p] and p != player_name]

    match = None  # Define match before usage

    # Match players
    if not player_data.get("match"):
        if unmatched:
            partner = unmatched[0]
            match_id = f"{partner}_vs_{player_name}"
            db.reference(f"players/{partner}/match").set(match_id)
            player_ref.child("match").set(match_id)
            st.success(f"🎮 Hello, {player_name}! You are Player 2 in match {match_id}")
            match = match_id
        else:
            st.info("⏳ Waiting for another player to join...")
    else:
        match = player_data["match"]
        p1, p2 = match.split("_vs_")
        role = "Player 1" if player_name == p1 else "Player 2"
        st.success(f"🎮 Hello, {player_name}! You are {role} in match {match}")

    if match:
        period = player_data.get("period", 1)
        match_ref = db.reference(f"matches/{match}/period{period}")
        choice_key = "p1_choice" if player_name == match.split("_vs_")[0] else "p2_choice"
        other_key = "p2_choice" if choice_key == "p1_choice" else "p1_choice"

        options_p1 = ["A", "B"]
        options_p2 = ["X", "Y", "Z"]

        selected = st.radio(f"🔽 Choose your action for Period {period}:", options_p1 if choice_key == "p1_choice" else options_p2, key=period)

        if st.button("Submit", key=period):
            match_ref.child(choice_key).set(selected)
            player_ref.update({"submitted": True})
            st.success("✅ Choice submitted. Waiting for the other player...")

        game_data = match_ref.get() or {}

        if choice_key in game_data and other_key in game_data:
            a1, a2 = game_data.get("p1_choice"), game_data.get("p2_choice")
            payoff_matrix = {
                "A": {"X": (4, 3), "Y": (0, 0), "Z": (1, 4)},
                "B": {"X": (0, 0), "Y": (2, 1), "Z": (0, 0)}
            }
            p1_payoff, p2_payoff = payoff_matrix[a1][a2]
            st.markdown(f"### 🎯 Period {period} Outcome:
- Player 1 chose {a1}
- Player 2 chose {a2}
- Payoffs = ({p1_payoff}, {p2_payoff})")

            if period == 1:
                # Store payoffs and reset for next round
                db.reference(f"matches/{match}/results").set({"p1": p1_payoff, "p2": p2_payoff})
                db.reference(f"players/{match.split('_vs_')[0]}/period").set(2)
                db.reference(f"players/{match.split('_vs_')[1]}/period").set(2)
                db.reference(f"players/{match.split('_vs_')[0]}/submitted").set(False)
                db.reference(f"players/{match.split('_vs_')[1]}/submitted").set(False)
                st.info("➡️ Proceeding to Period 2. Please refresh the page.")
            else:
                result_ref = db.reference(f"matches/{match}/results").get()
                if result_ref:
                    total_p1 = result_ref["p1"] + p1_payoff
                    total_p2 = result_ref["p2"] + p2_payoff
                    st.markdown(f"### 🧾 Final Payoffs:
- Player 1: {total_p1}
- Player 2: {total_p2}")
