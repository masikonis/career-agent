import logging
from typing import Annotated, TypedDict
import asyncio
import nest_asyncio
from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from src.profile.manager import ProfileManager
from src.config.settings import config
from langsmith import traceable
from src.utils.logger import get_logger

# Enable nested event loops
nest_asyncio.apply()

# Configure logging
logger = get_logger(__name__)

class AgentState(TypedDict):
    """State definition for the capability agent graph"""
    messages: Annotated[list, add_messages]

class CapabilityAgent:
    """Agent that understands and can discuss capabilities using a graph-based approach"""
    
    def __init__(self, profile_manager: ProfileManager, llm=None):
        self.profile_manager = profile_manager
        self.llm = llm or ChatOpenAI(temperature=0, model=config['LLM_MODELS']['advanced'])
        
        # Build the graph
        self.graph = self._build_graph()
        logger.info("CapabilityAgent initialized with graph built.")
        
    def _build_graph(self):
        logger.info("Building the capability agent graph.")
        # Create graph builder with defined state
        graph = StateGraph(AgentState)
        
        # Define tools using only existing ProfileManager methods
        tools = [
            Tool(
                name="get_all_capabilities",
                func=self._wrap_async(lambda: self.profile_manager.get_capabilities()),
                description="Get a list of all capabilities"
            ),
            Tool(
                name="get_capabilities_by_category",
                func=self._wrap_async(self.profile_manager.get_capabilities_by_category),
                description="Get capabilities filtered by category (e.g., Technical, Leadership)"
            ),
            Tool(
                name="get_top_capabilities",
                func=self._wrap_async(self.profile_manager.get_top_capabilities),
                description="Get top capabilities (Expert/Advanced level skills)"
            ),
            Tool(
                name="search_capabilities",
                func=self._wrap_async(lambda query: self.profile_manager.search_capabilities(query)),
                description="Search for specific capabilities by keyword"
            )
        ]

        # Create the agent with tools
        agent = create_openai_functions_agent(
            llm=self.llm,
            tools=tools,
            prompt=ChatPromptTemplate.from_messages([
                SystemMessage(content="""You are an AI assistant that helps answer questions about Nerijus's professional capabilities.
                Use the provided tools to access accurate information about his skills and experience.
                If you don't find specific information about a capability, clearly state that it's not documented."""),
                MessagesPlaceholder(variable_name="messages"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
        )
        
        # Create the agent executor
        agent_executor = AgentExecutor(agent=agent, tools=tools)
        
        def chatbot(state: AgentState):
            """Main chatbot node that processes messages"""
            messages = state["messages"]
            logger.debug(f"Processing messages: {messages}")
            # Ensure correct input handling
            if isinstance(messages, dict) and "input" in messages:
                input_value = messages["input"]
                # Handle input_value appropriately
                logger.debug(f"Handling input: {input_value}")
            response = agent_executor.invoke({"messages": messages})
            logger.debug(f"Response generated: {response}")
            return {"messages": [response["output"]]}
            
        # Add nodes and edges
        graph.add_node("chatbot", chatbot)
        graph.set_entry_point("chatbot")
        
        logger.info("Graph compiled and entry point set.")
        return graph.compile()

    def _wrap_async(self, coro):
        """Wrap an async function to make it sync"""
        def wrapper(*args, **kwargs):
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            # Ensure no extra arguments are passed to coro
            return loop.run_until_complete(coro(*args, **kwargs))
        return wrapper

    @traceable
    async def chat(self, message: str) -> str:
        """Process a message through the graph and return response"""
        logger.info(f"Received message: {message}")
        try:
            response = await self.graph.ainvoke(
                {"messages": [("user", message)]}
            )
            # Convert message to string if needed
            last_message = response["messages"][-1]
            logger.info(f"Response generated: {last_message}")
            return last_message.content if hasattr(last_message, 'content') else str(last_message)
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return f"Error processing message: {str(e)}"
