
import streamlit as st
import random
import firebase_admin
from firebase_admin import credentials, db
import json
import time
from datetime import datetime, timedelta

# --- Firebase Setup ---
if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(st.secrets["firebase_key"]))
    firebase_admin.initialize_app(cred, {
        'databaseURL': st.secrets["database_url"]
    })

# --- Game Description ---
st.title("🎲 Multiplayer 2-Period Dynamic Game")

st.markdown("""
### 🧠 Game Instructions

You are matched with another player for **2 rounds**.
Each round, both players **choose at the same time**.

After round 1, you'll **see your combined result**, and then you’ll play round 2 with the same player.

Your choices will determine your **payoff**, based on the table below.
""")

st.markdown("""
### 📊 Payoff Matrix (Player 1, Player 2)

|           | **X**      | **Y**      | **Z**      |
|-----------|------------|------------|------------|
| **A**     | (4, 3)     | (0, 0)     | (1, 4)     |
| **B**     | (0, 0)     | (2, 1)     | (0, 0)     |
""")

# --- Session State ---
for key in ["name", "role", "pair_id", "round", "submitted", "choice"]:
    if key not in st.session_state:
        st.session_state[key] = "" if key not in ["round", "submitted"] else 1 if key == "round" else False

# --- Name Entry ---
name = st.text_input("Enter your name to join the game:")
if name and not st.session_state.name:
    st.session_state.name = name
    now = datetime.utcnow().isoformat()
    db.reference(f"players/{name}").set({"joined": True, "paired": False, "timestamp": now})

# --- Cleanup stale players (older than 5 min) ---
players = db.reference("players").get() or {}
now = datetime.utcnow()
for pname, pdata in players.items():
    ts = pdata.get("timestamp")
    if ts:
        try:
            joined_time = datetime.fromisoformat(ts)
            if now - joined_time > timedelta(minutes=5):
                db.reference(f"players/{pname}").delete()
        except Exception:
            db.reference(f"players/{pname}").delete()

# --- Refresh players after cleanup ---
players = db.reference("players").get() or {}
pairs = db.reference("pairs").get() or {}

# Check existing pair
found_pair = False
for pid, p in pairs.items():
    if name == p.get("P1"):
        st.session_state.pair_id = pid
        st.session_state.role = "P1"
        found_pair = True
    elif name == p.get("P2"):
        st.session_state.pair_id = pid
        st.session_state.role = "P2"
        found_pair = True

# Pair new players
if not found_pair:
    unpaired = [p for p in players if not players[p].get("paired") and p != name]
    if unpaired:
        partner = unpaired[0]
        pair_id = f"{partner}_vs_{name}"
        db.reference(f"pairs/{pair_id}").set({"P1": partner, "P2": name})
        db.reference(f"players/{partner}/paired").set(True)
        db.reference(f"players/{name}/paired").set(True)
        st.session_state.pair_id = pair_id
        st.session_state.role = "P2"

if not st.session_state.pair_id:
    st.info("⏳ Waiting for another player to join...")
    st.stop()

st.success(f"👋 Hello, {st.session_state.name}! You are **{st.session_state.role}** in match `{st.session_state.pair_id}`")

# --- Game Play ---
round_key = f"R{st.session_state.round}"
options = ["A", "B"] if st.session_state.role == "P1" else ["X", "Y", "Z"]
choice = st.radio(f"🎮 Choose your move for Round {st.session_state.round}:", options, index=0)
if st.button("✅ Submit Choice") and not st.session_state.submitted:
    db.reference(f"choices/{st.session_state.pair_id}/{round_key}/{st.session_state.role}").set(choice)
    st.session_state.choice = choice
    st.session_state.submitted = True
    st.experimental_rerun()

# --- Wait for both players ---
choices = db.reference(f"choices/{st.session_state.pair_id}/{round_key}").get()
if st.session_state.submitted and (not choices or "P1" not in choices or "P2" not in choices):
    st.warning("⏳ Waiting for your partner to choose...")
    st.stop()

# --- Show Results ---
if choices and "P1" in choices and "P2" in choices:
    a1, a2 = choices["P1"], choices["P2"]
    payoff_matrix = {
        "A": {"X": (4, 3), "Y": (0, 0), "Z": (1, 4)},
        "B": {"X": (0, 0), "Y": (2, 1), "Z": (0, 0)}
    }
    p1_score, p2_score = payoff_matrix[a1][a2]

    st.markdown(f"""
    ### 🧾 Round {st.session_state.round} Results:
    - Player 1 chose **{a1}**
    - Player 2 chose **{a2}**
    - 💰 Payoffs: Player 1 = **{p1_score}**, Player 2 = **{p2_score}**
    """)

    if st.session_state.round == 1:
        if st.button("🔁 Continue to Round 2"):
            st.session_state.round = 2
            st.session_state.submitted = False
            st.rerun()
    else:
        st.success("🏁 Game finished. Thank you!")
        # Cleanup
        db.reference(f"players/{st.session_state.name}").delete()
        db.reference(f"pairs/{st.session_state.pair_id}").delete()
        db.reference(f"choices/{st.session_state.pair_id}").delete()
        st.session_state.clear()
        time.sleep(1)
        st.experimental_rerun()
