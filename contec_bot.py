
import json
from difflib import get_close_matches
import streamlit as st
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="Contec",
    page_icon="🌀",
    layout='centered',
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown(
    """
    <style>
        MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .scrollable-chat {
            max-height: calc(100vh - 200px);
            overflow-y: auto;
            padding-top: 1rem;
        }
        [data-testid="stSidebar"] {
            background-color: white;
            padding: 1rem;
        }
        .sidebar-logo {
            margin-bottom: 1rem;
            text-align: center;
        }
        .restart-prompt {
            color: #ff4b4b;
            font-weight: bold;
            text-align: center;
            margin-top: 1rem;
        }
        .centered-input {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 80%;
            max-width: 600px;
        }
        .bottom-input {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            width: 80%;
            max-width: 600px;
        }
    </style>
    """, 
    unsafe_allow_html=True
)

# -------------------------------------------------------------------------------------

def load_knowledge_base(file_path: str) -> dict:
    """Load the knowledge base from a JSON file."""
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {"questions": []}
    except json.JSONDecodeError:
        st.error("Error reading the knowledge base. Starting fresh.")
        return {"questions": []}

def save_knowledge_base(file_path: str, data: dict):
    """Save the knowledge base to a JSON file."""
    with open(file_path, "w") as file:
        json.dump(data, file, indent=2)

def find_best_match(user_question: str, questions: list[str]) -> str | None:
    """Find the closest matching question from the knowledge base."""
    matches = get_close_matches(user_question, questions, n=1, cutoff=0.6)
    return matches[0] if matches else None

def get_answer(question: str, knowledge_base: dict) -> str | None:
    """Get the answer for a question from the knowledge base."""
    for q in knowledge_base["questions"]:
        if q["question"].lower() == question.lower():
            return q["answer"]
    return None

def check_password():
    """Check if the user has entered the correct password."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if st.session_state.authenticated:
        return True
    
    try:
        correct_password = st.secrets["TRAINER_PASSWORD"]
    except:
        st.error("Password not configured. Please set TRAINER_PASSWORD in secrets.")
        return False
    
    password = st.text_input("Enter training password:", type="password")
    
    if st.button("Authenticate"):
        if password == correct_password:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password")
    
    return False

def display_chat():
    """Display the chat interface with centered input on startup."""
    
    # Initialize session state
    if "chat_active" not in st.session_state:
        st.session_state.chat_active = True
        st.session_state.messages = []
        st.session_state.awaiting_answer = False
        st.session_state.current_question = ""
        st.session_state.first_interaction = True
    
    # Sidebar with logo
    with st.sidebar:
        st.markdown('<div class="sidebar-logo">', unsafe_allow_html=True)
        st.image("https://raw.githubusercontent.com/clakshmanan/contec_chat/main/contec.png", width=250)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.caption("Type 'quit' to exit.")
        
        if st.session_state.get('authenticated', False):
            if st.button("Logout"):
                st.session_state.authenticated = False
                st.session_state.current_question = ""
                st.rerun()
    
    # Main chat area
    st.write("")
    
    # Display chat messages
    with st.container():
        st.markdown('<div class="scrollable-chat">', unsafe_allow_html=True)
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Handle quit state
    if not st.session_state.chat_active:
        st.markdown('<div class="restart-prompt">Please refresh the page to start a new conversation.</div>', unsafe_allow_html=True)
        return
    
    # Load knowledge base
    knowledge_base = load_knowledge_base("knowledge_base.json")
    questions = [q["question"] for q in knowledge_base["questions"]]
    
    # Determine input position (centered on first interaction, bottom afterwards)
    input_class = "centered-input" if st.session_state.first_interaction and not st.session_state.messages else "bottom-input"
    
    # User input container
    st.markdown(f'<div class="{input_class}">', unsafe_allow_html=True)
    if prompt := st.chat_input("Type your question here..."):
        st.session_state.first_interaction = False
        
        if prompt.lower() == 'quit':
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.messages.append({"role": "assistant", "content": "Goodbye! 👋 Please refresh the page to start a new conversation."})
            st.session_state.chat_active = False
            st.rerun()
        
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        if not st.session_state.awaiting_answer:
            # Find best match and respond
            best_match = find_best_match(prompt, questions)
            
            if best_match:
                answer = get_answer(best_match, knowledge_base)
                st.session_state.messages.append({"role": "assistant", "content": answer})
            else:
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": "I don't know the answer. Would you like to train me? (Authenticated users only)"
                })
                st.session_state.current_question = prompt
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Training mode - only if authenticated
    if st.session_state.current_question and check_password():
        with st.form("teach_form"):
            st.write(f"Training for question: '{st.session_state.current_question}'")
            new_answer = st.text_area("Please provide the answer:", key="new_answer")
            submit = st.form_submit_button("Train the bot")
            cancel = st.form_submit_button("Cancel")
            
            if submit and new_answer:
                # Add new Q&A to knowledge base
                knowledge_base["questions"].append({
                    "question": st.session_state.current_question,
                    "answer": new_answer
                })
                save_knowledge_base("knowledge_base.json", knowledge_base)
                
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": f"Thank you! I've learned: '{st.session_state.current_question}'"
                })
                st.session_state.awaiting_answer = False
                st.session_state.current_question = ""
                st.rerun()
            
            if cancel:
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": "Okay, let's continue our conversation."
                })
                st.session_state.awaiting_answer = False
                st.session_state.current_question = ""
                st.rerun()

if __name__ == "__main__":
    display_chat()
