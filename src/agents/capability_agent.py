from typing import Annotated, TypedDict
import asyncio
import nest_asyncio
from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage
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
        
        # Initialize state with an empty messages list
        initial_state = {"messages": []}
        
        # Build the graph with initial state
        self.graph = self._build_graph(initial_state)
        logger.info("CapabilityAgent initialized with graph built.")
        
    def _build_graph(self, initial_state):
        logger.info("Building the capability agent graph.")
        # Initialize the StateGraph without the initial_state argument
        graph = StateGraph(AgentState)  # Adjust this line based on the correct initialization method
        
        # Define tools using only existing ProfileManager methods
        tools = [
            Tool(
                name="get_all_capabilities",
                func=self._wrap_async(lambda _: self.profile_manager.get_capabilities()),
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
                SystemMessage(content="""You are an AI assistant specialized in answering questions about Nerijus's professional capabilities.
Use the following tools to access accurate information about his skills and experience.
If you don't find specific information about a capability, clearly state that it's not documented.
Respond in a clear and concise manner."""),
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
            input_message = messages[-1] if messages else None
            if isinstance(input_message, tuple) and input_message[0] == "user":
                user_message = input_message[1]
                logger.debug(f"Handling input: {user_message}")
            elif isinstance(input_message, HumanMessage):
                user_message = input_message.content
                logger.debug(f"Handling input: {user_message}")
            else:
                user_message = None

            if user_message:
                response = agent_executor.invoke({"messages": messages})
                logger.debug(f"Response generated: {response}")
                # Add the assistant's response to the messages list
                messages.append(("assistant", response["output"]))
                logger.debug(f"State after processing: {state}")
            return {"messages": messages}
            
        # Add nodes and edges
        graph.add_node("chatbot", chatbot)
        graph.set_entry_point("chatbot")
        
        logger.info("Graph compiled and entry point set.")
        return graph.compile()

    def _wrap_async(self, coro):
        """Wrap an async function to make it sync with better error handling"""
        def wrapper(*args, **kwargs):
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro(*args, **kwargs))
            except Exception as e:
                logger.error(f"Tool execution error: {str(e)}")
                return f"Error executing tool: {str(e)}"
        return wrapper

    @traceable
    async def chat(self, message: str) -> str:
        """Process a message through the graph and return response"""
        logger.info(f"Received message: {message}")
        try:
            # Append the new user message to the state
            response = await self.graph.ainvoke(
                {"messages": [("user", message)]}
            )
            # Extract the content from the last message
            last_message = response["messages"][-1]
            logger.info(f"Response generated: {last_message}")
            # Check if last_message is a structured object with a 'content' attribute
            if hasattr(last_message, 'content'):
                return last_message.content
            elif isinstance(last_message, tuple):
                return last_message[1]
            else:
                return str(last_message)
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return f"Error processing message: {str(e)}"
