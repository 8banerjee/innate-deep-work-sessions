import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import psycopg2
from sqlalchemy import create_engine
from sqlalchemy import text
import logging
from sqlalchemy.exc import SQLAlchemyError
import matplotlib.pyplot as plt  # Ensure plt is imported
import altair as alt


# Set up logging
logging.basicConfig(
    filename="app_errors.log",  # Log file name
    level=logging.ERROR,  # Log level
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log format
)

# Database connection string (update with your credentials)
DB_HOST = "localhost"
DB_NAME = "deep_work_db"
DB_USER = "postgres"
DB_PASS = "innate-ai"
DB_PORT = "5432"

params = st.query_params

# Create database connection
engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


def save_session_to_db(name, buddy, task):
    query = text(
        """
        INSERT INTO deep_work_sessions (timestamp, name, buddy, task)
        VALUES (NOW(), :name, :buddy, :task)
    """
    )
    logging.info(f"Attempting to save: name={name}, buddy={buddy}, task={task}")
    try:
        with engine.begin() as conn:
            conn.execute(query, {"name": name, "buddy": buddy, "task": task})
        logging.info("Session saved successfully.")
        st.success("Session saved successfully!")
    except Exception as e:
        logging.error(f"Error saving session: {e}")
        st.error(f"Error saving session: {e}")


# Function to load all sessions from the database
def load_sessions_from_db():
    try:
        with engine.connect() as conn:
            # Log successful connection
            logging.info("Database connection successful.")

            # Execute the query and return results
            return pd.read_sql("SELECT * FROM deep_work_sessions", conn)
    except SQLAlchemyError as e:
        # Log error to the log file
        logging.error(f"Database connection or query failed: {e}")

        # Return an empty DataFrame in case of failure
        return pd.DataFrame(columns=["timestamp", "name", "buddy", "task"])


# Temporary section to display the data from the database
if st.button("View All Stored Sessions"):
    try:
        query = "SELECT * FROM deep_work_sessions ORDER BY timestamp DESC"
        with engine.connect() as conn:
            data = pd.read_sql(query, conn)
        st.write("All Stored Sessions", data)
    except Exception as e:
        st.error(f"Error retrieving data: {e}")

# Load sessions from the database on app startup
if "sessions" not in st.session_state:
    try:
        st.session_state.sessions = load_sessions_from_db()
    except Exception as e:
        st.warning(f"Error loading data from database: {e}")
        st.session_state.sessions = pd.DataFrame(
            columns=["timestamp", "name", "buddy", "task"]
        )

# Display Headers in columns
col1, col2 = st.columns([1, 1])  # Adjust the width ratio as needed

# Last Updated Text
with col1:
    st.markdown(
        """
    <div style="display: flex; align-items: center; gap: 10px;">
        <h1 style="margin: 0;">🎯 Deep Work Session Tracker</h1>        
    </div>
    """,
        unsafe_allow_html=True,
    )

# Refresh Leaderboard Button
with col2:
    st.markdown(
        """
    <div style="display: flex; align-items: center; gap: 10px;">
        <img src="https://static.wixstatic.com/media/cb8cad_74b87ca69295429cb8dfc19e42a4bedf~mv2.png" alt="Logo" style="width: 150px; height: auto;">
  
    </div>
    """,
        unsafe_allow_html=True,
    )

st.subheader("Track your focused work with accountability buddies")


# Input form
with st.form("deep_work_form"):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Your Name")
    with col2:
        buddy = st.text_input("Accountability Buddy")

    task = st.text_area("What did you accomplish in this deep work session?")
    submitted = st.form_submit_button("Record Deep Work Session")

    if submitted and name and buddy and task:
        # Add new session to the database
        try:
            save_session_to_db(name, buddy, task)
            st.session_state.sessions = load_sessions_from_db()
            st.success("Deep work session recorded! 🎉")
        except Exception as e:
            st.error(f"Error saving session to database: {e}")


# Display weekly leaderboard

# Initialize a flag in session state to control refresh
if "refresh" not in st.session_state:
    st.session_state.refresh = False


# Check if refresh is triggered
if st.session_state.refresh:
    st.session_state.refresh = False  # Reset the flag
    # Update query params to trigger rerun
    st.query_params = {**st.query_params, "refresh": "true"}

