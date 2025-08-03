
import streamlit as st
import random
import firebase_admin
from firebase_admin import credentials, db
import json
import time

# --- Firebase Setup ---
cred = credentials.Certificate(json.loads(st.secrets["firebase_key"]))
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': st.secrets["database_url"]
    })

# --- UI: Game Description and Table ---
st.title("🎲 Multiplayer 2-Period Dynamic Game")

st.markdown("""
### 🧠 Game Instructions

You are matched with another player for **2 rounds**.
Each round, both players **choose simultaneously** from the options below.

After round 1, you'll **see your combined result**, and then you’ll play round 2 with the same player.

Your choices will determine your **payoff**, based on the table below.
""")

st.markdown("""
### 📊 Payoff Matrix (Player 1, Player 2)

|           | **X**      | **Y**      | **Z**      |
|-----------|------------|------------|------------|
| **A**     | (4, 3)     | (0, 0)     | (1, 4)     |
| **B**     | (0, 0)     | (2, 1)     | (0, 0)     |

- Player 1 chooses: **A** or **B**  
- Player 2 chooses: **X**, **Y**, or **Z**
""")

# --- Session State Initialization ---
for key in ["name", "role", "pair_id", "round", "choice", "game_over"]:
    if key not in st.session_state:
        st.session_state[key] = "" if key != "round" else 1

# --- Name Entry ---
name = st.text_input("Enter your name to join the game:")
if name and not st.session_state.name:
    st.session_state.name = name
    db.reference(f"players/{name}").set({"joined": True, "paired": False})

# --- Player Pairing ---
players = db.reference("players").get() or {}
paired = db.reference("pairs").get() or {}

# Check if already paired
found_pair = False
for pid, pair in paired.items():
    if name == pair.get("P1"):
        st.session_state.pair_id = pid
        st.session_state.role = "P1"
        found_pair = True
    elif name == pair.get("P2"):
        st.session_state.pair_id = pid
        st.session_state.role = "P2"
        found_pair = True

# Try new pairing if not already paired
if not found_pair:
    unpaired = [p for p in players if not players[p].get("paired")]
    if len(unpaired) >= 2:
        p1, p2 = random.sample(unpaired, 2)
        pair_id = f"{p1}_vs_{p2}"
        db.reference(f"pairs/{pair_id}").set({"P1": p1, "P2": p2})
        db.reference(f"players/{p1}/paired").set(True)
        db.reference(f"players/{p2}/paired").set(True)
        if name == p1:
            st.session_state.pair_id = pair_id
            st.session_state.role = "P1"
        elif name == p2:
            st.session_state.pair_id = pair_id
            st.session_state.role = "P2"

if not st.session_state.pair_id:
    st.info("⏳ Waiting to be paired with another player...")
    st.stop()

st.success(f"👋 Welcome, {st.session_state.name}! You are **{st.session_state.role}** in match `{st.session_state.pair_id}`")

# --- Game Play ---
round_key = f"R{st.session_state.round}"
options = ["A", "B"] if st.session_state.role == "P1" else ["X", "Y", "Z"]
choice = st.radio(f"🎮 Choose your action (Round {st.session_state.round}):", options)
if st.button("Submit Choice"):
    db.reference(f"choices/{st.session_state.pair_id}/{round_key}/{st.session_state.role}").set(choice)
    st.session_state.choice = choice

# --- Show Results if both players submitted ---
choices = db.reference(f"choices/{st.session_state.pair_id}/{round_key}").get()
payoff_matrix = {
    "A": {"X": (4, 3), "Y": (0, 0), "Z": (1, 4)},
    "B": {"X": (0, 0), "Y": (2, 1), "Z": (0, 0)}
}

if choices and "P1" in choices and "P2" in choices:
    a1, a2 = choices["P1"], choices["P2"]
    p1_payoff, p2_payoff = payoff_matrix[a1][a2]
    st.markdown(f"""
    ### 🎯 Round {st.session_state.round} Results:
    - Player 1 chose: **{a1}**
    - Player 2 chose: **{a2}**
    - 💰 Payoffs → P1: **{p1_payoff}**, P2: **{p2_payoff}**
    """)

    if st.session_state.round == 1:
        if st.button("🔁 Play Round 2"):
            st.session_state.round = 2
            st.rerun()
    else:
        st.success("✅ Game over! Thank you for playing.")
        # Clean up
        db.reference(f"players/{st.session_state.name}").delete()
        db.reference(f"choices/{st.session_state.pair_id}").delete()
        db.reference(f"pairs/{st.session_state.pair_id}").delete()
        st.session_state.clear()
        time.sleep(1)
        st.experimental_rerun()
