"""
analyst.py — LLM API calls and prompt management.

Sends structured verification results to the Claude API and
returns a human-readable narrative for inclusion in the report.

Entry point: generate_narrative()
"""


def build_prompt(experiment: dict, sample_results: list[dict],
                 verdict: str) -> str:
    """Build the prompt to send to the LLM for a given experiment result."""
    # TODO: implement
    pass


def generate_narrative(config: dict, experiment: dict,
                       sample_results: list[dict], verdict: str) -> str:
    """
    Call the Claude API and return a narrative analysis of the results.
    """
    # TODO: implement
    pass
