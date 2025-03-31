from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

def create_metadata_agent():
    """Create an agent to generate the metadata section of the MCP YAML file."""
    system_message = """You are an expert at creating metadata for MCP modules.
    Your task is to extract basic metadata information from repository analysis and generate the metadata section of an MCP YAML file.

    When saying the company domain, use the company website or documentation referenced by the MCP module.
    
    Focus ONLY on generating these basic metadata fields:
    - name (technical identifier without spaces)
    - displayName (human-readable name)
    - description (concise explanation, 1-2 sentences maximum)
    - longDescription (detailed explanation about the module's purpose and functionality)
    - siteUrl: URL to the product's official page (e.g. https://product.com)
    - icon: URL to the product's logo (e.g. https://img.logo.dev/product.domain)
    - categories (list of relevant categories for the module)
    - version (semantic version, usually 1.0.0)
    
    Base your metadata on the provided analysis and make sure all fields are properly formatted according to YAML standards.

    The output should be a valid YAML object, looking like this:
    name: <name>
    displayName: <displayName>
    description: <description>
    longDescription: <longDescription>
    siteUrl: <siteUrl>
    icon: <icon>
    categories: <categories>
    version: <version>
    """
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", "Generate the metadata section for an MCP module based on this analysis:\n\n"
                "Module name: {name}\n"
                "Repository: {repository_url}\n"
                "Branch: {branch}\n\n"
                "Analysis:\n{analysis}\n\n"
                "Please generate ONLY the metadata section of the YAML file with proper formatting.")
    ])
    
    chain = prompt | llm | StrOutputParser()
    return chain 