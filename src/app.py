import streamlit as st
import asyncio
import os
from dotenv import load_dotenv
from acm_agent import create_acm_agent

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
        st.header("🔍 ACM Assistant")

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

        st.markdown("---")

        # Configuration info
        model_name = os.getenv("MODEL_NAME", "gpt-4o")
        model_provider = os.getenv("MODEL_PROVIDER", "openai")
        st.markdown(f"**Model:** {model_provider.title()} {model_name}")
        st.markdown("**MCP Server:** ACM Search")

        # Check configuration status
        has_api_key = bool(os.getenv("OPENAI_API_KEY"))
        has_mcp_config = bool(os.getenv("MCP_SERVER_URL"))

        if has_api_key and has_mcp_config:
            st.markdown("✅ **Status:** Ready")
        else:
            st.markdown("⚠️ **Status:** Configuration incomplete")
            if not has_api_key:
                st.markdown("- Missing OPENAI_API_KEY")
            if not has_mcp_config:
                st.markdown("- Missing MCP_SERVER_URL")

        st.markdown("---")

        # Clear chat button
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "agent" not in st.session_state:
        st.session_state.agent = None

    # Check if we have required configuration
    has_api_key = bool(os.getenv("OPENAI_API_KEY"))
    has_mcp_config = bool(os.getenv("MCP_SERVER_URL"))
    has_config = has_api_key and has_mcp_config

    # Initialize agent if configuration is available and agent not yet created
    if has_config and st.session_state.agent is None:
        with st.spinner("🔧 Initializing ACM Agent..."):
            try:
                # Create agent using environment configuration
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                st.session_state.agent = loop.run_until_complete(create_acm_agent())
                st.success("✅ ACM Agent initialized successfully!")

            except Exception as e:
                st.error(f"❌ Failed to initialize agent: {str(e)}")
                st.session_state.agent = None

    # Chat interface
    if has_config:
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
                error_message = "❌ Agent not initialized. Please check your configuration."
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
        # Show welcome message when configuration is missing
        st.markdown("""
        ### Welcome to ACM Search Assistant! 👋

        This intelligent assistant helps you search and explore your Red Hat Advanced Cluster Management environment.

        **Configuration Required:**
        """)

        if not has_api_key:
            st.markdown("❌ **OPENAI_API_KEY** environment variable not set")
        if not has_mcp_config:
            st.markdown("❌ **MCP_SERVER_URL** environment variable not set")

        st.markdown("""
        **To get started:**
        1. Set the required environment variables (see .env.example)
        2. Restart the application
        3. Start asking questions about your ACM resources

        **What you can search for:**
        - Clusters and their status
        - Policies and compliance
        - Applications and workloads
        - Namespaces and resources
        - Configuration details
        """)

if __name__ == "__main__":
    main()