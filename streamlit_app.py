import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import json
import random

# ------------------- Setup -------------------
st.set_page_config(page_title="🎲 Dynamic Game", layout="centered")

st.title("🎲 Multiplayer 2-Period Dynamic Game")

st.markdown("""
**Game Description**  
You will be matched with another player and play a 2-period dynamic game. In each period, you simultaneously choose an action.  
After both players submit, the outcome and payoffs will be shown before moving to the next round.

**Payoff Matrix (Player 1, Player 2):**

|     | X       | Y       | Z       |
|-----|---------|---------|---------|
| A   | (4, 3)  | (0, 0)  | (1, 4)  |
| B   | (0, 0)  | (2, 1)  | (0, 0)  |
"""
)

# ------------------- Firebase Init -------------------
cred = credentials.Certificate(json.loads(st.secrets["firebase_key"]))
try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app(cred, {
        'databaseURL': st.secrets["database_url"]
    })

db_root = db.reference("/dynamic_game")

# ------------------- User Login -------------------
name = st.text_input("Enter your name to join the game:")

if name:
    st.success(f"👋 Welcome, {name}!")

    # Check if already matched
    players_ref = db_root.child("players")
    if not players_ref.child(name).get():
        players_ref.child(name).set({"joined": True})

    players = list(players_ref.get().keys() or [])
    players = [p for p in players if p != name]

    match_id = None
    matched = False

    matches_ref = db_root.child("matches")
    current_matches = matches_ref.get() or {}

    # Try to find an existing match
    for m_id, m_data in current_matches.items():
        if "P2" not in m_data and m_data["P1"] != name:
            match_id = m_id
            matches_ref.child(m_id).update({"P2": name})
            matched = True
            break

    # If not matched yet, create a new match
    if not matched:
        match_id = f"{name}_vs_placeholder"
        matches_ref.child(match_id).set({"P1": name})

    st.info(f"✅ You are matched in: {match_id}")