import copy
import importlib
import json
import concurrent.futures
import concurrent.futures
from typing import List, Dict, Any, Tuple
from collections import defaultdict
import sys
import asyncio

from uot_modules.llm_utils import get_response_util
from uot_modules.item import Item

async def generate_questions_and_estimate_probability(items : list[Item], ques_num : int, historys=None, additional_context=None, max_item_size_at_once=10, top_5_items : dict = None, use_fast_mode: bool = False):
   """
   Generates questions and estimates the probability of the given items being true.

   Args:
       items (list[str]): List of name of items to be classified.
       ques_num (int): Number of questions to generate.
       historys (list, optional): List of previous questions and answers. Defaults to None.
       additional_context (list, optional): Additional context for generating questions. Defaults to None.
       max_item_size_at_once (int, optional): Maximum number of items to handle simultaneously. Defaults to 10.
       top_5_items (dict[str, float], optional): Top 5 items and their probabilities. Defaults to None.
       use_fast_mode (bool, optional): Whether to use fast mode for question generation. Defaults to False.

   Returns:
       list: A list of dictionaries where each dictionary contains the classification results for a question.
        [
            {
                "question": str,
                "evaluated_items": [
                    {
                        "p_yes_given_item": float,
                        "p_no_given_item": float,
                        "name": str,
                        "description": str
                    },
                    ...
                ]
            },
            ...
        ]
   """
   if len(items) <= 1:
       return None

   additional_context_str = ", ".join(additional_context) if additional_context else ""
   historys_str = format_history(historys)

   generate_questions_chain = get_response_util("generate_questions_fast" if use_fast_mode else "generate_questions")

   response = generate_questions_chain.invoke({
       "item_name_list": [item.get_name() for item in items],
       "history": historys_str,
       "n": ques_num,
       "one_divided_n": 1/ques_num if ques_num > 0 else 0,
       "additional_context": additional_context_str,
       "top_5_items": top_5_items
   })


   gen_questions = [item["question"] for item in response["items"]]

   #print(f"questions: {gen_questions}")

   return _estimate_probability_of_items(items, gen_questions, historys_str, max_item_size_at_once)

def format_history(historys):
   """
   Formats the history into a string representation.

   Args:
       historys (list): List of previous questions and answers.

   Returns:
       str: String representation of the interaction history.
   """
   if historys is None:
       return "no history"
   
   return '\n'.join([f"Question {i + 1}: {h['q']} -> Answer {i + 1} : {h['a']}" for i, h in enumerate(historys)])

def _estimate_probability_of_items(items: List[Item], questions: List[str], history: str, max_item_size_at_once=10) -> List[Dict[str, Any]]:
    """
    Estimates the probability that items are true based on provided questions and historical context.
    Optimized for parallel API calls with synchronous completion.

    Args:
        items (List[Item]): List of Item to be classified.
        questions (List[str]): Questions used to estimate the truth probability of the items.
        history (str): String representation of the interaction history.
        max_item_size_at_once (int, optional): Maximum number of items to handle simultaneously. Defaults to 10.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing the classification results for a question.
    """
    size_items = len(items)
    items_chunks = [items[i:min(i + max_item_size_at_once, size_items)] for i in range(0, size_items, max_item_size_at_once)]
    results = defaultdict(list)

    #print(f"Number of chunks: {len(items_chunks)}")
    #print(f"Number of questions: {len(questions)}")

    def process_future(future: concurrent.futures.Future, chunk: List[Item], question: str) -> None:
        """
        Process the future result of a chunk of items.

        Args:
            future (concurrent.futures.Future): Future object representing the asynchronous execution.
            chunk (List[Item]): List of items in the chunk.
            question (str): The question used for classification.
        """
        try:
            evaluated_result = future.result()
            evaluated_items = evaluated_result["items"]
            evaluated_items_buf = [
                {
                    "p_yes_given_item": max(min(evaluated_item["y_prob"], 1), 0),
                    "p_no_given_item": max(min(1 - evaluated_item["y_prob"], 1), 0),
                    "name": evaluated_item["name"],
                    "description": evaluated_item["description"]
                }
                for evaluated_item in evaluated_items
            ]
            results[question].extend(evaluated_items_buf)
        except Exception as e:
            print(f"Error processing chunk for question {question}: {e}")

    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Submit all tasks at once
            futures = [
                executor.submit(_simulate_and_estimate_chunk, chunk, question, history)
                for question in questions
                for chunk in items_chunks
            ]

            # Wait for all futures to complete
            concurrent.futures.wait(futures)

            # Process all completed futures
            for future, (chunk, question) in zip(futures, [(chunk, q) for q in questions for chunk in items_chunks]):
                process_future(future, chunk, question)

        # Verify all items are accounted for
        all_evaluated_items = set()
        for question_results in results.values():
            all_evaluated_items.update(item["name"] for item in question_results)

        missing_items = set(item.get_name() for item in items) - all_evaluated_items
        if missing_items:
            print(f"Warning: Some items were not evaluated: {missing_items}")

        # Format results as required
        formatted_results = [{"question": q, "evaluated_items": results[q]} for q in questions]
        return formatted_results

    except Exception as e:
        print(f"Error classifying items: {e}")
        # Fallback to sequential processing if parallel processing fails
        return estimate_probability_of_items(items, questions, history, 1)

