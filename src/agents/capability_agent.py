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

# Enable nested event loops
nest_asyncio.apply()

class AgentState(TypedDict):
    """State definition for the capability agent graph"""
    messages: Annotated[list, add_messages]

class CapabilityAgent:
    """Agent that understands and can discuss capabilities using a graph-based approach"""
    
    def __init__(self, profile_manager: ProfileManager, llm=None):
        self.profile_manager = profile_manager
        self.llm = llm or ChatOpenAI(temperature=0, model="gpt-3.5-turbo")
        
        # Build the graph
        self.graph = self._build_graph()
        
    def _build_graph(self):
        # Create graph builder with defined state
        graph = StateGraph(AgentState)
        
        # Define tools using only existing ProfileManager methods
        tools = [
            Tool(
                name="get_all_capabilities",
                func=self._wrap_async(self.profile_manager.get_capabilities),
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
                func=self._wrap_async(self.profile_manager.search_capabilities),
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
            response = agent_executor.invoke({"messages": messages})
            return {"messages": [response["output"]]}
            
        # Add nodes and edges
        graph.add_node("chatbot", chatbot)
        graph.set_entry_point("chatbot")
        
        return graph.compile()

    def _wrap_async(self, coro):
        """Wrap an async function to make it sync"""
        def wrapper(*args, **kwargs):
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro(*args, **kwargs))
        return wrapper

    async def chat(self, message: str) -> str:
        """Process a message through the graph and return response"""
        try:
            response = await self.graph.ainvoke(
                {"messages": [("user", message)]}
            )
            # Convert message to string if needed
            last_message = response["messages"][-1]
            return last_message.content if hasattr(last_message, 'content') else str(last_message)
        except Exception as e:
            return f"Error processing message: {str(e)}"
