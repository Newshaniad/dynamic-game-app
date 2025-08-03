
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

# Game setup
game_description = '''
### Game Description
You will be matched with another player and play a 2-period dynamic game. 
In each period, you simultaneously choose an action. After both players submit,
the outcome and payoffs will be shown before moving to the next round.

**Payoff Matrix (Player 1, Player 2):**

|         | X       | Y       | Z       |
|---------|---------|---------|---------|
| **A**   | (4, 3)  | (0, 0)  | (1, 4)  |
| **B**   | (0, 0)  | (2, 1)  | (0, 0)  |
'''
st.markdown(game_description)

name = st.text_input("Enter your name to join the game:")
if not name:
    st.stop()

player_ref = db.reference(f"/players/{name}")
player_ref.set({
    "joined": True,
    "timestamp": time.time()
})
st.success(f"👋 Welcome, {name}!")

st.write("✅ Firebase is connected and you are registered.")

# For brevity, only initialization and player setup is shown in this template
# The rest of the game logic (pairing, rounds, results, cleanup) would go below
