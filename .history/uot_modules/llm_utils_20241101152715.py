from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_fireworks import ChatFireworks
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import List, Callable
from enum import Enum
from langchain_core.runnables.base import RunnableSequence

from .tasks.prompts.dementia_support import *

from dotenv import load_dotenv
load_dotenv()

class _EvaluationProbabilityOfYes(BaseModel):
    name: str = Field(..., description="The name of the item. You cannot change the name. (in Japanese)")
    description: str = Field(..., description="The description of the item. You cannot change the description. (in Japanese)")
    thought: str = Field(..., description=evaluate_probabilities_of_chunk_discription) # CoT
    y_prob : float = Field(..., description="The probability of the item being yes. y_prob must be between 0 and 1. Around 0.5 means not related, both, or difficult. Please set the number as detailed as possible. (in English)")

class _EvaluationProbabilityOfYesResult(BaseModel):
    question: str = Field(..., description="The question posed for evaluation of probability of yes option of situation with the item.")
    items: List[_EvaluationProbabilityOfYes] = Field(..., description="The list of evaluated items.")

class _GenerateQuestionsItem(BaseModel):
    number : int = Field(..., description="The number of questions generated. This is from 1 to size n.")
    thoughts: str = Field(..., description=generate_questions_thought_discription) # CoT
    question: str = Field(..., description=generate_questions_discription)

class _CheckOpenAnswer(BaseModel):
    thoughts: str = Field(..., description=check_open_answer_thought_discription) # CoT
    is_answer_done: bool = Field(..., description="Whether the answer is done or not. If the answer is done, set True. If the answer is not done, set False.")
    observed_prob_of_yes: float = Field(..., description="The probability of the answer being correct. This must be between 0 and 1. Around 0.5 means not related, both, or difficult. Please set the number as detailed as possible. (in English)")

class _GenerateQuestionsResult(BaseModel):
    items: List[_GenerateQuestionsItem] = Field(..., description="The list of generated items which include a question with index number and pander result. You must generate from 1 to n (so, len of the list is n)!!!")

class _CheckIsAnsweredToQuestion(BaseModel):
    thoughts: str = Field(..., description=check_is_answered_to_question_discription) # CoT
    is_answered: bool = Field(..., description="Whether the question has been already answered or not. If the question is answered, set True. If the question is not answered, set False. If the response looks on going to answer the question, set False to keep hearing. If looks so much confused, give up and set True.")
    observed_prob_of_yes: float = Field(..., description="The probability of the answer being 'yes'. This must be between 0 and 1. Around 0.5 means not related, both, or difficult. Please set the number as detailed as possible.")

class _CheckIsQuestionExplained(BaseModel):
    thoughts: str = Field(..., description=check_is_question_explained_discription) # CoT
    is_question_explained: bool = Field(..., description="Whether the question or similar question has been asked in the response. If the question has been asked, set True. If the question has not been asked, set False.")

def pydantic_to_dict(obj):
    """
    Recursively converts Pydantic models, Enums, lists, and dictionaries to a standard dictionary format.
    
    Args:
        obj: The object to be converted, which can be a Pydantic model, Enum, list, or dictionary.
    
    Returns:
        A dictionary representation of the input object, with Enums converted to their string values.
    """
    if isinstance(obj, Enum):
        # If the object is an Enum, return its value (usually a string).
        return obj.value
    elif isinstance(obj, BaseModel):
        # If the object is a Pydantic model, convert it to a dictionary.
        # Use a dictionary comprehension to apply pydantic_to_dict to each attribute.
        return {k: pydantic_to_dict(v) for k, v in obj.dict().items()}
    elif isinstance(obj, list):
        # If the object is a list, apply pydantic_to_dict to each item in the list.
        return [pydantic_to_dict(item) for item in obj]
    elif isinstance(obj, dict):
        # If the object is a dictionary, apply pydantic_to_dict to each key-value pair in the dictionary.
        return {k: pydantic_to_dict(v) for k, v in obj.items()}
    else:
        # If the object is any other type, return it as is.
        return obj

