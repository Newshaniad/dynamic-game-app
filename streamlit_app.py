import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import json
import time
import random
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import base64

st.set_page_config(page_title="🎲 2-Period Dynamic Game")

st.title("🎲 Multiplayer 2-Period Dynamic Game")

# Game description
st.markdown("""
Game Description  
You will be matched with another player and play a 2-period dynamic game. In each period, you simultaneously choose an action.  
After both players submit, the outcome and payoffs will be shown before moving to the next round.

Payoff Matrix (Player 1, Player 2):

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

# Initialize variables to avoid undefined errors
already_matched = False
match_id = None
role = None
pair = None

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
        # Check if all expected players have finished playing
        expected_players_ref = db.reference("expected_players")
        expected_players = expected_players_ref.get() or 0
        all_games = db.reference("games").get() or {}
        
        # Count completed players
        completed_players = 0
        for match_id, game_data in all_games.items():
            if "period1" in game_data and "period2" in game_data:
                if "Player 1" in game_data["period1"] and "Player 2" in game_data["period1"] \
                and "Player 1" in game_data["period2"] and "Player 2" in game_data["period2"]:
                    completed_players += 2
        
        # If all expected players have completed, no more matches allowed
        if expected_players >= 0 and completed_players >= expected_players:
            st.info("🎯 All games have been completed! No more matches are available.")
            st.info("📊 Check the Game Summary section below to see the results.")
        else:
            # Get fresh data to avoid race conditions
            players_data = db.reference("players").get() or {}
            match_data = db.reference("matches").get() or {}
            
            unmatched = [p for p in players_data.keys()
                         if not any(p in m.get("players", []) for m in match_data.values())
                         and p != name]

            if unmatched:
                partner = unmatched[0]
                pair = sorted([name, partner])
                match_id = f"{pair[0]}vs{pair[1]}"
                
                # Double-check that the match doesn't already exist (race condition protection)
                existing_match = match_ref.child(match_id).get()
                if not existing_match:
                    match_ref.child(match_id).set({"players": pair})
                    role = "Player 1" if pair[0] == name else "Player 2"
                    st.success(f"🎮 Hello, {name}! You are {role} in match {match_id}")
                else:
                    # Match was created by another player, check our role
                    role = "Player 1" if existing_match["players"][0] == name else "Player 2"
                    st.success(f"🎮 Hello, {name}! You are {role} in match {match_id}")
                    already_matched = True
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
                                already_matched = True
                                st.rerun()
                        time.sleep(2)

    # ✅ Once matched, proceed to Period 1 gameplay
    if already_matched or role is not None:
        match_id = match_id if already_matched else f"{pair[0]}vs{pair[1]}"
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

                    if st.button("▶ Continue to Period 2"):
                        st.session_state["go_to_period2"] = True
                        st.rerun()
                    break
                time.sleep(1)
            else:
                st.warning("⌛ The other player hasn't submitted yet. Please wait a bit more and refresh.")

        # ✅ Period 2 logic (if "Continue to Period 2" was clicked or auto-triggered)
        if st.session_state.get("go_to_period2", False):
            st.subheader("🔁 Period 2: Make Your Choice (Knowing Period 1 Outcome)")

            # Ensure match_id is properly set
            if not match_id and pair:
                match_id = f"{pair[0]}vs{pair[1]}"
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
                        st.markdown("✅ Game Complete! Thanks for playing.")
                        
                        # Initialize variables for PDF functionality  
                        st.session_state["game_complete"] = True
                        st.session_state["match_id"] = match_id
                        st.session_state["action1"] = action1
                        st.session_state["action2"] = action2
                        st.session_state["period1_payoff"] = period1_payoff
                        st.session_state["action1_2"] = action1_2
                        st.session_state["action2_2"] = action2_2
                        st.session_state["payoff2"] = payoff2
                        st.session_state["pair"] = pair
                        
                        # Check if all players have finished and trigger rerun for results display
                        expected_players = db.reference("expected_players").get() or 0
                        all_games_check = db.reference("games").get() or {}
                        completed_check = 0
                        for mid, gdata in all_games_check.items():
                            if "period1" in gdata and "period2" in gdata:
                                if "Player 1" in gdata["period1"] and "Player 2" in gdata["period1"] \
                                and "Player 1" in gdata["period2"] and "Player 2" in gdata["period2"]:
                                    completed_check += 2
                        
                        if expected_players > 0 and completed_check >= expected_players:
                            st.success("🎉 All players have finished! Results are now available below.")
                            st.info("📊 Scroll down to see the complete game results and charts.")
                            # Set a flag instead of immediate rerun to avoid infinite loops
                            st.session_state["all_games_complete"] = True
                        break
                    time.sleep(1)
                else:
                    st.warning("⌛ The other player hasn't submitted their Period 2 action yet. Please wait and refresh.")
                    st.balloons()
                    st.markdown("✅ Game Complete! Thanks for playing.")
                    
                    # Initialize variables for PDF functionality
                    st.session_state["game_complete"] = True
                    st.session_state["match_id"] = match_id
                    st.session_state["action1"] = action1
                    st.session_state["action2"] = action2
                    st.session_state["period1_payoff"] = period1_payoff
                    st.session_state["action1_2"] = action1_2
                    st.session_state["action2_2"] = action2_2
                    st.session_state["payoff2"] = payoff2
                    st.session_state["pair"] = pair

import matplotlib.pyplot as plt
import pandas as pd

# Public Game Summary (visible to everyone)
st.header("📊 Game Summary")

# Get expected number of players from Firebase (set by admin)
expected_players_ref = db.reference("expected_players")
expected_players = expected_players_ref.get() or 0

# Fetch all players and all matches
players = db.reference("players").get() or {}
matches = db.reference("matches").get() or {}
all_games = db.reference("games").get() or {}

# Determine how many players are in completed matches
completed_players = 0

for match_id, game_data in all_games.items():
    if "period1" in game_data and "period2" in game_data:
        if "Player 1" in game_data["period1"] and "Player 2" in game_data["period1"] \
        and "Player 1" in game_data["period2"] and "Player 2" in game_data["period2"]:
            completed_players += 2  # Both players finished

# Auto-refresh for users who haven't seen results yet (but not if they just completed)
if expected_players > 0 and completed_players >= expected_players and not st.session_state.get("all_games_complete", False):
    time.sleep(3)
    st.rerun()

# Show graph ONLY if all expected players completed both periods
if expected_players > 0 and completed_players >= expected_players:
    st.success(f"✅ All {expected_players} players completed both rounds. Showing results...")

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
        if len(choices) > 0:
            counts = pd.Series(choices).value_counts(normalize=True).reindex(labels, fill_value=0) * 100
            fig, ax = plt.subplots()
            counts.plot(kind='bar', ax=ax)
            ax.set_title(title)
            ax.set_ylabel("Percentage (%)")
            ax.set_xlabel("Choice")
            st.pyplot(fig)
        else:
            st.write(f"No data available for {title}")

    st.subheader("Round 1")
    plot_percentage_bar(p1_choices_r1, ["A", "B"], "Player 1 Choices (Round 1)")
    plot_percentage_bar(p2_choices_r1, ["X", "Y", "Z"], "Player 2 Choices (Round 1)")

    st.subheader("Round 2")
    plot_percentage_bar(p1_choices_r2, ["A", "B"], "Player 1 Choices (Round 2)")
    plot_percentage_bar(p2_choices_r2, ["X", "Y", "Z"], "Player 2 Choices (Round 2)")
elif expected_players > 0:
    st.info(f"⏳ Waiting for all participants to finish... ({completed_players}/{expected_players} players completed)")
else:
    st.info("📈 Admin needs to set the expected number of players to display results.")

# Refresh Results Button (available to all users)
st.subheader("🔄 Refresh Results")
if st.button("🔄 Check for Updated Results"):
    # Re-fetch data from Firebase
    fresh_expected_players = db.reference("expected_players").get() or 0
    fresh_all_games = db.reference("games").get() or {}
    
    # Recount completed players
    fresh_completed_players = 0
    for match_id, game_data in fresh_all_games.items():
        if "period1" in game_data and "period2" in game_data:
            if "Player 1" in game_data["period1"] and "Player 2" in game_data["period1"] \
            and "Player 1" in game_data["period2"] and "Player 2" in game_data["period2"]:
                fresh_completed_players += 2
    
    # Check if all players have finished
    if fresh_expected_players > 0 and fresh_completed_players >= fresh_expected_players:
        st.success(f"✅ All {fresh_expected_players} players have completed! Refreshing results...")
        st.rerun()  # Refresh the page to show updated results
    elif fresh_expected_players > 0:
        st.info(f"⏳ Still waiting... ({fresh_completed_players}/{fresh_expected_players} players completed)")
    else:
        st.warning("⚠ Admin needs to set the expected number of players first.")



# Function to create comprehensive PDF with all game data and graphs
def create_comprehensive_pdf():
    import matplotlib.pyplot as plt
    import tempfile
    import os
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=colors.darkblue,
        spaceAfter=30
    )
    story.append(Paragraph("🎲 Dynamic Game Complete Results", title_style))
    story.append(Spacer(1, 20))
    
    # Get all game data from Firebase
    all_games = db.reference("games").get() or {}
    expected_players = db.reference("expected_players").get() or 0
    
    # Summary section
    story.append(Paragraph(f"<b>Game Summary</b>", styles['Heading2']))
    story.append(Paragraph(f"Expected Players: {expected_players}", styles['Normal']))
    story.append(Paragraph(f"Total Matches: {len(all_games)}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Individual match results
    story.append(Paragraph("<b>Individual Match Results</b>", styles['Heading2']))
    
    # Create table data for all matches
    table_data = [["Match ID", "Period 1", "Period 1 Payoffs", "Period 2", "Period 2 Payoffs"]]
    
    for match_id, game_data in all_games.items():
        if "period1" in game_data and "period2" in game_data:
            # Period 1
            p1_action1 = game_data["period1"].get("Player 1", {}).get("action", "N/A")
            p2_action1 = game_data["period1"].get("Player 2", {}).get("action", "N/A")
            payoff_matrix = {
                "A": {"X": (4, 3), "Y": (0, 0), "Z": (1, 4)},
                "B": {"X": (0, 0), "Y": (2, 1), "Z": (0, 0)}
            }
            if p1_action1 != "N/A" and p2_action1 != "N/A":
                payoff1 = payoff_matrix[p1_action1][p2_action1]
            else:
                payoff1 = "N/A"
            
            # Period 2
            p1_action2 = game_data["period2"].get("Player 1", {}).get("action", "N/A")
            p2_action2 = game_data["period2"].get("Player 2", {}).get("action", "N/A")
            if p1_action2 != "N/A" and p2_action2 != "N/A":
                payoff2 = payoff_matrix[p1_action2][p2_action2]
            else:
                payoff2 = "N/A"
            
            table_data.append([
                match_id,
                f"P1:{p1_action1}, P2:{p2_action1}",
                str(payoff1),
                f"P1:{p1_action2}, P2:{p2_action2}",
                str(payoff2)
            ])
    
    # Create and style the table
    table = Table(table_data, colWidths=[1.5*inch, 1.5*inch, 1*inch, 1.5*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(table)
    story.append(Spacer(1, 30))
    
    # Generate charts and add to PDF
    story.append(Paragraph("<b>Statistical Analysis</b>", styles['Heading2']))
    
    # Collect choice data
    p1_choices_r1, p2_choices_r1 = [], []
    p1_choices_r2, p2_choices_r2 = [], []
    
    for match in all_games.values():
        if "period1" in match:
            p1 = match["period1"].get("Player 1", {}).get("action")
            p2 = match["period1"].get("Player 2", {}).get("action")
            if p1: p1_choices_r1.append(p1)
            if p2: p2_choices_r1.append(p2)
        if "period2" in match:
            p1 = match["period2"].get("Player 1", {}).get("action")
            p2 = match["period2"].get("Player 2", {}).get("action")
            if p1: p1_choices_r2.append(p1)
            if p2: p2_choices_r2.append(p2)
    
    # Create temporary directory for chart images
    temp_dir = tempfile.mkdtemp()
    
    def create_chart(choices, labels, title, filename):
        if len(choices) > 0:
            import pandas as pd
            counts = pd.Series(choices).value_counts(normalize=True).reindex(labels, fill_value=0) * 100
            fig, ax = plt.subplots(figsize=(8, 6))
            counts.plot(kind='bar', ax=ax, color=['#1f77b4', '#ff7f0e', '#2ca02c'])
            ax.set_title(title, fontsize=16, fontweight='bold')
            ax.set_ylabel("Percentage (%)", fontsize=12)
            ax.set_xlabel("Choice", fontsize=12)
            ax.tick_params(rotation=0)
            plt.tight_layout()
            filepath = os.path.join(temp_dir, filename)
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            return filepath
        return None
    
    # Generate charts
    chart_files = []
    if p1_choices_r1:
        chart_files.append(create_chart(p1_choices_r1, ["A", "B"], "Player 1 Choices (Round 1)", "p1_r1.png"))
    if p2_choices_r1:
        chart_files.append(create_chart(p2_choices_r1, ["X", "Y", "Z"], "Player 2 Choices (Round 1)", "p2_r1.png"))
    if p1_choices_r2:
        chart_files.append(create_chart(p1_choices_r2, ["A", "B"], "Player 1 Choices (Round 2)", "p1_r2.png"))
    if p2_choices_r2:
        chart_files.append(create_chart(p2_choices_r2, ["X", "Y", "Z"], "Player 2 Choices (Round 2)", "p2_r2.png"))
    
    # Add charts to PDF
    for chart_file in chart_files:
        if chart_file and os.path.exists(chart_file):
            story.append(Image(chart_file, width=6*inch, height=4*inch))
            story.append(Spacer(1, 20))
    
    # Add payoff matrix reference
    story.append(Paragraph("<b>Payoff Matrix Reference</b>", styles['Heading2']))
    payoff_data = [
        ["", "X", "Y", "Z"],
        ["A", "(4, 3)", "(0, 0)", "(1, 4)"],
        ["B", "(0, 0)", "(2, 1)", "(0, 0)"]
    ]
    payoff_table = Table(payoff_data, colWidths=[1*inch, 1*inch, 1*inch, 1*inch])
    payoff_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(payoff_table)
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("Format: (Player 1 Payoff, Player 2 Payoff)", styles['Normal']))
    story.append(Spacer(1, 20))
    story.append(Paragraph("✅ Report generated automatically", styles['Normal']))
    
    # Build PDF
    doc.build(story)
    
    # Cleanup temporary files
    for chart_file in chart_files:
        if chart_file and os.path.exists(chart_file):
            os.remove(chart_file)
    os.rmdir(temp_dir)
    
    buffer.seek(0)
    return buffer
   

# Password protection for admin functions only
admin_password = st.text_input("Admin Password (for database management):", type="password")

if admin_password == "admin123":
    st.header("🔒 Admin Section")
    
    # Set expected number of players
    st.subheader("👥 Game Configuration")
    current_expected = db.reference("expected_players").get() or 0
    st.write(f"Current expected players: {current_expected}")
    
    new_expected_players = st.number_input(
        "Set expected number of players:", 
        min_value=0, 
        max_value=100, 
        value=current_expected,
        step=2,
        help="Must be an even number (players are paired)"
    )
    
    if st.button("⚙ Update Expected Players"):
        if new_expected_players % 2 == 0:  # Must be even for pairing
            db.reference("expected_players").set(new_expected_players)
            st.success(f"✅ Expected players set to {new_expected_players}")
        else:
            st.error("⚠ Number of players must be even (for pairing)")
    
    st.subheader("📄 Game Management")
    
    # PDF Download - Comprehensive report with all games and charts
    if st.button("📄 Download Complete Game Report (PDF)"):
        with st.spinner("Generating comprehensive PDF report with all game data and charts..."):
            try:
                pdf_buffer = create_comprehensive_pdf()
                b64 = base64.b64encode(pdf_buffer.read()).decode()
                href = f'<a href="data:application/pdf;base64,{b64}" download="complete_game_results.pdf">Click here to download Complete Game Report</a>'
                st.markdown(href, unsafe_allow_html=True)
                st.success("✅ Complete game report generated successfully!")
            except Exception as e:
                st.error(f"Error generating PDF: {str(e)}")
                st.info("Please ensure all required libraries are installed.")
    
    # Database cleanup
    if st.button("🗑 Delete ALL Game Data"):
        # Delete all game data from Firebase
        db.reference("games").delete()
        db.reference("matches").delete()
        db.reference("players").delete()
        db.reference("expected_players").set(0)
        st.success("🧹 ALL game data deleted from Firebase.")
        st.warning("⚠ All players, matches, and game history have been permanently removed.")