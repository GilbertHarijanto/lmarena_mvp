import streamlit as st
import pandas as pd
import numpy as np
import uuid
from datetime import datetime

# --- Page Configuration ---
st.set_page_config(
    page_title="LM Arena MVP",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Session State Initialization ---
if 'vote_history' not in st.session_state:
    st.session_state.vote_history = []
    st.session_state.judge_hash = f"user_{str(uuid.uuid4())[:8]}"
    st.session_state.suspicion_score = 0.0  # Use float for decay
    st.session_state.status = "✅ Normal"
    st.session_state.triggered_rules = set()
    st.session_state.current_prompt = "Explain the concept of photosynthesis in simple terms."
    st.session_state.model_a_response = "Model A: Photosynthesis is the process plants use to convert light energy into chemical energy, creating food."
    st.session_state.model_b_response = "Model B: Think of photosynthesis as a plant's kitchen! It uses sunlight as the stove to cook up its own food (glucose) from water and carbon dioxide."

# --- "Fake API" Logic ---
def generate_fake_responses(prompt):
    prompt_lower = prompt.lower()
    if "joke" in prompt_lower:
        response_a, response_b = "Why don't scientists trust atoms? Because they make up everything!", "I told my wife she was drawing her eyebrows too high. She looked surprised."
    elif "story" in prompt_lower:
        response_a, response_b = "Once upon a time, in a land of code, a brave function set out to find the missing semicolon.", "The old lighthouse stood against the storm, its light a beacon of hope."
    elif "code" in prompt_lower or "python" in prompt_lower:
        response_a, response_b = "def hello_world():\n    print('Hello, World!')", "def greet(name):\n    return f'Hello, {name}!'"
    else:
        response_a, response_b = f"Model A has processed your request about '{prompt}'.", f"Model B finds your query, '{prompt}', fascinating."
    st.session_state.model_a_response = response_a
    st.session_state.model_b_response = response_b

# --- Comprehensive Fraud Detection Logic ---
def update_suspicion_score():
    """
    Analyzes the user's vote history to incrementally update their suspicion score.
    The score now decays over time with good behavior.
    """
    history_df = pd.DataFrame(st.session_state.vote_history)
    if len(history_df) < 3:
        return # Need more data for robust checks

    # --- 1. Decay the score for every vote, rewarding continued normal behavior ---
    st.session_state.suspicion_score *= 0.9
    
    triggered = set()
    
    # --- 2. Calculate Metrics for the LATEST vote ---
    is_fast_vote = (history_df.iloc[-1]['tstamp'] - history_df.iloc[-2]['tstamp']).total_seconds() < 3
    
    # Win Streak check over last 5 votes
    last_5_votes = history_df.tail(5)
    has_strong_bias = False
    if len(last_5_votes) == 5:
        winner_list = last_5_votes['winner'].tolist()
        if winner_list.count(winner_list[0]) == 5 and winner_list[0] in ['model_a', 'model_b']:
             has_strong_bias = True

    # Repetitive Battles check
    battle_counts = history_df['battle_pair'].value_counts()
    is_repetitive_battle = battle_counts.max() > 5 if not battle_counts.empty else False

    # Repetitive Prompts check
    prompt_diversity = history_df['prompt'].nunique() / len(history_df) if len(history_df) > 0 else 1.0
    is_repetitive_prompt = prompt_diversity < 0.3 and len(history_df) > 5

    # Excessive Ties check
    tie_rate = len(history_df[history_df['winner'].str.contains('tie')]) / len(history_df)
    has_excessive_ties = tie_rate > 0.8 and len(history_df) > 5
    
    # --- 3. Apply Rules to INCREMENT the score for bad behavior ---
    # Combination Rules (high penalty)
    if is_fast_vote and has_strong_bias:
        st.session_state.suspicion_score += 4
        triggered.add("Fast & Biased")
        st.toast("High suspicion: Fast and biased voting detected.", icon="🚨")

    if has_strong_bias and is_repetitive_battle:
        st.session_state.suspicion_score += 3
        triggered.add("Biased & Repetitive Battles")
        st.toast("High suspicion: Targeting specific battles.", icon="🚨")

    if is_fast_vote and is_repetitive_prompt:
        st.session_state.suspicion_score += 2
        triggered.add("Fast & Repetitive Prompts")

    if is_fast_vote and has_excessive_ties:
        st.session_state.suspicion_score += 2
        triggered.add("Fast & Excessive Ties")
        
    # Individual signals (lower penalty)
    if has_strong_bias and not triggered:
        st.session_state.suspicion_score += 1
        triggered.add("Strong Bias")
    if is_fast_vote and not triggered:
        st.session_state.suspicion_score += 1
        triggered.add("Fast Voting")

    st.session_state.triggered_rules = triggered
    st.session_state.suspicion_score = max(0, st.session_state.suspicion_score) # Ensure score doesn't go below 0

    # --- 4. Update User Status based on the new score ---
    if st.session_state.suspicion_score >= 10:
        st.session_state.status = "🚩 FLAGGED"
    elif st.session_state.suspicion_score >= 5:
        st.session_state.status = "⚠️ Suspicious"
    else:
        st.session_state.status = "✅ Normal"

# --- UI Layout ---
st.title("⚖️ LM Arena MVP")
st.markdown("---")

# --- User Status Sidebar ---
with st.sidebar:
    st.header("Your Status")
    st.metric("Judge ID", st.session_state.judge_hash)
    
    status_color = {"✅ Normal": "green", "⚠️ Suspicious": "orange", "🚩 FLAGGED": "red"}
    st.markdown(f"**Status:** <span style='color:{status_color[st.session_state.status]};'>{st.session_state.status}</span>", unsafe_allow_html=True)

    st.metric("Suspicion Score", f"{st.session_state.suspicion_score:.1f} / 10")
    st.progress(min(st.session_state.suspicion_score / 10, 1.0))
    
    if st.session_state.triggered_rules:
        st.subheader("Triggered Rules:")
        for rule in st.session_state.triggered_rules:
            st.warning(f"- {rule}")

    st.markdown("---")
    st.subheader("Vote History")
    if st.session_state.vote_history:
        history_display = pd.DataFrame(st.session_state.vote_history)[['winner', 'suspicion_score_after']]
        st.dataframe(history_display.round(2), use_container_width=True)

# --- Main Arena View ---
st.subheader("Ask Anything...")
prompt_input = st.text_area("Enter your prompt here:", value=st.session_state.current_prompt, height=100, label_visibility="collapsed")

if st.button("Generate Responses", type="primary"):
    st.session_state.current_prompt = prompt_input
    generate_fake_responses(prompt_input)
    st.rerun()

st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    st.subheader("Model A")
    st.info(st.session_state.model_a_response)
with col2:
    st.subheader("Model B")
    st.success(st.session_state.model_b_response)

st.markdown("---")
st.subheader("Cast Your Vote")
vote_cols = st.columns(4)

def handle_vote(winner_choice):
    """Callback function to process a vote."""
    vote_record = {
        'judge_hash': st.session_state.judge_hash,
        'model_a': 'model_alpha', 
        'model_b': 'model_beta',
        'battle_pair': tuple(sorted(('model_alpha', 'model_beta'))),
        'winner': winner_choice,
        'tstamp': datetime.now(),
        'prompt': st.session_state.current_prompt
    }
    st.session_state.vote_history.append(vote_record)
    
    update_suspicion_score()
    
    st.session_state.vote_history[-1]['suspicion_score_after'] = st.session_state.suspicion_score

    new_prompt = np.random.choice(["Tell me a joke.", "Write a short story.", "Explain gravity."])
    st.session_state.current_prompt = new_prompt
    generate_fake_responses(new_prompt)
    st.rerun()

if vote_cols[0].button("Model A is Better", use_container_width=True):
    handle_vote('model_a')
if vote_cols[1].button("Model B is Better", use_container_width=True):
    handle_vote('model_b')
if vote_cols[2].button("Tie", use_container_width=True):
    handle_vote('tie')
if vote_cols[3].button("Both are Bad", type="primary", use_container_width=True):
    handle_vote('tie (bothbad)')
