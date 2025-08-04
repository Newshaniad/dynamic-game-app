
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

# ✅ Once matched, proceed to Period 1 gameplay
if already_matched or "role" in locals():
    match_id = match_id if already_matched else f"{pair[0]}_vs_{pair[1]}"
    role = role if already_matched else ("Player 1" if pair[0] == name else "Player 2")
    game_ref = db.reference(f"games/{match_id}/period1")

    # Display available choices
    st.subheader("🎮 Period 1: Make Your Choice")

    existing_action = game_ref.child(role).get()
if existing_action:
    st.info(f"✅ You already submitted: {existing_action['action']}")
else:
    if role == "Player 1":
        choice = st.radio("Choose your action:", ["A", "B"])
    else:
        choice = st.radio("Choose your action:", ["X", "Y", "Z"])

    if st.button("Submit Choice"):
        game_ref.child(role).set({
            "action": choice,
            "timestamp": time.time()
        })
        st.success("✅ Your choice has been submitted!")


    # Wait for both players to submit
with st.spinner("⏳ Waiting for the other player to submit their action..."):
    max_wait = 10  # seconds
    for _ in range(max_wait):
        submitted = game_ref.get()
        if submitted and "Player 1" in submitted and "Player 2" in submitted:
            action1 = submitted["Player 1"]["action"]
            action2 = submitted["Player 2"]["action"]

            payoff_matrix = {
                "A": {"X": (4, 3), "Y": (0, 0), "Z": (1, 4)},
                "B": {"X": (0, 0), "Y": (2, 1), "Z": (0, 0)}
            }
            payoff = payoff_matrix[action1][action2]

            st.success(f"🎯 Period 1 Outcome: P1 = {action1}, P2 = {action2} → Payoffs = {payoff}")

            if st.button("▶️ Continue to Period 2"):
                st.session_state["go_to_period2"] = True
                st.rerun()
            break
        time.sleep(1)
    else:
        st.warning("⌛ The other player hasn't submitted yet. Please wait a bit more and refresh.")


# ✅ Period 2 logic (if "Continue to Period 2" was clicked or auto-triggered)
if st.session_state.get("go_to_period2", False):
    st.subheader("🔁 Period 2: Make Your Choice (Knowing Period 1 Outcome)")

    match_id = match_id if already_matched else f"{pair[0]}_vs_{pair[1]}"
    period1_data = db.reference(f"games/{match_id}/period1").get()
    if period1_data and "Player 1" in period1_data and "Player 2" in period1_data:
        action1 = period1_data["Player 1"]["action"]
        action2 = period1_data["Player 2"]["action"]
        payoff_matrix = {
            "A": {"X": (4, 3), "Y": (0, 0), "Z": (1, 4)},
            "B": {"X": (0, 0), "Y": (2, 1), "Z": (0, 0)}
        }
        period1_payoff = payoff_matrix[action1][action2]
        st.info(f"📢 In Period 1: P1 = {action1}, P2 = {action2} → Payoffs = {period1_payoff}")

    # Let players choose again
    game_ref2 = db.reference(f"games/{match_id}/period2")

    existing_action2 = game_ref2.child(role).get()
if existing_action2:
    st.info(f"✅ You already submitted: {existing_action2['action']}")
else:
    if role == "Player 1":
        choice2 = st.radio("Choose your Period 2 action:", ["A", "B"], key="p1_period2")
    else:
        choice2 = st.radio("Choose your Period 2 action:", ["X", "Y", "Z"], key="p2_period2")

    if st.button("Submit Period 2 Choice"):
        game_ref2.child(role).set({
            "action": choice2,
            "timestamp": time.time()
        })
        st.success("✅ Your Period 2 choice has been submitted!")

    # Wait for both submissions
    # Period 2: Wait for both players to submit
with st.spinner("⏳ Waiting for the other player to submit their action in Period 2..."):
    max_wait = 10  # seconds
    for _ in range(max_wait):
        submitted2 = game_ref2.get()
        if submitted2 and "Player 1" in submitted2 and "Player 2" in submitted2:
            action1_2 = submitted2["Player 1"]["action"]
            action2_2 = submitted2["Player 2"]["action"]

            payoff_matrix = {
                "A": {"X": (4, 3), "Y": (0, 0), "Z": (1, 4)},
                "B": {"X": (0, 0), "Y": (2, 1), "Z": (0, 0)}
            }
            payoff2 = payoff_matrix[action1_2][action2_2]

            st.success(f"🎯 Period 2 Outcome: P1 = {action1_2}, P2 = {action2_2} → Payoffs = {payoff2}")
            st.balloons()
            st.markdown("✅ **Game Complete!** Thanks for playing.")
            break
        time.sleep(1)
    else:
        st.warning("⌛ The other player hasn't submitted their Period 2 action yet. Please wait and refresh.")
        st.balloons()

        st.markdown("✅ **Game Complete!** Thanks for playing.")

import matplotlib.pyplot as plt
import pandas as pd

st.header("📊 Game Summary")

# Fetch all players and all matches
players = db.reference("players").get() or {}
matches = db.reference("matches").get() or {}
all_games = db.reference("games").get() or {}

# Determine how many players are in completed matches
total_players = len(players)
completed_players = 0

for match_id, game_data in all_games.items():
    if "period1" in game_data and "period2" in game_data:
        if "Player 1" in game_data["period1"] and "Player 2" in game_data["period1"] \
        and "Player 1" in game_data["period2"] and "Player 2" in game_data["period2"]:
            completed_players += 2  # Both players finished

# Show graph ONLY if all players completed both periods
if completed_players >= total_players:
    st.success("✅ All players completed both rounds. Showing results...")

    p1_choices_r1, p2_choices_r1 = [], []
    p1_choices_r2, p2_choices_r2 = [], []

    for match in all_games.values():
        # Round 1
        if "period1" in match:
            p1 = match["period1"].get("Player 1", {}).get("action")
            p2 = match["period1"].get("Player 2", {}).get("action")
            if p1: p1_choices_r1.append(p1)
            if p2: p2_choices_r1.append(p2)
        # Round 2
        if "period2" in match:
            p1 = match["period2"].get("Player 1", {}).get("action")
            p2 = match["period2"].get("Player 2", {}).get("action")
            if p1: p1_choices_r2.append(p1)
            if p2: p2_choices_r2.append(p2)

    def plot_percentage_bar(choices, labels, title):
        total = len(choices)
        counts = pd.Series(choices).value_counts(normalize=True).reindex(labels, fill_value=0) * 100
        fig, ax = plt.subplots()
        counts.plot(kind='bar', ax=ax)
        ax.set_title(title)
        ax.set_ylabel("Percentage (%)")
        ax.set_xlabel("Choice")
        st.pyplot(fig)

    st.subheader("Round 1")
    plot_percentage_bar(p1_choices_r1, ["A", "B"], "Player 1 Choices (Round 1)")
    plot_percentage_bar(p2_choices_r1, ["X", "Y", "Z"], "Player 2 Choices (Round 1)")

    st.subheader("Round 2")
    plot_percentage_bar(p1_choices_r2, ["A", "B"], "Player 1 Choices (Round 2)")
    plot_percentage_bar(p2_choices_r2, ["X", "Y", "Z"], "Player 2 Choices (Round 2)")
else:
    st.info(f"⏳ Waiting for all participants to finish... ({completed_players}/{total_players} done)")
