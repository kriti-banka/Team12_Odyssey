from langchain.prompts import PromptTemplate
from agents.base_agent import create_agent

template = PromptTemplate(
    input_variables=["document"],
    template="""EYou are an expert RFP requirement extractor. Carefully analyze the RFP text below:
    - Even if the RFP says “All contractors must enroll in E-Verify,” treat E-Verify requirements as "preferred," 
    unless it explicitly says proposals will be disqualified without it.

    Output:
    1. Valid JSON array only.
    2. Each object: "requirement": short text, "type": "must_have" or "preferred."

    Example:
    [
    {{"requirement": "E-Verify affidavit", "type": "preferred"}},
    {{"requirement": "Signed Non-Collusion Affidavit", "type": "must_have"}}
    ]
:\n\n{document}"""
)
agent = create_agent(template)
