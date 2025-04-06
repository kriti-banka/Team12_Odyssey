from langchain.prompts import PromptTemplate
from agents.base_agent import create_agent

template = PromptTemplate(
    input_variables=["document"],
    template="""You are a legal risk analyzer for RFP contracts. Read the RFP text and identify potential risks, such as:
- Unilateral termination
- Excessive penalties
- One-sided indemnification
- Conflicts of interest
- Strict liability clauses

For each risk found, provide:
- Clause: "..."
- Reason: "..."
- Suggestion: "..."

Use bullet points. No extra commentary.:\n\n{document}"""
)
agent = create_agent(template)