# Display the last updated time
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.header("📊 This Week's Leaderboard")


if not st.session_state.sessions.empty:
    # Convert 'timestamp' to datetime and remove timezone information
    st.session_state.sessions["timestamp"] = pd.to_datetime(
        st.session_state.sessions["timestamp"]
    )
    st.session_state.sessions["timestamp"] = st.session_state.sessions[
        "timestamp"
    ].dt.tz_localize(None)

    # Calculate start of the current week (Monday at 00:00:00)
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

    # Display Last Updated and Refresh Button

    # Last Updated Text
    st.caption(f"Start of Week: {start_of_week.strftime('%Y-%m-%d %H:%M:%S')}")

    # Refresh Leaderboard Button
    if st.button("🔄 Refresh Leaderboard"):
        st.session_state.refresh = True  # Trigger refresh logic

    # st.write("Start of Week:", start_of_week)  # Debug: Check start of week

    # Filter sessions for the current week
    weekly_sessions = st.session_state.sessions[
        st.session_state.sessions["timestamp"] >= start_of_week
    ]

    # st.write("Filtered Weekly Sessions:", weekly_sessions)  # Debug: Check filtered data

    if not weekly_sessions.empty:
        # Total sessions this week (for the table)
        session_counts = weekly_sessions["name"].value_counts().reset_index()
        session_counts.columns = ["Name", "Number of Sessions"]

        # Add ranking with emojis
        rank_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}  # Define emoji mapping for top 3
        session_counts["Rank"] = [
            f"{rank_emojis.get(i + 1, str(i + 1) + 'th')}"
            for i in range(len(session_counts))
        ]

        # Reorder columns to display Rank first
        session_counts = session_counts[["Rank", "Name", "Number of Sessions"]]

        # Display the leaderboard table without an index
        st.dataframe(session_counts, use_container_width=True, hide_index=True)

        # Prepare data for the bar graph (sessions per day)
        weekly_sessions["day"] = weekly_sessions["timestamp"].dt.strftime(
            "%a"
        )  # Day names (Mon, Tue, etc.)
        sessions_per_day = weekly_sessions.groupby("day").size()

        # Sort days in calendar order
        days_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        sessions_per_day = sessions_per_day.reindex(days_order, fill_value=0)

        # Plot the bar graph

        # Prepare data for the bar chart (sessions per day)
        weekly_sessions["day"] = weekly_sessions["timestamp"].dt.strftime(
            "%a"
        )  # Day names (Mon, Tue, etc.)
        sessions_per_day = (
            weekly_sessions.groupby("day")
            .size()
            .reindex(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], fill_value=0)
            .reset_index()
        )
        sessions_per_day.columns = ["Day", "Number of Sessions"]

        # Create Altair bar chart
        bar_chart = (
            alt.Chart(sessions_per_day)
            .mark_bar(color="skyblue")
            .encode(
                x=alt.X(
                    "Day",
                    sort=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                    axis=alt.Axis(labelAngle=-45),
                ),
                y=alt.Y("Number of Sessions", title="Sessions"),
                tooltip=["Day", "Number of Sessions"],
            )
            .properties(title="Team Sessions This Week 🥳", width=600, height=400)
        )

        # Render the chart in Streamlit
        st.altair_chart(bar_chart, use_container_width=True)

    else:
        st.info("No sessions recorded this week yet.")
else:
    st.info("No sessions found in the database.")

# Display all-time leaderboard
st.header("🏆 All-Time Leaderboard")

if not st.session_state.sessions.empty:
    # Calculate sessions per person (all-time)
    all_time_leaderboard = (
        st.session_state.sessions["name"].value_counts().reset_index()
    )
    all_time_leaderboard.columns = ["Team Member", "Total Sessions"]

    st.dataframe(all_time_leaderboard, hide_index=True)

# Display recent sessions
st.header("🕒 Recent Sessions")
recent_sessions = st.session_state.sessions.sort_values("timestamp", ascending=False)
for _, session in recent_sessions.iterrows():
    with st.expander(
        f"{session['name']} with {session['buddy']} - {session['timestamp']}"
    ):
        st.write(session["task"])
