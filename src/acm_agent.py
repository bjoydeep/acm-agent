import asyncio
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode


@dataclass
class ACMAgentConfig:
    # LLM Configuration
    openai_api_key: str
    model_provider: str = "openai"
    model_name: str = "gpt-4o"
    temperature: float = 0.01

    # MCP Configuration
    mcp_server_url: str = ""
    mcp_transport: str = "sse"
    mcp_bearer_token: str = ""

    @classmethod
    def from_env(cls) -> 'ACMAgentConfig':
        """Load configuration from environment variables"""
        return cls(
            # LLM settings
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            model_provider=os.getenv("MODEL_PROVIDER", "openai"),
            model_name=os.getenv("MODEL_NAME", "gpt-4o"),
            temperature=float(os.getenv("MODEL_TEMPERATURE", "0.01")),

            # MCP settings
            mcp_server_url=os.getenv("MCP_SERVER_URL", ""),
            mcp_transport=os.getenv("MCP_TRANSPORT", "sse"),
            mcp_bearer_token=os.getenv("MCP_BEARER_TOKEN", "")
        )

    def get_model_string(self) -> str:
        """Get the model string for LangChain init_chat_model"""
        return f"{self.model_provider}:{self.model_name}"

    def get_mcp_config(self) -> Dict[str, Any]:
        """Get MCP client configuration"""
        return {
            "acm-search": {
                "url": self.mcp_server_url,
                "transport": self.mcp_transport,
                "headers": {
                    "Authorization": f"Bearer {self.mcp_bearer_token}"
                }
            }
        }


