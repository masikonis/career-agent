from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState, StateGraph
from langsmith import traceable
import asyncio
from typing import Any, Callable, Optional
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import StructuredTool, Tool
from src.config import config
from src.profile.manager import ProfileManager
from src.utils.logger import get_logger

logger = get_logger(__name__)

class CapabilityAgent:
    """Agent that understands and can discuss capabilities using a graph-based approach"""
    
    def __init__(self, profile_manager: ProfileManager, llm=None, model_name=None):
        if not isinstance(profile_manager, ProfileManager):
            raise ValueError("profile_manager must be an instance of ProfileManager")
        
        self.profile_manager = profile_manager
        
        if model_name and model_name not in config['LLM_MODELS'].values():
            raise ValueError(f"Invalid model_name. Must be one of: {list(config['LLM_MODELS'].values())}")
        
        model = model_name or config['LLM_MODELS']['basic']
        self.llm = llm or ChatOpenAI(
            temperature=0,
            model=model,
            streaming=True
        )
        
        self.strategy = asyncio.run(self.profile_manager.get_strategy())
        logger.info(f"Strategy loaded for context using model: {model}")
        
        self.graph = self._build_graph()
        self.message_history = []
        logger.info("CapabilityAgent initialized with graph built and empty message history.")
        
    def _build_graph(self):
        logger.info("Building the capability agent graph.")
        graph = StateGraph(MessagesState)
        
        # Define tools using ProfileManager's comprehensive methods
        tools = [
            StructuredTool(
                name="get_all_capabilities",
                func=lambda: {"capabilities": self._wrap_async(self.profile_manager.get_capabilities)()},
                description="Returns a complete list of all capabilities with full details including name, category, level, experience, and examples. DO NOT pass any arguments to this tool - it takes no parameters.",
                return_direct=False,
                args_schema=None,
                coroutine=None,
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

IMPORTANT RULES:
- You MUST use at least one tool for EVERY response. If unsure which tool to use, use get_all_capabilities.
- You are not allowed to use any other tools than the ones provided.
- You are not allowed to use any other sources of information than the ones provided.
- If you don't find specific information about a capability, clearly state that I don't have that capability.
- Present my capabilities in first person, as if I am telling my story in an interview.
- Never make assumptions about capabilities without verifying through tools.
- Always reference the specific data retrieved from tools in your response.
- Strictly answer only what is asked - do not provide advice or suggestions for improvement.
- Focus on factual assessment of current capabilities only.

Respond in a clear, professional manner and cite specific data from the tools, if applicable based on the query.

Remember: ALWAYS use at least one tool before responding, even for seemingly simple questions."""),
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
        """Process a message through the graph and return response."""
        logger.info(f"Received message: {message}")
        try:
            # Include message history in the graph invocation
            if isinstance(message, str):
                self.message_history.append(("user", message))
            else:
                self.message_history.append(("user", message.content))

            response = await asyncio.wait_for(
                self.graph.ainvoke({"messages": self.message_history}),
                timeout=timeout
            )
            
            # Extract and store the response
            last_message = response["messages"][-1]
            if hasattr(last_message, 'content'):
                response_content = last_message.content
            elif isinstance(last_message, tuple):
                response_content = last_message[1]
            else:
                response_content = str(last_message)
                
            # Add response to history
            self.message_history.append(("assistant", response_content))
            logger.info(f"Response generated and added to history: {response_content}")
            
            return response_content
            
        except asyncio.TimeoutError:
            logger.error("Operation timed out")
            return "Operation timed out. Please try again."
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return f"Error processing message: {str(e)}"

    async def clear_history(self):
        """Clear the conversation history"""
        self.message_history = []
        logger.info("Conversation history cleared")
        return True