# Define the models
gpt_4o_model = ChatOpenAI(model="gpt-4o", max_tokens=4096)
fireworks_llama70b = ChatFireworks(model="accounts/fireworks/models/llama-v3p2-90b-vision-instruct", max_tokens=4096)
claude_3_haiku_model = ChatAnthropic(model="claude-3-haiku-20240307", max_tokens=4096)
claude_3_5_sonnet_model = ChatAnthropic(model="claude-3-5-sonnet-20241022", max_tokens=4096)
fireworks_llama_v3p2_11b = ChatFireworks(model="accounts/fireworks/models/llama-v3p2-11b-vision-instruct", max_tokens=4096)
groq_llama_v3p2_90b = ChatGroq(model="llama-3.2-90b-text-preview", max_tokens=4096)

smart_model = gpt_4o_model
fast_model = fireworks_llama_v3p2_11b
fast_quasi_model = groq_llama_v3p2_90b
quasi_model = claude_3_5_sonnet_model

# Define the prompts and output parsers for the "classify_chunk" usecase
output_parser_evaluate_probabilities_of_chunk = JsonOutputParser(pydantic_object=_EvaluationProbabilityOfYesResult)
prompt_template_evaluate_probabilities_of_chunk = PromptTemplate.from_template(
    evaluate_probabilities_of_chunk_prompt, 
    partial_variables={
            "format_instructions": output_parser_evaluate_probabilities_of_chunk.get_format_instructions()
        },
)

# Define the prompts and output parsers for the "generate_questions" usecase
output_parser_generate_questions = JsonOutputParser(pydantic_object=_GenerateQuestionsResult)
prompt_template_generate_questions = PromptTemplate.from_template(
    generate_questions_prompt, 
    partial_variables={
            "format_instructions": output_parser_generate_questions.get_format_instructions()
        },
)

output_parser_check_open_answer = JsonOutputParser(pydantic_object=_CheckOpenAnswer)
prompt_template_check_open_answer = PromptTemplate.from_template(
    check_open_answer_prompt,
    partial_variables={
        "format_instructions": output_parser_check_open_answer.get_format_instructions()
    },
)

output_parser_check_is_answered_to_question = JsonOutputParser(pydantic_object=_CheckIsAnsweredToQuestion)
prompt_template_check_is_answered_to_question = PromptTemplate.from_template(
    check_is_answered_to_question_prompt,
    partial_variables={
        "format_instructions": output_parser_check_is_answered_to_question.get_format_instructions()
    },
)

output_parser_check_is_question_explained = JsonOutputParser(pydantic_object=_CheckIsQuestionExplained)
prompt_template_check_is_question_explained = PromptTemplate.from_template(
    check_is_question_explained_prompt,
    partial_variables={
        "format_instructions": output_parser_check_is_question_explained.get_format_instructions()
    },
)

def get_response_util(usecase_name : str) -> RunnableSequence:
    """
    Returns a RunnableSequence object for the given usecase name.

    Args:
        usecase_name (str): The name of the usecase. like "evaluate_probabilities_of_chunk" or "generate_questions"

    Returns:
        A RunnableSequence object for the given usecase name.
    """
    if usecase_name == "evaluate_probabilities_of_chunk":
        return prompt_template_evaluate_probabilities_of_chunk | fast_model | output_parser_evaluate_probabilities_of_chunk
    elif usecase_name == "generate_questions":
        return prompt_template_generate_questions | quasi_fast_model | output_parser_generate_questions
    elif usecase_name == "generate_questions_fast":
        return prompt_template_generate_questions | fast_model | output_parser_generate_questions
    elif usecase_name == "check_open_answer":
        return prompt_template_check_open_answer | fast_model | output_parser_check_open_answer
    elif usecase_name == "check_is_answered_to_question":
        return prompt_template_check_is_answered_to_question | fast_model | output_parser_check_is_answered_to_question
    elif usecase_name == "check_is_question_explained":
        return prompt_template_check_is_question_explained | fast_model | output_parser_check_is_question_explained
    else:
        raise ValueError(f"Invalid usecase_name: {usecase_name}")