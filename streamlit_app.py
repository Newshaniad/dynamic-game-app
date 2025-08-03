
import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import time

# ----------------------------
# Firebase Configuration
# ----------------------------
cred = credentials.Certificate({
  "type": "service_account",
  "project_id": "dynamic-game-79aa7",
  "private_key_id": st.secrets["firebase_key"]["private_key_id"],
  "private_key": st.secrets["firebase_key"]["private_key"].replace("\n", "\n"),
  "client_email": st.secrets["firebase_key"]["client_email"],
  "client_id": st.secrets["firebase_key"]["client_id"],
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": st.secrets["firebase_key"]["client_x509_cert_url"]
})

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': st.secrets["database_url"]
    })

# ----------------------------
# Game Setup
# ----------------------------

st.title("🎲 2-Period Dynamic Game")
st.markdown("""
### Game Description
You will be matched with another player and play a 2-period dynamic game.
In each period, you simultaneously choose an action.
After both players submit, the outcome and payoffs will be shown before moving to the next round.

#### Payoff Matrix (Player 1, Player 2):

|     | X     | Y     | Z     |
|-----|-------|-------|-------|
| A   | (4,3) | (0,0) | (1,4) |
| B   | (0,0) | (2,1) | (0,0) |
""")

name = st.text_input("Enter your name to join the game:")
if name:
    st.success(f"👋 Welcome, {name}!")

    players_ref = db.reference("players")
    current_players = players_ref.get() or {}

    if name not in current_players:
        players_ref.child(name).set({
            "joined": True,
            "opponent": None,
            "role": None,
            "choice1": None,
            "choice2": None,
            "ready_for_round2": False
        })
        st.success("✅ Firebase is connected and you are registered.")

    player_data = players_ref.child(name).get()
    opponent_name = player_data.get("opponent")

    # Matching Logic (DO NOT TOUCH)
    if not opponent_name:
        for other_name, data in current_players.items():
            if other_name != name and not data.get("opponent"):
                players_ref.child(name).update({"opponent": other_name, "role": "P1"})
                players_ref.child(other_name).update({"opponent": name, "role": "P2"})
                opponent_name = other_name
                break

    # Refresh player data
    player_data = players_ref.child(name).get()
    opponent_name = player_data.get("opponent")
    role = player_data.get("role")

    if not opponent_name:
        st.warning("⏳ Waiting for another player to join...")
        st.stop()
    else:
        st.success(f"🎮 Hello, {name}! You are Player {1 if role == 'P1' else 2} in match {name}_vs_{opponent_name}")

        # ROUND 1
        st.header("🔁 Round 1")

        # Define available choices
        choices_p1 = ["A", "B"]
        choices_p2 = ["X", "Y", "Z"]

        # Allow choices only if not yet submitted
        if player_data["choice1"] is None:
            if role == "P1":
                action = st.radio("Choose your action (Player 1):", choices_p1)
            else:
                action = st.radio("Choose your action (Player 2):", choices_p2)

            if st.button("Submit Round 1 Choice"):
                players_ref.child(name).update({"choice1": action})
                st.success(f"✅ You selected: {action}")
                st.experimental_rerun()
        else:
            st.info(f"✅ Waiting for {opponent_name} to submit their choice...")

        # Check if both players submitted
        opponent_data = players_ref.child(opponent_name).get()
        if player_data["choice1"] and opponent_data and opponent_data.get("choice1"):
            # Show results
            p1_action = player_data["choice1"] if role == "P1" else opponent_data["choice1"]
            p2_action = player_data["choice1"] if role == "P2" else opponent_data["choice1"]

            payoff_matrix = {
                ("A", "X"): (4, 3),
                ("A", "Y"): (0, 0),
                ("A", "Z"): (1, 4),
                ("B", "X"): (0, 0),
                ("B", "Y"): (2, 1),
                ("B", "Z"): (0, 0)
            }

            payoffs = payoff_matrix.get((p1_action, p2_action), (0, 0))

            st.success(f"🎯 Period 1 Outcome: P1 = {p1_action}, P2 = {p2_action} → Payoffs = {payoffs}")
            st.markdown("➡️ Round 2 coming soon...")
