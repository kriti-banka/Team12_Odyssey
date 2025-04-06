from langchain.prompts import PromptTemplate
from agents.base_agent import create_agent

template = PromptTemplate(
    input_variables=["document"],
    template="""You are an expert at summarizing government RFPs. Read the text below and produce a concise summary:
- Highlight the main scope or purpose of the RFP.
- Identify key objectives and any critical deadlines or instructions.
- Do not exceed 250 words.:\n\n{document}"""
)
agent = create_agent(template)
