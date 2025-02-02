import streamlit as st
import pandas as pd
import os
import time
import random
import csv
from datetime import datetime

# Configure page
st.set_page_config(
    page_title="Quizzy Pro",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling
st.markdown("""
<style>
    .correct { color: #4CAF50; font-weight: bold; }
    .incorrect { color: #f44336; font-weight: bold; }
    .question-review { 
        border-left: 4px solid #4CAF50; 
        padding: 1rem; 
        margin: 1rem 0;
        background-color: #f8f9fa;
        border-radius: 8px;
    }
    .score-card { 
        background-color: #f8f9fa; 
        padding: 2rem; 
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .review-header {
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
    }
    .stProgress > div > div > div {
        background-color: #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
if 'quiz_state' not in st.session_state:
    st.session_state.update({
        'quiz_state': 'not_started',
        'admin_logged_in': False,
        'current_question': 0,
        'user_answers': {},
        'shuffled_options': {},
        'question_feedback': [],
        'quiz_duration': 0,
        'final_score': 0
    })

# Admin credentials (store securely in production)
ADMIN_CREDENTIALS = {
    "admin": "quizzy123"
}

# Results storage files
RESULTS_FILE = "quiz_results.csv"
QUESTIONS_FILE = "numpy1.csv"

# App title
st.title("🧠 Quizzy Pro: Ultimate Quiz Experience")

# --- Student Authentication Section ---
with st.sidebar.expander("🎓 Student Login", expanded=True):
    st.markdown('<div style="padding:15px; border-radius:10px; background-color:#f0f2f6;">', unsafe_allow_html=True)
    student_name = st.text_input("Full Name", key="student_name")
    student_email = st.text_input("Email Address", key="student_email")
    st.markdown('</div>', unsafe_allow_html=True)

# --- Admin Authentication Section ---
with st.sidebar.expander("🔐 Admin Login"):
    admin_user = st.text_input("Admin Username", key="admin_user")
    admin_pass = st.text_input("Admin Password", type="password", key="admin_pass")
    if st.button("Admin Login"):
        if ADMIN_CREDENTIALS.get(admin_user) == admin_pass:
            st.session_state.admin_logged_in = True
            st.success("Admin login successful!")
        else:
            st.error("Invalid admin credentials")

# --- Admin Features ---
if st.session_state.admin_logged_in:
    st.sidebar.markdown("---")
    st.sidebar.header("🔧 Admin Tools")
    
    # Add new questions
    with st.sidebar.expander("➕ Add New Question"):
        with st.form("new_question"):
            new_question = st.text_area("Question")
            opt1 = st.text_input("Option 1")
            opt2 = st.text_input("Option 2")
            opt3 = st.text_input("Option 3")
            opt4 = st.text_input("Option 4")
            correct_answer = st.selectbox("Correct Answer", [opt1, opt2, opt3, opt4])
            
            if st.form_submit_button("Save Question"):
                new_row = {
                    'question': new_question,
                    'option1': opt1,
                    'option2': opt2,
                    'option3': opt3,
                    'option4': opt4,
                    'correct_answer': correct_answer
                }
                
                # Save to CSV
                with open(QUESTIONS_FILE, 'a') as f:
                    writer = csv.DictWriter(f, fieldnames=new_row.keys())
                    if os.stat(QUESTIONS_FILE).st_size == 0:
                        writer.writeheader()
                    writer.writerow(new_row)
                st.success("Question saved successfully!")

    # View all results
    if st.sidebar.button("📊 View All Results"):
        try:
            results_df = pd.read_csv(RESULTS_FILE)
            st.subheader("📈 All Student Results")
            
            # Format dataframe display
            styled_df = results_df.style.format({
                'timestamp': lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S").strftime("%d %b %Y %H:%M")
            })
            
            st.dataframe(
                styled_df,
                column_config={
                    "timestamp": "Date/Time",
                    "student_name": "Name",
                    "student_email": "Email",
                    "score": st.column_config.NumberColumn("Score", format="%d/%d"),
                    "time_seconds": "Duration (sec)"
                },
                hide_index=True,
                use_container_width=True
            )
            
            # Download button
            csv_data = results_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Full Results",
                data=csv_data,
                file_name="quiz_results.csv",
                mime="text/csv"
            )
        except FileNotFoundError:
            st.warning("No results available yet")

# --- Main Quiz Logic ---
def load_questions():
    """Load questions with caching and validation"""
    try:
        df = pd.read_csv(QUESTIONS_FILE)
        required_columns = ['question', 'option1', 'option2', 'option3', 'option4', 'correct_answer']
        
        if not all(col in df.columns for col in required_columns):
            st.error("Invalid question format in database")
            return None
            
        return df.sample(frac=1).reset_index(drop=True)  # Shuffle questions
    except FileNotFoundError:
        st.error("Question database not found")
        return None

def display_question():
    """Display current question with stable shuffled options"""
    idx = st.session_state.current_question
    row = st.session_state.quiz_df.iloc[idx]
    
    # Generate consistent shuffled options for this question
    if idx not in st.session_state.shuffled_options:
        options = [row['option1'], row['option2'], row['option3'], row['option4']]
        random.shuffle(options)
        st.session_state.shuffled_options[idx] = options
    
    options = st.session_state.shuffled_options[idx]
    
    with st.expander(f"Question {idx + 1}", expanded=True):
        st.markdown(f"#### {row['question']}")
        
        # Display options as buttons
        cols = st.columns(2)
        for i, option in enumerate(options):
            with cols[i % 2]:
                btn_type = "primary" if st.session_state.user_answers.get(idx) == option else "secondary"
                if st.button(
                    option,
                    key=f"q{idx}_opt{i}",
                    use_container_width=True,
                    type=btn_type
                ):
                    st.session_state.user_answers[idx] = option

def save_result(score, duration):
    """Save student results to CSV with detailed feedback"""
    result = {
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'student_name': student_name,
        'student_email': student_email,
        'score': score,
        'total_questions': len(st.session_state.quiz_df),
        'time_seconds': int(duration),
        'detailed_feedback': str(st.session_state.question_feedback)
    }
    
    # Write to CSV
    file_exists = os.path.isfile(RESULTS_FILE)
    with open(RESULTS_FILE, 'a') as f:
        writer = csv.DictWriter(f, fieldnames=result.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(result)

# --- Student Quiz Interface ---
if not st.session_state.admin_logged_in:
    # Validate student info
    if not student_name or not student_email:
        st.warning("Please enter your name and email in the sidebar to start the quiz!")
    else:
        if st.session_state.quiz_state == 'not_started':
            if st.button("🚀 Start Quiz"):
                st.session_state.quiz_df = load_questions()
                if st.session_state.quiz_df is not None:
                    st.session_state.quiz_state = 'in_progress'
                    st.session_state.start_time = time.time()
                    st.rerun()

        if st.session_state.quiz_state == 'in_progress':
            # Quiz progress
            current_q = st.session_state.current_question
            total_q = len(st.session_state.quiz_df)
            
            # Display progress
            progress = (current_q + 1) / total_q
            st.progress(progress, text=f"Question {current_q + 1} of {total_q}")
            
            # Display current question
            display_question()
            
            # Navigation controls
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if current_q > 0:
                    st.button("← Previous", on_click=lambda: st.session_state.update({"current_question": current_q - 1}))
                if current_q < total_q - 1:
                    st.button("Next →", on_click=lambda: st.session_state.update({"current_question": current_q + 1}))
                else:
                    if st.button("Submit Quiz", type="primary"):
                        # Calculate results
                        question_feedback = []
                        for idx in range(total_q):
                            row = st.session_state.quiz_df.iloc[idx]
                            user_answer = st.session_state.user_answers.get(idx)
                            correct_answer = row['correct_answer']
                            
                            # Verify answer exists in shuffled options
                            shuffled = st.session_state.shuffled_options.get(idx, [])
                            actual_correct = correct_answer in shuffled
                            
                            question_feedback.append({
                                'question': row['question'],
                                'user_answer': user_answer or "Not answered",
                                'correct_answer': correct_answer,
                                'correct': user_answer == correct_answer if actual_correct else False
                            })
                        
                        # Update session state
                        st.session_state.question_feedback = question_feedback
                        st.session_state.quiz_duration = time.time() - st.session_state.start_time
                        st.session_state.final_score = sum(1 for fb in question_feedback if fb['correct'])
                        
                        # Save results
                        save_result(st.session_state.final_score, st.session_state.quiz_duration)
                        st.session_state.quiz_state = 'completed'
                        st.rerun()

        elif st.session_state.quiz_state == 'completed':
            # Display results
            st.balloons()
            st.markdown('<div class="score-card">', unsafe_allow_html=True)
            st.subheader("📝 Quiz Results Summary")
            
            # Student info
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Student Name:**  \n{student_name}")
            with col2:
                st.markdown(f"**Email:**  \n{student_email}")
            
            # Score and time
            col3, col4 = st.columns(2)
            with col3:
                st.markdown(f"**Final Score:**  \n{st.session_state.final_score}/{len(st.session_state.quiz_df)}")
            with col4:
                mins = int(st.session_state.quiz_duration // 60)
                secs = int(st.session_state.quiz_duration % 60)
                st.markdown(f"**Time Taken:**  \n{mins} minutes {secs} seconds")
            
            st.markdown('</div>', unsafe_allow_html=True)

            # Detailed question review
            st.subheader("🔍 Detailed Question Review")
            for idx, feedback in enumerate(st.session_state.question_feedback):
                with st.expander(f"Question {idx+1}: {feedback['question']}", expanded=False):
                    st.markdown(f"""
                    <div class="question-review">
                        <div class="review-header">
                            <span class="{'correct' if feedback['correct'] else 'incorrect'}">
                                Your answer: {feedback['user_answer']} {'✅' if feedback['correct'] else '❌'}
                            </span>
                        </div>
                        <p><strong>Correct Answer:</strong> {feedback['correct_answer']}</p>
                    </div>
                    """, unsafe_allow_html=True)

            # Restart button
            if st.button("🔄 Take Quiz Again"):
                st.session_state.quiz_state = 'not_started'
                st.session_state.current_question = 0
                st.session_state.user_answers = {}
                st.session_state.shuffled_options = {}
                st.session_state.question_feedback = []
                st.rerun()

# --- Footer ---
st.markdown("---")
st.markdown("### 🏆 Quizzy Pro v3.1 | Secure Student Assessment System")