class ACMSearchAgent:
    def __init__(self, config: ACMAgentConfig):
        self.config = config
        self.llm = None
        self.mcp_client = None
        self.tools = []
        self.model_with_tools = None
        self.tool_node = None
        self.graph = None
        self.system_prompt = None  # Cache the system prompt

    async def setup_mcp_connection(self):
        """Set up connection to MCP server and get available tools"""
        try:
            print(f"🔧 Initializing {self.config.model_provider} model: {self.config.model_name}")

            # Load and cache the system prompt (only once during initialization)
            self.system_prompt = self.load_system_prompt()
            print("📝 === LOADED SYSTEM PROMPT ===")
            print(self.system_prompt)
            print("📝 === END SYSTEM PROMPT ===")

            # Initialize the model using configuration
            self.llm = init_chat_model(
                self.config.get_model_string(),
                api_key=self.config.openai_api_key,
                temperature=self.config.temperature
            )

            print(f"🔗 Attempting MCP connection to: {self.config.mcp_server_url}")
            # Set up MCP client using configuration
            mcp_config = self.config.get_mcp_config()
            self.mcp_client = MultiServerMCPClient(mcp_config)

            print("📡 Getting tools from MCP server...")
            # Get tools from MCP server
            self.tools = await self.mcp_client.get_tools()
            print(f"✅ Connected to MCP server. Available tools: {[tool.name for tool in self.tools]}")

            print("🔗 Binding tools to model...")
            # Bind tools to model
            self.model_with_tools = self.llm.bind_tools(self.tools)

            # Create ToolNode with custom wrapper for debugging
            self.tool_node = self.create_debug_tool_node()
            print(f"🎯 Created ToolNode with {len(self.tools)} tools")

        except Exception as e:
            print(f"Failed to connect to MCP server: {e}")
            # Fallback to basic OpenAI model without tools
            self.llm = ChatOpenAI(
                api_key=self.config.openai_api_key,
                model=self.config.model_name,
                temperature=self.config.temperature
            )
            self.tools = []

    def create_debug_tool_node(self):
        """Create a ToolNode with debug printing"""
        async def debug_tool_execution(state: MessagesState):
            messages = state["messages"]
            last_message = messages[-1]

            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                for tool_call in last_message.tool_calls:
                    print(f"🔧 Tool called: {tool_call['name']}")
                    print(f"📝 Tool args: {tool_call['args']}")

            # Execute the actual tools
            tool_node = ToolNode(self.tools)
            result = await tool_node.ainvoke(state)

            # Print tool results
            if 'messages' in result:
                for msg in result['messages']:
                    if hasattr(msg, 'content'):
                        print(f"📊 Tool result: {msg.content}")

            return result

        return debug_tool_execution

    def load_system_prompt(self):
        """Load system prompt from external file"""
        try:
            prompt_file = Path(__file__).parent / "acm_system_prompt.txt"
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            print(f"Warning: Could not find prompt file at {prompt_file}")
            return self.get_fallback_prompt()
        except Exception as e:
            print(f"Warning: Could not load prompt file: {e}")
            return self.get_fallback_prompt()

    def get_fallback_prompt(self):
        """Fallback prompt if file loading fails"""
        return """
        You are an ACM (Advanced Cluster Management) assistant that helps users search and find information about their Red Hat OpenShift clusters and resources.

        CRITICAL DATABASE SCHEMA KNOWLEDGE:
        - Main table: search.resources with columns: uid (text), cluster (text), data (jsonb)
        - ALL resource information is stored in the 'data' JSONB column
        - Always explore the data structure before making assumptions

        CRITICAL: NEVER HALLUCINATE MISSING DATA
        - If data fields are missing, explicitly state the limitation
        - Never assume "no field = feature disabled"
        - Always be honest about data completeness

        IMPORTANT: Always discover the actual data structure first using:
        SELECT jsonb_pretty(data) FROM search.resources WHERE data->>'kind' = 'ResourceType' LIMIT 1;
        """

    def get_loaded_system_prompt(self):
        """Get the currently loaded system prompt for debugging/display purposes"""
        return self.system_prompt or self.load_system_prompt()

    def should_continue(self, state: MessagesState):
        """Determine if we should continue to tools or end"""
        messages = state["messages"]
        last_message = messages[-1]
        print(f"Messages being exchanged: {last_message}")
        if last_message.tool_calls:
            return "tools"
        return END

    async def call_model(self, state: MessagesState):
        """Call the model with current state"""
        messages = state["messages"]

        # Add system message for ACM context (use cached prompt)
        system_msg = SystemMessage(content=self.system_prompt)

        # Insert system message at the beginning if not already there
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [system_msg] + messages

        if self.model_with_tools:
            response = await self.model_with_tools.ainvoke(messages)
        else:
            # Fallback to basic model
            response = await self.llm.ainvoke(messages)

        return {"messages": [response]}

    def create_graph(self):
        """Create the LangGraph workflow"""
        builder = StateGraph(MessagesState)
        builder.add_node("call_model", self.call_model)

        if self.tools and self.tool_node:
            builder.add_node("tools", self.tool_node)
            builder.add_edge(START, "call_model")
            builder.add_conditional_edges(
                "call_model",
                self.should_continue,
            )
            builder.add_edge("tools", "call_model")
        else:
            # Simple flow without tools
            builder.add_edge(START, "call_model")
            builder.add_edge("call_model", END)

        self.graph = builder.compile()

    async def chat(self, user_input: str) -> str:
        """Process a user input and return the agent's response"""
        print(f"\n{'='*60}")
        print(f"🚀 START OF QUESTION: {user_input}")
        print(f"{'='*60}")

        if not self.graph:
            await self.setup_mcp_connection()
            self.create_graph()

        # Create the input state
        input_state = {"messages": [HumanMessage(content=user_input)]}

        # Run the graph
        result = await self.graph.ainvoke(input_state)

        # Get the final response
        final_response = result["messages"][-1].content

        print(f"\n{'='*60}")
        print(f"✅ FINAL ANSWER: {final_response}")
        print(f"{'='*60}\n")

        # Return the last message content
        return final_response


async def create_acm_agent(openai_api_key: str = None) -> ACMSearchAgent:
    """Create and initialize an ACM search agent"""
    # Load configuration from environment variables
    config = ACMAgentConfig.from_env()

    # Override with provided API key if given (for backwards compatibility)
    if openai_api_key:
        config.openai_api_key = openai_api_key

    agent = ACMSearchAgent(config)
    await agent.setup_mcp_connection()
    agent.create_graph()
    return agent