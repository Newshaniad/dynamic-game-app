import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import json
import random
import time

# Page config
st.set_page_config(page_title="Multiplayer 2-Period Dynamic Game", page_icon="🎲")

# Firebase setup
if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(st.secrets["firebase_key"]))
    firebase_admin.initialize_app(cred, {
        'databaseURL': st.secrets["database_url"]
    })

# Refs
players_ref = db.reference("players")

# UI title
st.title("🎲 Multiplayer 2-Period Dynamic Game")
st.markdown("Enter your name to join the game:")

name = st.text_input("Enter your name")
if st.button("Submit") and name:
    st.session_state.name = name
    st.session_state.role = None
    st.session_state.round = 1
    st.session_state.choices = {}

    # Register player
    player_ref = players_ref.child(name)
    player_ref.set({"joined": True, "choice1": "", "choice2": ""})
    st.success(f"👋 Welcome, {name}!")
    st.rerun()

# Proceed if name exists
if "name" in st.session_state:
    name = st.session_state.name
    player_list = list(players_ref.get().keys())

    # Wait for another player
    if len(player_list) < 2:
        st.info("Waiting for another player to join...")
    else:
        player_list.sort()
        idx = player_list.index(name)
        if idx % 2 == 0:
            role = "Player 1"
        else:
            role = "Player 2"
        st.session_state.role = role
        opponent = player_list[idx + 1] if role == "Player 1" else player_list[idx - 1]
        st.success(f"You are {role} matched with {opponent}")

        # Play round 1
        if st.session_state.round == 1:
            st.subheader("🔁 Round 1 Choices")
            choice = st.radio("Choose your action:", ["A", "B"] if role == "Player 1" else ["X", "Y", "Z"])
            if st.button("Submit Choice"):
                players_ref.child(name).update({"choice1": choice})
                st.session_state.choices["round1"] = choice
                st.rerun()

        # Display round 1 results if both chose
        if st.session_state.round == 1:
            data = players_ref.get()
            p1 = player_list[idx - idx % 2]  # Even index
            p2 = player_list[idx - idx % 2 + 1]  # Next
            c1 = data[p1].get("choice1", "")
            c2 = data[p2].get("choice1", "")
            if c1 and c2:
                st.subheader("📊 Round 1 Results")
                st.write(f"Player 1 ({p1}) chose: {c1}")
                st.write(f"Player 2 ({p2}) chose: {c2}")
                st.session_state.round = 2
                time.sleep(2)
                st.rerun()

        # Round 2
        if st.session_state.round == 2:
            st.subheader("🔁 Round 2 Choices")
            choice = st.radio("Choose your action:", ["A", "B"] if role == "Player 1" else ["X", "Y", "Z"])
            if st.button("Submit Round 2 Choice"):
                players_ref.child(name).update({"choice2": choice})
                st.session_state.choices["round2"] = choice
                st.rerun()

        # Display round 2 results
        if st.session_state.round == 2:
            data = players_ref.get()
            p1 = player_list[idx - idx % 2]
            p2 = player_list[idx - idx % 2 + 1]
            c1 = data[p1].get("choice2", "")
            c2 = data[p2].get("choice2", "")
            if c1 and c2:
                st.subheader("📊 Round 2 Results")
                st.write(f"Player 1 ({p1}) chose: {c1}")
                st.write(f"Player 2 ({p2}) chose: {c2}")
                st.balloons()
                st.markdown("### 🎉 Game Over. Thank you for playing!")
