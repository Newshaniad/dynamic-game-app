
import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import json
import time
import random

# Load Firebase credentials from Streamlit secrets
firebase_key = json.loads(st.secrets["firebase_key"])
database_url = st.secrets["database_url"]

# Initialize Firebase only once
cred = credentials.Certificate(firebase_key)
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {'databaseURL': database_url})

st.title("🎲 Multiplayer 2-Period Dynamic Game")

# Game description
st.markdown("""
### Game Description
You will be matched with another player and play a 2-period dynamic game. 
In each period, you simultaneously choose an action. After both players submit,
the outcome and payoffs will be shown before moving to the next round.

**Payoff Matrix (Player 1, Player 2):**

|         | X       | Y       | Z       |
|---------|---------|---------|---------|
| **A**   | (4, 3)  | (0, 0)  | (1, 4)  |
| **B**   | (0, 0)  | (2, 1)  | (0, 0)  |
""")

# Ask player to enter their name
name = st.text_input("Enter your name to join the game:")
if not name:
    st.stop()

# Register player in Firebase
player_ref = db.reference(f"/players/{name}")
player_ref.set({
    "joined": True,
    "timestamp": time.time()
})
st.success(f"👋 Welcome, {name}!")

# Get all registered players
players_ref = db.reference("/players")
all_players = players_ref.get() or {}

# Remove old or corrupted entries
valid_players = [p for p in all_players if isinstance(all_players[p], dict) and "joined" in all_players[p]]

# Sort and group players into pairs
valid_players.sort()
my_match = None

# Try to assign players into matches
match_ref = db.reference("/matches")
existing_matches = match_ref.get() or {}

# Check if already in a match
for match_name, match_data in existing_matches.items():
    if name in match_name.split("_vs_"):
        my_match = match_name
        break

# If not in a match yet, create one
if not my_match:
    unmatched = []
    for p in valid_players:
        already_matched = any(p in m.split("_vs_") for m in existing_matches)
        if not already_matched:
            unmatched.append(p)

    if len(unmatched) >= 2:
        p1, p2 = random.sample(unmatched[:2], 2)
        if random.random() < 0.5:
            player1, player2 = p1, p2
        else:
            player1, player2 = p2, p1
        match_name = f"{player1}_vs_{player2}"
        match_ref.child(match_name).set({
            "player1": player1,
            "player2": player2,
            "round": 1
        })
        if name in [player1, player2]:
            my_match = match_name

# Display role
if my_match:
    match_data = db.reference(f"/matches/{my_match}").get()
    if match_data:
        if name == match_data["player1"]:
            st.info(f"🎮 Hello, {name}! You are Player 1 in match `{my_match}`")
        elif name == match_data["player2"]:
            st.info(f"🎮 Hello, {name}! You are Player 2 in match `{my_match}`")
        else:
            st.warning("You are not assigned in any match yet. Please wait.")
    else:
        st.warning("Match data not found. Please wait.")
else:
    st.warning("⏳ Waiting for another player to join...")
