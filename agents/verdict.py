from langchain.prompts import PromptTemplate
from agents.base_agent import create_agent
from utility.fileparser import load_json
import json

# Load and escape company data
company_data = load_json("json/company_data.json")
company_data_str = json.dumps(company_data, indent=2)
escaped_company_json = company_data_str.replace("{", "{{").replace("}", "}}")

# Prompt template with natural explanation and math
template = PromptTemplate(
    input_variables=["document"],
    template=f"""
You are an expert in government RFP eligibility evaluation. You will receive two inputs:

1. The full RFP content (unstructured text)  
2. The company profile (already embedded below)

---

### RFP Document:
{{document}}

### Company Profile:
{escaped_company_json}

---

### Your Task:
1. Carefully read the RFP and extract **all eligibility-related requirements**.
2. Organize them into two categories:
   - 📌 **Mandatory Requirements**: absolutely required for eligibility.
   - 📝 **Optional Requirements**: preferred, but not essential.
3. Compare these with the company profile and determine:
   - Which mandatory requirements are **met**
   - Which optional requirements are **met**
   - Which mandatory requirements are **missing**
4. If any requirements are **conditional or irrelevant**, you may ignore them — explain why in reasoning.
5. Do **not count** conditional requirements that do not apply to this company as missing.
6. Use **logical judgment** to determine eligibility score and final verdict.

---

### Final Output Format (JSON only — no extra text):
```json
{{{{ 
  "eligible": true or false,
  "verdict": "Highly Eligible | Moderately Eligible | Not Eligible",
  "reasoning": "Short explanation of why",
  "mandatory_requirements": [...],
  "optional_requirements": [...],
  "met_mandatory": [...],
  "met_optional": [...],
  "missing_mandatory": [...]
}}}}
"""
)

agent = create_agent(template)