def _simulate_and_estimate_chunk(chunk: List[Item], question: str, history: str) -> Dict[str, Any]:
    """
    Simulates and estimates the probability of a chunk of items based on a question and the history.

    Args:
        chunk (List[Item]): List of items to be classified.
        question (str): The question used for classification.
        history (str): String representation of the interaction history.

    Returns:
        Dict[str, Any]: A dictionary containing the classification results for the question.
    """
    estimate_probabilities_of_chunk_chain = get_response_util("evaluate_probabilities_of_chunk")
    response = estimate_probabilities_of_chunk_chain.invoke({"item_name_list": [item.get_name() for item in chunk], "question": question, "history": history})
    return response

async def check_open_answer(question: str, answer: str) -> Tuple[bool, str, float]:
    check_open_answer_chain = get_response_util("check_open_answer")
    response = await asyncio.to_thread(check_open_answer_chain.invoke, {"question": question, "answer": answer})
    
    is_answer_done = response["is_answer_done"]
    observed_prob_of_yes = response["observed_prob_of_yes"]

    if observed_prob_of_yes <= 0.5:
        answer_label = "no"
    else:
        answer_label = "yes"
    
    return is_answer_done, answer_label, observed_prob_of_yes

async def check_is_answered_to_question(responses: list[str], question: str, real_asked_question: str) -> Tuple[bool, str, float]:
    """
    Asynchronously checks if the response answers the given question.

    Args:
        response (list[str]): List of responses to check
        question (str): The question to check against
        real_asked_question (str): The actual question asked (currently unused)

    Returns:
        Tuple[bool, str, float]: 
            - is_answered: Whether the question is answered
            - answer_label: String "yes" or "no"
            - observed_prob_of_yes: Probability of "yes"

    Note:
        This function uses an asynchronous thread to invoke the chain for checking if the question is answered.
    """
    check_is_answered_to_question_chain = get_response_util("check_is_answered_to_question")
    result = await asyncio.to_thread(
        check_is_answered_to_question_chain.invoke,
        {
            "responses": responses,
            "question": question,
            "real_asked_question": real_asked_question,
            "no_clear_answer_count": len(responses)
        }
    )
    
    is_answered = result["is_answered"]
    observed_prob_of_yes = result["observed_prob_of_yes"]

    # Determine the answer label based on the probability
    answer_label = "yes" if observed_prob_of_yes > 0.5 else "no"
    print(f"check_is_answered_to_question response : (responses: {responses}, question: {question}, real_asked_question: {real_asked_question}, is_answered: {is_answered}, answer_label: {answer_label}, observed_prob_of_yes: {observed_prob_of_yes}, thought: {result['thoughts']})")
    return is_answered, answer_label, observed_prob_of_yes

async def check_is_question_explained(response: str, question: str) -> bool:
    """
    Asynchronously checks if the question is explained in the response.

    Args:
        response (str): The response to check
        question (str): The question to check for explanation

    Returns:
        bool: True if the question is explained, False otherwise

    Note:
        This function uses an asynchronous thread to invoke the chain for checking if the question is explained.
    """
    check_is_question_explained_chain = get_response_util("check_is_question_explained")

    result = await asyncio.to_thread(check_is_question_explained_chain.invoke, {"response": response, "question": question})
    print(f"check_is_question_explained_chain response : (response: {response}, question: {question}, result: {result})")
    return result["is_question_explained"]