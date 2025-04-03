"""
Build Agent Module

This module provides an agent for generating the build section of MCP YAML files.
"""

from typing import Dict, Any, Union, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.agents import AgentExecutor, create_openai_tools_agent

from .base_agent import BaseAgent
from langchain_community.tools.file_management import ReadFileTool, ListDirectoryTool

class BuildResponse(BaseModel):
    """Structured response for build section."""
    language: Optional[str] = Field(
        description="Programming language used for the project",
        default=None
    )
    command: Optional[str] = Field(
        description="Command to build the project",
        default=None
    )
    output: Optional[str] = Field(
        description="Output directory of the build",
        default=None
    )
    # Add other build options as needed


class BuildAgent(BaseAgent):
    """Agent for generating the build section of an MCP YAML file."""
    
    def __init__(self):
        """Initialize the build agent."""
        super().__init__(structured_output_class=BuildResponse)

        # Define tools with repo_path context
        self.read_file_tool = ReadFileTool()
        self.list_directory_tool = ListDirectoryTool()
        
        self.tools = [
            Tool(
                name="ReadFile",
                description="Read a file from the repository to analyze its content. Use this to inspect key files like tsconfig.json, package.json, webpack.config.js, etc.",
                func=self.read_file_tool.run
            ),
            Tool(
                name="ListDirectory",
                description="List contents of a repository directory to discover important build configuration files.",
                func=self.list_directory_tool.run
            ),
        ]
        
        # Define the system and human messages for the agent
        self.system_message = """You are an expert at defining build configurations for MCP modules.
        Your task is to extract build information from the provided analysis and generate the build section of an MCP YAML file.
        
        You have access to the following tools:
        1. ReadFile - Use this to read configuration files like tsconfig.json, package.json, webpack.config.js, etc.
        2. ListDirectory - Use this to discover important files in the repository.
        
        FIRST, you should use ListDirectory on the repository path to identify important build configuration files.
        THEN, use ReadFile to examine those files for build information.
        
        Focus on generating the build section with these fields:
        
        - language: Programming language used for the project (e.g., typescript, javascript)
        - command: Command to build the project (e.g., npm run build, yarn build, npx tsc)
        - output: Output directory of the build (e.g., dist, build, out, etc.)
        
        ## Finding Build Information
        You should infer the appropriate build configuration based on:
        1. The structure of the codebase (languages used, build tools present)
        2. Any build instructions or requirements found in the repository. You can use the ReadFile tool to find these in README.md, package.json, etc.
        3. Package manager configuration files like package.json
        4. For TypeScript projects, ALWAYS check tsconfig.json for the "outDir" property
        
        The output should be a valid YAML object for the build section, looking like:
        
        build:
          language: <language>
          command: <build command>
          output: <output directory>
        
        ## TypeScript Projects
        For TypeScript projects, follow these strict guidelines:
        
        1. ALWAYS check tsconfig.json first and use the "outDir" property as the output directory
        2. Remove any "./" prefix from the output path (e.g., "./dist" should be "dist")
        3. If tsconfig.json isn't available, look at package.json scripts and infer the output directory
        4. When determining the build command, check if there's a build script in package.json
        5. If there's no build script, use the "tsc" command to build the project
        6. For monorepos, check if there's a workspace-specific build command
        7. For projects that might have TypeScript type declaration issues, modify the build command to handle missing type declarations:
           - Add `|| true` to the end of tsc commands to prevent build failures from missing types, e.g., `npx tsc || true`
           - Alternatively, use `"npx tsc --skipLibCheck"` to skip checking declaration files
           - For critical type issues that need fixing, check if the project has a postinstall script to install types
        
        ## Example 1 - Basic TypeScript with tsc:
        If package.json contains:
        ```
        {{
          "name": "my-typescript-app",
          "scripts": {{
            "build": "tsc",
            "start": "node dist/index.js"
          }},
          "devDependencies": {{
            "typescript": "^4.9.5"
          }}
        }}
        ```
        
        And tsconfig.json contains:
        ```
        {{
          "compilerOptions": {{
            "outDir": "./dist"
          }}
        }}
        ```
        
        The build section should be:
        ```
        build:
          language: typescript
          command: npm run build
          output: dist
        ```
        
        ## Example 2 - TypeScript with custom bundler:
        If package.json contains:
        ```
        {{
          "name": "my-nextjs-app",
          "scripts": {{
            "build": "next build",
            "export": "next export"
          }},
          "dependencies": {{
            "next": "^12.0.0",
            "react": "^17.0.2"
          }},
          "devDependencies": {{
            "typescript": "^4.5.4"
          }}
        }}
        ```
        
        And tsconfig.json contains:
        ```
        {{
          "compilerOptions": {{
            "outDir": "./build"
          }}
        }}
        ```
        
        The build section should be:
        ```
        build:
          language: typescript
          command: npm run build
          output: build
        ```
        
        ## Example 3 - TypeScript with Webpack:
        If webpack.config.js contains:
        ```
        module.exports = {{
          output: {{
            path: path.resolve(__dirname, 'public/assets'),
          }}
        }}
        ```
        
        But tsconfig.json contains:
        ```
        {{
          "compilerOptions": {{
            "outDir": "./build"
          }}
        }}
        ```
        
        The build section should be:
        ```
        build:
          language: typescript
          command: npm run build
          output: build
        ```

        ## Example 4 - TypeScript with no build script
        If package.json contains:
        ```
        {{
          "name": "my-typescript-app",
        }}
        ```

        The build section should be:
        ```
        build:
          language: typescript
          command: echo 'declare module \"marklogic\";' > src/types.d.ts && npx tsc
          output: dist
        ```
        
        ## Example 5 - TypeScript with missing type declarations
        If you encounter TypeScript modules missing type declarations (error TS7016), use:
        ```
        build:
          language: typescript
          command: echo 'declare module \"marklogic\";' > src/types.d.ts && npx tsc
          output: dist
        ```
        
        This command creates a declaration file before compiling to avoid TypeScript build failures.

        ## Example 6 - TypeScript in Docker build context with declaration issues
        If you encounter TypeScript modules missing type declarations in a Docker build context:
        ```
        build:
          language: typescript
          command: /bin/sh -c 'mkdir -p src/types && echo "declare module \"*\";" > src/types/global.d.ts && npx tsc'
          output: dist
        ```
        
        This ensures the command works in a shell context and continues even if there are errors.
        
        ## JavaScript/TypeScript Projects without Build Scripts
        For projects without explicit build scripts, follow these guidelines:
        
        1. FIRST, identify whether the project is using TypeScript or JavaScript by examining file extensions and configurations
        2. THEN, determine the appropriate default build command based on the identified frameworks and tools
        3. FINALLY, infer the output directory based on conventions or file system analysis
        
        ### JavaScript/TypeScript Projects without Build Scripts:
        - If using TypeScript without a build script in package.json: use `npx tsc --skipLibCheck` or create declaration files
        - If using JavaScript with Webpack present but no build script: use `npx webpack` command
        - If using JavaScript with Vite present but no build script: use `npx vite build` command with "dist" output
        - If using JavaScript with Parcel present but no build script: use `npx parcel build src/index.html` with "dist" output
        - If using React without a build script: use `npx react-scripts build` with "build" output
        - If using Vue without a build script: use `npx vue-cli-service build` with "dist" output
        - If using Next.js without a build script: use `npx next build` with ".next" output
        - If using Nuxt without a build script: use `npx nuxt build` with ".nuxt" output
        - If using Angular without a build script: use `npx ng build` with "dist" output
        
        ## Handling TypeScript Type Declaration Issues
        When TypeScript projects have missing type declaration files, use one of these approaches:
        
        1. Create declaration files directly as part of the build command:
           ```
           command: mkdir -p src/types && echo 'declare module "marklogic";' > src/types/global.d.ts && npx tsc
           ```
           
        2. Use the noImplicitAny flag to allow modules without types:
           ```
           command: npx tsc --noImplicitAny
           ```
        
        3. For Docker build environments, use shell scripting to handle potential failures:
           ```
           command: /bin/sh -c 'mkdir -p src/types && echo "declare module \"*\";" > src/types/global.d.ts && npx tsc'
           ```
           
        4. When specific modules are causing issues, create targeted declaration files:
           ```
           command: /bin/sh -c 'for module in marklogic other-module; do mkdir -p src/types && echo "declare module \"$module\";" >> src/types/global.d.ts; done && npx tsc'
           ```
           
        5. As a last resort, suppress the exit code to prevent build failures:
           ```
           command: npx tsc || true
           ```
           Or:
           ```
           command: npx tsc || exit 0
           ```

        ## JavaScript-Specific Bundling Options
        For JavaScript projects using modern bundlers:
        
        1. Webpack:
           ```
           command: npx webpack --mode production
           output: dist
           ```
        
        2. Rollup:
           ```
           command: npx rollup -c
           output: dist
           ```
        
        3. Vite:
           ```
           command: npx vite build
           output: dist
           ```
        
        4. Parcel:
           ```
           command: npx parcel build src/index.html
           output: dist
           ```
        
        5. esbuild:
           ```
           command: npx esbuild src/index.js --bundle --minify --outdir=dist
           output: dist
           ```
        
        ## Framework-Specific Build Commands
        For JavaScript/TypeScript projects using popular frameworks:
        
        1. React (Create React App):
           ```
           command: npm run build
           output: build
           ```
        
        2. Next.js:
           ```
           command: npm run build
           output: .next
           ```
        
        3. Vue:
           ```
           command: npm run build
           output: dist
           ```
        
        4. Angular:
           ```
           command: npm run build
           output: dist
           ```
        
        5. Svelte:
           ```
           command: npm run build
           output: public/build
           ```
        
        ## Important Rules
        1. TYPESCRIPT PROJECTS: ALWAYS prioritize the "outDir" setting in tsconfig.json for determining the output directory.
        2. NEVER include the "./" prefix in the output path.
        3. Only use the build field's "path" property if the build must happen in a specific subdirectory.
        4. Make sure the command actually builds the project, not just installs dependencies.
        5. For TypeScript projects, the language should ALWAYS be set to "typescript" (not javascript).
        6. Look for common directory patterns in the repository to infer build outputs when config files don't specify them.
        7. For projects with multiple potential build systems, prioritize based on which appears to be the primary one.
        8. If a project uses specific build tools like esbuild, rollup, etc., use their appropriate commands with default outputs.
        9. For TypeScript projects with type declaration issues, use explicit declaration file creation rather than just relying on --skipLibCheck.
        10. In Docker build contexts, ensure commands are properly escaped and shell-compatible.
        11. Avoid guessing - if you can't find a value, explain your reasoning.
        
        Make sure to provide accurate values based on the repository analysis and files you've examined.
        """
        
        self.human_message_template = """Generate the build section for an MCP module based on this analysis:

        Repository: {repository_url}
        Repo Path: {repo_path}

        Analysis:
        {analysis}

        Please explore the repository at path {repo_path} using the provided tools to find detailed build configuration information, then generate ONLY the build section of the YAML file with proper formatting."""
    
    def initialize_agent(self):
        """Initialize the agent with the chain."""
        if not self.llm:
            raise ValueError("LLM must be set before initializing the agent")
            
        # Create a prompt that includes tool usage instructions
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=self.system_message),
            # Remove the chat_history placeholder since it's not being provided
            HumanMessage(content=self.human_message_template),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create an agent that can use tools
        agent = create_openai_tools_agent(
            self.llm,
            self.tools,
            prompt
        )
        
        # Create an executor for the agent
        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=agent,
            tools=self.tools,
            verbose=True,
            return_intermediate_steps=True,
            handle_parsing_errors=True
        )
        
        # Set up the chain with structured output
        self.chain = self.setup_structured_output_chain(
            self.agent_executor,
            self.structured_output_class
        )

    async def ainvoke(self, inputs: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
        """Asynchronously invoke the build agent.
        
        Args:
            inputs: Dictionary with keys:
                - repository_url: Repository URL
                - repo_path: Path to repository on disk
                - analysis: Repository analysis
                
        Returns:
            The build section as structured output (BuildResponse)
        """
        try:
            # Create an agent with the formatted human message template
            # Format the human message with the actual repo_path
            formatted_human_message = self.human_message_template.format(
                repository_url=inputs.get("repository_url", ""),
                repo_path=inputs.get("repo_path", ""),
                analysis=inputs.get("analysis", "")
            )
            
            # Create a new prompt with the formatted human message
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=self.system_message),
                HumanMessage(content=formatted_human_message),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
            
            # Create a new agent with the formatted prompt
            agent = create_openai_tools_agent(
                self.llm,
                self.tools,
                prompt
            )
            
            # Create a new executor for this invocation
            agent_executor = AgentExecutor.from_agent_and_tools(
                agent=agent,
                tools=self.tools,
                verbose=True,
                return_intermediate_steps=True,
                handle_parsing_errors=True
            )
            
            # Set up the chain with structured output
            formatted_chain = self.setup_structured_output_chain(
                agent_executor,
                self.structured_output_class
            )
            
            # Call the chain with just the repo_path
            # We've already formatted the human message with all the inputs
            response = await formatted_chain.ainvoke({})
            return response
        except Exception as e:
            print(f"Error in BuildAgent.ainvoke: {str(e)}")
            # Return a minimal valid response with error information
            return {"build": {
                "language": "unknown",
                "command": "echo 'Error during build analysis'",
                "output": ".",
                "error": str(e)
            }}
    
    def invoke(self, inputs: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
        """Synchronously invoke the build agent.
        
        Args:
            inputs: Dictionary with keys:
                - repository_url: Repository URL
                - repo_path: Path to repository on disk
                - analysis: Repository analysis
                
        Returns:
            The build section as structured output (BuildResponse)
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
        
    def setup_structured_output_chain(self, agent_executor, output_class):
        """Set up a chain that returns structured output for an agent executor."""
        from langchain_core.runnables import RunnableLambda
        
        # Create a function to parse the agent output into structured format
        def parse_agent_output(agent_result):
            return agent_result["output"]
        
        # Set up the chain with structured output
        chain = agent_executor | RunnableLambda(parse_agent_output)
        
        # Create a chain to convert the output to the structured_output_class
        def format_to_pydantic(output_text):
            """Convert output text to a Pydantic model instance."""
            import json
            import re
            
            # Try to extract JSON from the output if it's not already valid JSON
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', output_text)
            if json_match:
                json_str = json_match.group(1)
                try:
                    parsed_data = json.loads(json_str)
                    # Check if we have a build section or direct fields
                    if "build" in parsed_data:
                        return parsed_data
                    else:
                        return {"build": parsed_data}
                except:
                    pass
            
            # If it's already valid JSON, use it directly
            try:
                parsed_data = json.loads(output_text)
                if "build" in parsed_data:
                    return parsed_data
                else:
                    return {"build": parsed_data}
            except:
                pass
                
            # If we can't parse to JSON, try to extract key-value pairs
            # This is a fallback for non-JSON outputs
            result = {}
            for line in output_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    if key in ['language', 'command', 'output']:
                        result[key] = value
                        
            return {"build": result}
        
        return chain | RunnableLambda(format_to_pydantic)


def create_build_agent(model_name: str = "gpt-4o-mini", temperature: float = 0) -> BuildAgent:
    """Create a build agent instance.
    
    This function maintains backward compatibility with the original implementation.
    
    Args:
        model_name: The OpenAI model to use
        temperature: Temperature setting for the model
        
    Returns:
        BuildAgent instance
    """
    build_agent = BuildAgent()
    
    # Set the model name and temperature
    build_agent.llm = ChatOpenAI(
        model_name=model_name,
        temperature=temperature
    )
    
    # Initialize the agent
    build_agent.initialize_agent()
    
    return build_agent