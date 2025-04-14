"""
Base Agent Module

This module provides the base agent class for all MCP agents to inherit from,
ensuring a consistent interface and shared functionality across all agents.
"""

from typing import Any, Callable, Dict, List, Optional, Union

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel


class BaseAgent:
    """Base agent class that all MCP agents inherit from."""

    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        temperature: float = 0,
        structured_output_class: Optional[BaseModel] = None
    ):
        """Initialize the base agent.

        Args:
            model_name: The OpenAI model to use
            temperature: Temperature setting for the model
            structured_output_class: Optional Pydantic model for structured output
        """
        self.model_name = model_name
        self.temperature = temperature
        self.structured_output_class = structured_output_class

        # Create a standard LLM for basic chains
        self.llm = ChatOpenAI(model_name=model_name, temperature=temperature)

        # If structured output class is provided, create a separate LLM for structured output
        if structured_output_class:
            self.structured_llm = ChatOpenAI(model_name=model_name, temperature=temperature)
            # Use function_calling explicitly as the method, which is more reliable
            self.structured_llm = self.structured_llm.with_structured_output(
                structured_output_class,
                method="function_calling"  # Explicitly use function_calling instead of the default
            )
        else:
            self.structured_llm = None

        # Create a separate LLM for tools/agents to avoid conflicts
        self.tools_llm = ChatOpenAI(model_name=model_name, temperature=temperature)

    def setup_chain(self, system_message: str, human_message_template: str) -> Callable:
        """Set up a basic chain with system and human message templates.

        Args:
            system_message: The system message to use
            human_message_template: The human message template with variables

        Returns:
            A callable chain function
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_message_template)
        ])

        # Use either the structured LLM or the standard LLM
        if self.structured_llm:
            # For structured output, don't use StrOutputParser
            chain = prompt | self.structured_llm
        else:
            # For non-structured output, use the standard LLM with StrOutputParser
            chain = prompt | self.llm | StrOutputParser()

        return chain

    def setup_agent_with_tools(
        self,
        system_message: str,
        human_message_template: str,
        tools: List[Tool]
    ) -> AgentExecutor:
        """Set up an agent with tools.

        Args:
            system_message: The system message to use
            human_message_template: The human message template with variables
            tools: List of tools for the agent to use

        Returns:
            An AgentExecutor instance
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_message_template),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])

        # Always use the tools-specific LLM for agents to avoid conflicts
        agent = create_openai_functions_agent(self.tools_llm, tools, prompt)
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=15
        )

        return executor

    async def ainvoke(self, inputs: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
        """Asynchronously invoke the agent with the given inputs.

        This method should be overridden by child classes.

        Args:
            inputs: Dictionary of inputs for the agent

        Returns:
            The agent's response as either a string or dictionary
        """
        if hasattr(self, 'chain'):
            response = await self.chain.ainvoke(inputs)

            # Handle structured output
            if self.structured_output_class:
                # If we directly got a structured output class instance back
                if isinstance(response, self.structured_output_class):
                    return response

                # If we got a Message object with content
                if hasattr(response, 'content'):
                    content = response.content
                else:
                    content = response

                # If the content is a structured output class instance
                if isinstance(content, self.structured_output_class):
                    return content

                # If we got a dictionary back
                if isinstance(content, dict):
                    try:
                        # Try to create a structured output instance from the dictionary
                        return self.structured_output_class(**content)
                    except Exception as e:
                        # If that fails but it contains a key matching the class name or the simplified class name
                        class_name = self.structured_output_class.__name__
                        simple_name = class_name.replace("Response", "").lower()

                        if class_name in content:
                            return self.structured_output_class(**content[class_name])
                        elif simple_name in content:
                            return self.structured_output_class(**content[simple_name])
                        # Otherwise return the raw dictionary
                        return content

                # We got a string back - try to parse it
                if isinstance(content, str):
                    try:
                        # If it's YAML formatted, parse it
                        import re

                        import yaml

                        # Try to parse as YAML
                        yaml_data = yaml.safe_load(content)

                        # If it's a dictionary, try to convert to structured output
                        if isinstance(yaml_data, dict):
                            # Check if it has a key matching the class name or simplified class name
                            class_name = self.structured_output_class.__name__
                            simple_name = class_name.replace("Response", "").lower()

                            if class_name in yaml_data:
                                return self.structured_output_class(**yaml_data[class_name])
                            elif simple_name in yaml_data:
                                return self.structured_output_class(**yaml_data[simple_name])
                            else:
                                # Otherwise assume the whole dict is the structured data
                                return self.structured_output_class(**yaml_data)
                    except Exception as e:
                        # If parsing fails, return the content as is
                        return content

                # If we get here, we couldn't parse or convert the response, return it as is
                return response

            return response
        elif hasattr(self, 'agent'):
            return await self.agent.ainvoke(inputs)
        else:
            raise NotImplementedError("Child agents must implement ainvoke method or have chain/agent attribute")

    def invoke(self, inputs: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
        """Synchronously invoke the agent with the given inputs.

        This method should be overridden by child classes.

        Args:
            inputs: Dictionary of inputs for the agent

        Returns:
            The agent's response as either a string or dictionary
        """
        # For consistency, use the async implementation through an event loop
        import asyncio

        # Create an event loop if one doesn't exist
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the async method
        return loop.run_until_complete(self.ainvoke(inputs))