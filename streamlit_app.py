
import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import random
import time
import json
from datetime import datetime

# Game setup
GAME_DESCRIPTION = '''
### 🎲 2-Period Dynamic Game
Players are randomly matched and play a 2-stage game.

#### Payoff Matrix (Player 1, Player 2)
|       | X       | Y       | Z       |
|-------|---------|---------|---------|
| **A** | (4, 3)  | (0, 0)  | (1, 4)  |
| **B** | (0, 0)  | (2, 1)  | (0, 0)  |
'''

payoffs = {
    "A": {"X": (4, 3), "Y": (0, 0), "Z": (1, 4)},
    "B": {"X": (0, 0), "Y": (2, 1), "Z": (0, 0)},
}

# Firebase setup using secrets
cred = credentials.Certificate(json.loads(st.secrets["firebase_key"]))
firebase_admin.initialize_app(cred, {
    'databaseURL': st.secrets["database_url"]
})
ref = db.reference("/dynamic_game")

# UI
st.title("🎮 Multiplayer 2-Stage Game")
st.markdown(GAME_DESCRIPTION)

player_name = st.text_input("Enter your name to join the game:")
if player_name:
    player_ref = ref.child("players").child(player_name)
    player_data = player_ref.get()

    if not player_data:
        player_ref.set({
            "joined": True,
            "timestamp": time.time(),
            "choice1": None,
            "choice2": None,
            "role": None,
            "partner": None
        })
        st.success(f"👋 Welcome, {player_name}!")

    # Matchmaking
    players = ref.child("players").get()
    waiting = [p for p, pdata in players.items() if isinstance(pdata, dict) and pdata.get("partner") is None]

    if len(waiting) >= 2:
        random.shuffle(waiting)
        for i in range(0, len(waiting) - 1, 2):
            p1, p2 = waiting[i], waiting[i+1]
            ref.child("players").child(p1).update({"partner": p2, "role": "P1"})
            ref.child("players").child(p2).update({"partner": p1, "role": "P2"})
            match_id = f"{p1}_vs_{p2}"
            ref.child("matches").child(match_id).set({
                "p1": p1,
                "p2": p2,
                "round1": {},
                "round2": {}
            })

    # Check if matched
    role = ref.child("players").child(player_name).child("role").get()
    partner = ref.child("players").child(player_name).child("partner").get()
    if role and partner:
        st.info(f"🎮 You are {role} matched with {partner}")

        match_id = f"{player_name}_vs_{partner}" if role == "P1" else f"{partner}_vs_{player_name}"
        match_ref = ref.child("matches").child(match_id)

        # Round 1
        choice1 = ref.child("players").child(player_name).child("choice1").get()
        if not choice1:
            choice = st.selectbox("🔁 Round 1: Choose your action", ["A", "B"] if role == "P1" else ["X", "Y", "Z"])
            if st.button("Submit Round 1 Choice"):
                ref.child("players").child(player_name).update({"choice1": choice})
                match_ref.child("round1").child(role).set(choice)
                st.success("✅ Choice submitted. Waiting for partner...")

        round1 = match_ref.child("round1").get()
        if round1 and "P1" in round1 and "P2" in round1:
            c1 = round1["P1"]
            c2 = round1["P2"]
            payoff1, payoff2 = payoffs[c1][c2]
            st.success(f"🎯 Round 1: {c1} vs {c2} → Payoffs = ({payoff1}, {payoff2})")

            # Round 2
            choice2 = ref.child("players").child(player_name).child("choice2").get()
            if not choice2:
                choice = st.selectbox("🔁 Round 2: Choose your action", ["A", "B"] if role == "P1" else ["X", "Y", "Z"])
                if st.button("Submit Round 2 Choice"):
                    ref.child("players").child(player_name).update({"choice2": choice})
                    match_ref.child("round2").child(role).set(choice)
                    st.success("✅ Round 2 choice submitted. Waiting for partner...")

            round2 = match_ref.child("round2").get()
            if round2 and "P1" in round2 and "P2" in round2:
                c1 = round2["P1"]
                c2 = round2["P2"]
                payoff1, payoff2 = payoffs[c1][c2]
                st.success(f"🎯 Round 2: {c1} vs {c2} → Payoffs = ({payoff1}, {payoff2})")

                # Clean up after game
                ref.child("players").child(player_name).delete()
                st.info("✅ Game complete! Thank you for playing.")
