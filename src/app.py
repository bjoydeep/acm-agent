import streamlit as st
import asyncio
import os
from dotenv import load_dotenv
from acm_agent import create_acm_agent
from react_agent import create_react_acm_agent
from langgraph_react_agent import create_langgraph_react_agent

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="ACM Search Assistant",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stApp {
        background-color: #f8f9fa;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        display: flex;
        align-items: flex-start;
        gap: 0.5rem;
    }
    .chat-message.user {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
    }
    .chat-message.assistant {
        background-color: #f3e5f5;
        border-left: 4px solid #9c27b0;
    }
    .chat-message .avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        color: white;
    }
    .user .avatar {
        background-color: #2196f3;
    }
    .assistant .avatar {
        background-color: #9c27b0;
    }
    .chat-message .content {
        flex: 1;
        margin-left: 0.5rem;
    }
    .sidebar-info {
        background-color: #e8f5e8;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #4caf50;
        margin-bottom: 1rem;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ffc107;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

def display_chat_message(role: str, content: str):
    """Display a chat message with styling"""
    avatar = "👤" if role == "user" else "🤖"
    css_class = role

    st.markdown(f"""
    <div class="chat-message {css_class}">
        <div class="avatar">{avatar}</div>
        <div class="content">
            <strong>{'You' if role == 'user' else 'ACM Assistant'}:</strong><br>
            {content}
        </div>
    </div>
    """, unsafe_allow_html=True)

def main():
    st.title("🔍 ACM Search Assistant")
    st.markdown("*Your intelligent assistant for Red Hat Advanced Cluster Management*")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")

        # API Key inputs
        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=os.getenv("OPENAI_API_KEY", ""),
            help="Enter your OpenAI API key for GPT models"
        )

        claude_api_key = st.text_input(
            "Claude API Key (Optional)",
            type="password",
            value=os.getenv("CLAUDE_API_KEY", ""),
            help="Enter your Claude API key to use Claude models in REACT agent"
        )

        if not api_key and not claude_api_key:
            st.markdown("""
            <div class="warning-box">
                <strong>⚠️ API Key Required</strong><br>
                Please enter at least one API key to start using the assistant.
            </div>
            """, unsafe_allow_html=True)

        # Agent Selection
        agent_type = st.selectbox(
            "🤖 Agent Type",
            ["Linear Agent", "REACT Agent", "LangGraph REACT Agent"],
            help="Choose between Linear (fast, simple), REACT (custom iterative), or LangGraph REACT (official implementation)"
        )

        st.markdown("---")

        # Information section
        st.markdown("""
        <div class="sidebar-info">
            <strong>🎯 What can I help you with?</strong><br><br>
            • Search ACM clusters and resources<br>
            • Find policies and applications<br>
            • Query workloads and deployments<br>
            • Get cluster status information<br>
            • Explore ACM configurations
        </div>
        """, unsafe_allow_html=True)

        # Model info
        st.markdown("**Model:** GPT-4o")
        st.markdown("**MCP Server:** ACM Search")
        st.markdown(f"**Active Agent:** {agent_type}")

        if agent_type == "REACT Agent":
            st.markdown("🔄 *Custom iterative implementation*")
        elif agent_type == "LangGraph REACT Agent":
            st.markdown("🏆 *Official LangGraph REACT*")
        else:
            st.markdown("⚡ *Fast, linear execution*")

        # Clear chat button
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "agent" not in st.session_state:
        st.session_state.agent = None
        st.session_state.current_agent_type = None

    # Initialize agent if API key is provided or agent type changed
    agent_changed = st.session_state.current_agent_type != agent_type
    has_api_key = api_key or claude_api_key

    if has_api_key and (st.session_state.agent is None or agent_changed):
        agent_name = agent_type.replace(" ", "_").lower()
        with st.spinner(f"🔧 Initializing {agent_type}..."):
            try:
                # Create agent asynchronously based on type
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                if agent_type == "REACT Agent":
                    # REACT agent now supports both OpenAI and Claude
                    st.session_state.agent = loop.run_until_complete(create_react_acm_agent(api_key, claude_api_key))
                elif agent_type == "LangGraph REACT Agent":
                    st.session_state.agent = loop.run_until_complete(create_langgraph_react_agent(api_key))
                else:  # Linear Agent
                    st.session_state.agent = loop.run_until_complete(create_acm_agent(api_key))

                st.session_state.current_agent_type = agent_type
                st.success(f"✅ {agent_type} initialized successfully!")

                # Clear messages when switching agents
                if agent_changed:
                    st.session_state.messages = []

            except Exception as e:
                st.error(f"❌ Failed to initialize {agent_type}: {str(e)}")
                st.session_state.agent = None

    # Chat interface
    if api_key:
        # Display chat history
        for message in st.session_state.messages:
            display_chat_message(message["role"], message["content"])

        # Chat input
        if prompt := st.chat_input("Ask me about your ACM clusters and resources..."):
            # Add user message to history
            st.session_state.messages.append({"role": "user", "content": prompt})
            display_chat_message("user", prompt)

            # Get agent response
            if st.session_state.agent:
                with st.spinner("🤔 Thinking..."):
                    try:
                        # Get response from agent
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        response = loop.run_until_complete(st.session_state.agent.chat(prompt))

                        # Add assistant response to history
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        display_chat_message("assistant", response)

                    except Exception as e:
                        error_message = f"❌ Error: {str(e)}"
                        st.session_state.messages.append({"role": "assistant", "content": error_message})
                        display_chat_message("assistant", error_message)
            else:
                error_message = "❌ Agent not initialized. Please check your API key and try again."
                st.session_state.messages.append({"role": "assistant", "content": error_message})
                display_chat_message("assistant", error_message)

        # Example queries
        if not st.session_state.messages:
            st.markdown("### 💡 Try these example queries:")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("🏠 List all clusters", use_container_width=True):
                    st.session_state.example_query = "List all clusters in my ACM environment"
                    st.rerun()

                if st.button("📋 Show policies", use_container_width=True):
                    st.session_state.example_query = "Show me all policies"
                    st.rerun()

            with col2:
                if st.button("🚀 Find applications", use_container_width=True):
                    st.session_state.example_query = "Find all applications deployed"
                    st.rerun()

                if st.button("⚡ Check cluster status", use_container_width=True):
                    st.session_state.example_query = "What is the status of my clusters?"
                    st.rerun()

            # Handle example query clicks
            if "example_query" in st.session_state:
                example_query = st.session_state.example_query
                del st.session_state.example_query

                # Add to messages and process
                st.session_state.messages.append({"role": "user", "content": example_query})
                st.rerun()

    else:
        # Show welcome message when no API key
        st.markdown("""
        ### Welcome to ACM Search Assistant! 👋

        This intelligent assistant helps you search and explore your Red Hat Advanced Cluster Management environment.

        **To get started:**
        1. Enter your OpenAI API key in the sidebar
        2. Start asking questions about your ACM resources

        **What you can search for:**
        - Clusters and their status
        - Policies and compliance
        - Applications and workloads
        - Namespaces and resources
        - Configuration details
        """)

if __name__ == "__main__":
    main()