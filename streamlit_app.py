# streamlit_app.py
import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import json
import random

# Initialize Firebase using Streamlit Secrets
if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(st.secrets["firebase_key"]))
    firebase_admin.initialize_app(cred, {
        'databaseURL': st.secrets["databaseURL"]
    })

st.title("🎲 Multiplayer 2-Period Dynamic Game")

# Enter name
name = st.text_input("Enter your name to join the game:")
submit = st.button("Submit")

if submit and name:
    players_ref = db.reference("players")
    current_players = players_ref.get() or {}

    if name in current_players:
        st.warning("Name already used. Choose another.")
        st.stop()

    players_ref.child(name).set({
        "round": 1,
        "choice1": None,
        "choice2": None,
        "paired": False
    })
    st.success(f"👋 Welcome, {name}!")
    st.experimental_rerun()

current_players = db.reference("players").get() or {}
unpaired = [p for p, v in current_players.items() if not v["paired"]]

if name in current_players and not current_players[name]["paired"]:
    if len(unpaired) >= 2:
        others = [p for p in unpaired if p != name]
        if others:
            partner = random.choice(others)
            db.reference("players").child(name).update({"paired": partner})
            db.reference("players").child(partner).update({"paired": name})
            st.experimental_rerun()
    else:
        st.info("⌛ Waiting for another player to join...")

if name in current_players and current_players[name]["paired"]:
    partner = current_players[name]["paired"]
    st.info(f"You are matched with {partner}!")

    round_number = current_players[name]["round"]

    st.header(f"Round {round_number}")
    if round_number == 1:
        choice = st.radio("Choose action for Round 1", ["A", "B"])
        if st.button("Play Round 1"):
            db.reference("players").child(name).update({"choice1": choice})
            st.success("Waiting for your partner's move...")
    elif round_number == 2:
        choice = st.radio("Choose action for Round 2", ["A", "B"])
        if st.button("Play Round 2"):
            db.reference("players").child(name).update({"choice2": choice})
            st.success("Waiting for your partner's move...")

    you = db.reference("players").child(name).get()
    partner_data = db.reference("players").child(partner).get()

    if you and partner_data:
        if round_number == 1 and you["choice1"] and partner_data["choice1"]:
            st.success(f"✅ Round 1 Done! You: {you['choice1']}, {partner}: {partner_data['choice1']}")
            db.reference("players").child(name).update({"round": 2})
            st.experimental_rerun()
        elif round_number == 2 and you["choice2"] and partner_data["choice2"]:
            st.success(f"🎉 Game Over!\nRound 1: {you['choice1']} vs {partner_data['choice1']}\n"
                       f"Round 2: {you['choice2']} vs {partner_data['choice2']}")
