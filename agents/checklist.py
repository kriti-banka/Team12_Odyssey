from langchain.prompts import PromptTemplate
from agents.base_agent import create_agent

template = PromptTemplate(
    input_variables=["document"],
    template="""You are an RFP submission checklist generator. Analyze the following RFP and extract a detailed checklist
of all submission requirements, including document format (e.g., page limits, font type/size, line spacing),
required attachments or forms, table of contents requirements, and any other specific instructions.:\n\n{document}"""
)
agent = create_agent(template)
