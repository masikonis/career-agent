from typing import Annotated, TypedDict, Optional, Any, Callable, Union
import asyncio
import nest_asyncio
from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langgraph.graph import StateGraph, END, MessagesState
from langgraph.graph.message import add_messages
from src.profile.manager import ProfileManager
from src.config.settings import config
from langsmith import traceable
from src.utils.logger import get_logger

# Enable nested event loops
nest_asyncio.apply()

# Configure logging
logger = get_logger(__name__)

class CapabilityAgent:
    """Agent that understands and can discuss capabilities using a graph-based approach"""
    
    def __init__(self, profile_manager: ProfileManager, llm=None, model_name=None):
        if not isinstance(profile_manager, ProfileManager):
            raise ValueError("profile_manager must be an instance of ProfileManager")
        
        self.profile_manager = profile_manager
        
        # Validate model name if provided
        if model_name and model_name not in config['LLM_MODELS'].values():
            raise ValueError(f"Invalid model_name. Must be one of: {list(config['LLM_MODELS'].values())}")
        
        # Use provided model name or default to basic
        model = model_name or config['LLM_MODELS']['basic']
        self.llm = llm or ChatOpenAI(
            temperature=0,
            model=model,
            streaming=True
        )
        
        # Get strategy during initialization
        self.strategy = asyncio.run(self.profile_manager.get_strategy())
        logger.info(f"Strategy loaded for context using model: {model}")
        
        self.graph = self._build_graph()
        logger.info("CapabilityAgent initialized with graph built.")
        
    def _build_graph(self):
        logger.info("Building the capability agent graph.")
        graph = StateGraph(MessagesState)
        
        # Define tools using ProfileManager's comprehensive methods
        tools = [
            Tool(
                name="get_all_capabilities",
                func=self._wrap_async(lambda _: self.profile_manager.get_capabilities()),
                description="Returns a complete list of all capabilities with full details including name, category, level, experience, and examples. No arguments needed."
            ),
            Tool(
                name="get_capabilities_by_category",
                func=self._wrap_async(self.profile_manager.get_capabilities_by_category),
                description="""Returns capabilities filtered by category. 
Arguments: 
- category (str): One of 'Hard Skills', 'Soft Skills', 'Domain Knowledge', 'Tools/Platforms'
Example: get_capabilities_by_category('Hard Skills')"""
            ),
            Tool(
                name="get_capabilities_by_level",
                func=self._wrap_async(self.profile_manager.get_capabilities_by_level),
                description="""Returns capabilities filtered by expertise level. 
Arguments:
- level (str): One of 'Expert', 'Advanced', 'Intermediate', 'Basic'
Example: get_capabilities_by_level('Expert')"""
            ),
            Tool(
                name="get_top_capabilities",
                func=self._wrap_async(lambda limit=5: self.profile_manager.get_top_capabilities(limit)),
                description="""Returns top capabilities (Expert/Advanced levels), sorted by expertise level. 
Arguments:
- limit (int, optional): Maximum number of capabilities to return. Default is 5.
Example: get_top_capabilities(3) or get_top_capabilities()"""
            ),
            Tool(
                name="search_capabilities",
                func=self._wrap_async(lambda query: self.profile_manager.search_capabilities(query)),
                description="""Performs semantic search across capabilities, returning relevant matches with similarity scores. 
Arguments:
- query (str): Search term or phrase to match against capabilities
Example: search_capabilities('python development') or search_capabilities('team leadership')"""
            ),
            Tool(
                name="match_requirements",
                func=self._wrap_async(lambda reqs: self.profile_manager.match_requirements(reqs.split(','))),
                description="""Matches requirements against capabilities, providing detailed matching analysis. 
Arguments:
- reqs (str): Comma-separated list of required skills or competencies
Returns: Dictionary with matched skills, partial matches, missing skills, and overall match score
Example: match_requirements('Python,AWS,Team Leadership')"""
            ),
            Tool(
                name="get_expertise_distribution",
                func=self._wrap_async(lambda _: self.profile_manager.get_expertise_distribution()),
                description="""Returns distribution of capabilities across expertise levels (Expert, Advanced, Intermediate, Basic).
No arguments needed. Returns a dictionary with capabilities grouped by level."""
            ),
            Tool(
                name="find_related_capabilities",
                func=self._wrap_async(self.profile_manager.find_related_capabilities),
                description="""Finds capabilities semantically related to a given capability. 
Arguments:
- capability_name (str): Name of the capability to find relations for
Returns: List of related capabilities with similarity scores
Example: find_related_capabilities('Python') might return related programming skills"""
            ),
            Tool(
                name="generate_skill_summary",
                func=self._wrap_async(lambda format='brief': self.profile_manager.generate_skill_summary(format)),
                description="""Generates capability summary in specified format. 
Arguments:
- format (str): One of:
  * 'brief': Quick overview of top skills
  * 'detailed': Comprehensive breakdown by category
  * 'technical': Focus on technical skills and tools
  * 'business': Focus on soft skills and domain knowledge
Example: generate_skill_summary('technical') or generate_skill_summary('brief')"""
            )
        ]

        # Create the agent with enhanced system prompt including strategy
        agent = create_openai_functions_agent(
            llm=self.llm,
            tools=tools,
            prompt=ChatPromptTemplate.from_messages([
                SystemMessage(content=f"""You are an AI assistant specialized in answering questions about Nerijus's professional capabilities.
You have access to comprehensive tools to explore and analyze skills, expertise levels, and professional competencies.

Core Strategy and Context:
<strategy>                              
{self.strategy['content']}
</strategy>

Key guidelines:
- Use get_all_capabilities for complete overview
- Use category/level filters for specific queries (get_capabilities_by_category, get_capabilities_by_level)
- Use get_top_capabilities to focus on Expert/Advanced skills
- Use search_capabilities for semantic search
- Use match_requirements for skill gap analysis
- Use expertise_distribution for level insights
- Use generate_skill_summary for different perspectives (brief/detailed/technical/business)
- Use find_related_capabilities to explore skill relationships
- Use get_expertise_distribution for detailed level breakdown
                              
If you don't find specific information about a capability, clearly state that it's not documented.

Respond in a clear, professional manner and cite specific data from the tools."""),
                MessagesPlaceholder(variable_name="messages"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
        )
        
        # Create the agent executor
        agent_executor = AgentExecutor(agent=agent, tools=tools)
        
        def chatbot(state: MessagesState):
            """Main chatbot node that processes messages"""
            messages = state["messages"]
            logger.debug(f"Processing messages: {messages}")
            
            input_message = messages[-1] if messages else None
            if isinstance(input_message, tuple) and input_message[0] == "user":
                user_message = input_message[1]
                logger.debug(f"Handling user input: {user_message}")
            elif isinstance(input_message, HumanMessage):
                user_message = input_message.content
                logger.debug(f"Handling HumanMessage: {user_message}")
            else:
                logger.warning(f"Unexpected message format: {input_message}")
                user_message = None

            if user_message:
                response = agent_executor.invoke({"messages": messages})
                logger.debug(f"Generated response: {response}")
                messages.append(("assistant", response["output"]))
                
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
                return loop.run_until_complete(
                    asyncio.wait_for(coro(*args, **kwargs), timeout=30.0)
                )
            except asyncio.TimeoutError:
                logger.error("Operation timed out")
                return "Operation timed out. Please try again."
            except Exception as e:
                logger.error(f"Tool execution error: {str(e)}")
                return f"Error executing tool: {str(e)}"
        return wrapper

    @traceable
    async def chat(self, message: str, timeout: Optional[float] = 30.0) -> str:
        """
        Process a message through the graph and return response.
        
        Args:
            message: The user's input message
            
        Returns:
            str: The agent's response
            
        Raises:
            Exception: If there's an error processing the message
        """
        logger.info(f"Received message: {message}")
        try:
            response = await asyncio.wait_for(
                self.graph.ainvoke({"messages": [("user", message)]}),
                timeout=timeout
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
        except asyncio.TimeoutError:
            logger.error("Operation timed out")
            return "Operation timed out. Please try again."
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return f"Error processing message: {str(e)}"

    async def shutdown(self):
        """Gracefully shutdown the agent and cleanup resources"""
        try:
            # Cleanup any active sessions
            if hasattr(self.llm, 'aclose'):
                await self.llm.aclose()
            # Cleanup profile manager resources
            await self.profile_manager.cleanup()
            logger.info("CapabilityAgent shutdown completed")
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")
