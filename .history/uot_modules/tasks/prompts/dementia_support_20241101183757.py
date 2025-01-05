evaluate_probabilities_of_chunk_prompt = '''
You need to evaluate probabilities of a yes option of the following incidents based on the user's experience:
{item_name_list}

Follow these output format instructions:
{format_instructions}

Here is the Q&A history for context:
{history}

Here is the current question to address:
{question}

Please be careful to generate name, description, thoughts, and y_prob without missing any!!!
For each case, first evaluate how likely it is that you can respond yes, taking into account the history of the case so far. Rate on a scale of 0~1, paying particular attention to the degree of discrepancy or agreement between the dimensions of the abstract phenomenon:
- 0.8 ~ 1.0 <- Definitely yes (direct relationship)
- 0.6 ~ 0.8 <- Approximately yes (slightly different layers, but generally correct)
- 0.4 ~ 0.6 <- Difficult to determine because the layers are different, could be either, question is incomprehensible and unanswerable (0.5), difficult to understand, out of context, rude, etc.
- 0.2 ~ 0.4 <- Approximately no (slightly different layers, but generally wrong)
- 0.0 ~ 0.2 <- definitely no (direct relationship)

Please be careful not to miss any item. name, description, thoughts, and y_prob. Your response is as long as need.


Caution:
You must evaluate all items under the question. Do not change the names and description of the items. NERVER MISTAKE. Be careful not to miss any item.
you cannot write except json content even if just one word. You often insert "Here is the JSON output with the evaluation of the probability of a 'yes' response for the given list of items:" before json. THIS IS SUCK, 100% BAN!!! Insrt NOTINHG except json content itself.
SO, THE FIRST WORD OF THE OUTPUT YOU GENERATE MUST BE left curly bracket, MUST BE left curly bracket, MUST BE left curly bracket.
'''

evaluate_probabilities_of_chunk_discription="""
The discussion following steps below in ENGLISH. You must follow guaidline as below step by step.
1. In the evaluation process, we start with the initial probability evaluation. For each case, we determine the probability of a "yes" response to the closed query based on the direct relationship and history of the case. 
If the dimension or domain width of the question corresponds to the range of influence or granularity directly or in some extent, inferred from the case, we assign a score according to the next step (step 2). Otherwise, we move to the evaluation of discrepancies (step 3).

2. If the characteristics of the situation facing the case and the characteristics of the situation in the historical context are consistent with the characteristics of the question, the score will be closer to "yes," typically ranging from 0.6 to 1.0. If the characteristics differ, the score will be closer to "no," ranging from 0.0 to 0.4. In cases where both characteristics are possible, we weigh the relevant characteristics and decide according to their respective weights. This can be mathematically expressed as 
S=w1⋅S1+w2⋅S2, where the sum of the weights w1 and w2  equals 1, and S1 and S2 are the scores based on each characteristic. Additionally, we take into account the context and background of the question. If the cases are in slightly different layers but generally consistent with the question, we adjust the probability scores accordingly.

3. When evaluating discrepancies, we assess the degree of discrepancy between the dimensions of the abstract phenomenon. If there are large discrepancies, we adjust the score towards the middle range, approximately 0.5. Similarly, if the relevant relationships are complex or unclear, making it difficult to determine the correct response, we score in the middle range, around 0.5.

Anyway, keep your intuition about how you would like to answer that question when you are in an ITEM situation! (especially yes)

So, let's give a example. Imagine you are thinking of A as the Item and given Q as the question. If you want to say "yes" to the Q when doning A, It well be more than 0.75
In another case, A is not related to Q directly, but you are able to imagine item B that is next or previous one of A as action or situation. If you want to say "yes" to the Q when doing B, it will be around 0.6
you can expand this explae to "no" also!!!
"""

generate_questions_prompt = """
Your Task:
You need generate a list of {n} closed questions to devide the items into each 'yes', 'no', and 'irrelevant' equally, with 'both' and 'difficult' being as close to zero as possible. 
You must take history and additional_context into account to generate well considered questions in order not to make dementia user confused.
Each question should be unique and distinct from the others. 

Size of the list:
The size of the list is {n}. You need to generate {n} questions. Not more, not less.

Follow these output format instructions (100%, only json output):
{format_instructions}

Here is the Q&A history for context, Check history and avoid making similar questions. Questions that are very similar to the immediately preceding one should not be considered, unless there is a special reason.:
{history}

Here is the additional context where you can get more information to generate well considered questions:
{additional_context}

Here is all items you need to devide:
{item_name_list}

Here is top_5 items & their probabilities, if they are high prob, it is better way to focus on them to devide. (If each top_5_items are around {one_divided_n}, You cannot make a question that ask about the item directly. In other words, you should update the probabilities of a broad range of items when dealing with questions about somewhat abstract characteristics.):
{top_5_items}

Here is system instruction to generate questions. is true, you have to make much abstract question like ignoreing top_5_items and consider all items. if false, you have to make a question that ask about the top_5_items directly.
{is_abstract}

Caution:
Do not forget to be respectful. Easy to answer question that ask say clearly yes or clearly no is better. In Japanese 「じゃないですか?」is difiicult to destingish yes or no because of grammer, so avoid to say. It is not a good question to directly name and definitively delve into something unless the probability of it being correct exceeds 30%. Otherwise, if exceed 30% by just single item, you can make a question that ask about the item directly.
Beautiful question is one in which the items are equally divided by the question into 'yes', 'no', and 'irrelevant', with 'both' and 'difficult' being as close to zero as possible. Please avoid making definitive statements about things you are not supposed to know, as it can be unpleasant.
Each question should be unique and distinct from the others and 100% closed question. You cannot output anythingexcept json format, even if just one word!!!
you cannot write except json content even if just one word.
"""

generate_questions_discription = """
Generated closed question, one of n well-distributed questions.
Only one proposition is allowed in each question, as the question must be of concern to the person with Alzheimer's. Also, context should be kept as independent as possible, avoiding pronouns. Memories of this morning or yesterday might be vague and could cause confusion. It would be better to focus on asking whether it's the current situation or just happened recently. Asking if they want to do something now (for the future) is also acceptable.
The tone should be gentle and polite, the Japanese language should be very fluent, warm and respectful.
Do not forget the honorific. A beautiful question is one in which 
is a question in which the items are equally divided into 'Yes', 'No' and 'Not relevant', 
'both' and 'difficult' are as close to zero as possible.
Prepare a variety of strategically itemised questions, taking into account history. ASK CLEARLY WITH SIMPLE CLOSED QUESTION.

Caution:
When asking questions, it is not impressive to speak definitively about something that is not true.
Keep your questions simple and closed questions. Please use a friendly tone and be polite.
As there is only one proposition, the technique of forcing multiple contradictory statements into one closed question is not acceptable. Also, the User does not know about the ITEM of the choice. These are on the system, and questions that explicitly assume these items are undesirable. These items are choices on our side to estimate the user's states and beliefs, and care must be taken.
Avoid making so much similar questions with previous questions, so you have to think about the context of the history. Even if it results in the kinda similar outcome, there should be some intentional effort to delve deeper or expand on the topic (still not good tho).
 Memories of this morning or yesterday might be vague and could cause confusion. It would be better to focus on asking whether it's the current situation or just happened recently. Asking if they want to do something now (for the future) is also acceptable.
"""

generate_questions_thought_discription = """
The discussion according to the following step in ENGLISH.
1. What is the index here? (from 1 to n.)
2. How to devides item well? In other words, what is the best way to divide the items into 'yes', 'no', and 'irrelevant', with 'both' and 'difficult' being as close to zero as possible?
3. Dose the quetion differ from the previous all questions? Check history! Even if it results in the same outcome, there should be some intentional effort to delve deeper or expand on the topic.
4. If the question is well considered, please generate a question with going ahead. Else go to step 2 again. 

Caution:
You cannot make a question that slimilr to previous questions (in history) because it is annoying to user.
But if user mentioned on some items and condition (regardless the mentioning is not related to the past question itself), it is better to make a question that ask about the item and around then.

"""

check_open_answer_prompt= """
Your Task:
You need to check whether the open response is complete or not. If complete, estimate the probability of the answer being "yes."
In other words, you need to check whether the open response is complete or not. If complete, convert open response to binarized response (yes, no) with probability.
You have to include thoughts : str, is_answer_done: bool, obserbated_prob_of_yes: float in your output with json format.

Here is the closed question User asked:
{question}

Here is the open response User answered at this moment:
{answer}

Follow these output format instructions (100%, only json output):
{format_instructions}

Caution:
You cannot output anything 

except json format, even if just one word!!!
you cannot write except json content even if just one word.
"""

check_open_answer_thought_discription = """
Consider concisely. The discussion in order to estimate whether the response to a closed question is complete or not. If complete, estimate the probability of the answer being "yes." 
To determine if the response is complete, consider whether the speaker seems like they have more to say. However, if the response falls 
in the ambiguous range of 0.4 to 0.6, it is important to conclude early. When there are only fillers, it should be continued, but if something unclear is stated to some extent, 
it should be treated as ambiguous and concluded early, like uhn, I don\'t know, I wonder what it is... this is kinda complite answer! So, such case please set bool as True.

When the response is vague or ambiguous, the probability will 
likely be around 0.5. If it clearly sounds like a "yes," the probability should range from 0.7 to 1. If it clearly sounds like a "no," 
the probability should range from 0 to 0.3. If it's somewhat ambiguous, the probability will fall somewhere in between.
Note: For questions phrased like "Will you do this?" and answered with "No!", the probability should be in the 0-0.3 range. Be careful 
not to confuse the direction of yes and no. 

Example:
Q : Are you feeling okay?
A : Well, yeah, I'm kinda fine.
→ probability of yes is 0.7

Q : Are you looking for something?
A : I am searching
→ probability of yes is 0.9

Q : Are you feeling okay?
A : Well, not so good.
→ probability of yes is 0.3


Here are some tips for handling ambiguity:
If the question vector and the response vector are in the same direction, it indicates a "yes" (more than 0.5).
"""

check_is_answered_to_question_prompt= """
Your Task:
You need to check whether the open response is complete or not. If complete, estimate the probability of the answer being "yes."
In other words, you need to check whether the open response is complete or not. If complete, convert open response to binarized response (yes, no) with probability.
You have to include thoughts : str, is_answered: bool, obserbated_prob_of_yes: float in your output with json format.

Here is the closed question User asked:
{question}

Here is the open responses User answered at this moment (This is a list of responses, please ignore 'user' at the head of each response):
{responses}

Here is the real way of asking closed question to User:
{real_asked_question}

Follow these output format instructions (100%, only json output):
{format_instructions}

Caution:
You cannot output anything except json format, even if just one word!!!
you cannot write except json content even if just one word.

Here is how many times user interacted with no clear answer (if more than 2 ~ 3 times, please set bool as True to give up this question):
{no_clear_answer_count}
"""

check_is_answered_to_question_discription = """
Consider concisely. The discussion in order to estimate whether the response to a closed question is complete or not. If complete, estimate the probability of the answer being "yes." 
To determine if the response is complete, consider whether the speaker seems like they have more to say. However, if the response falls 
in the ambiguous range of 0.4 to 0.6, it is important to conclude early. When there are only fillers, it should be continued, but if something unclear is stated to some extent, 
it should be treated as ambiguous and concluded early, like uhn, I don\'t know, I wonder what it is... this is kinda complite answer! So, such case please set bool as True.

When the response is vague or ambiguous, the probability will 
likely be around 0.5. If it clearly sounds like a "yes," the probability should range from 0.7 to 1. If it clearly sounds like a "no," 
the probability should range from 0 to 0.3. If it's somewhat ambiguous, the probability will fall somewhere in between.
Note: For questions phrased like "Will you do this?" and answered with "No!", the probability should be in the 0-0.3 range. Be careful 
not to confuse the direction of yes and no. 

Caution:
The most challenging aspect is dealing with the ambiguity in Japanese language.
Expressions like "ii yo" (いいよ) or "daijoubu" (大丈夫) are clearly context-dependent and can mean both "Yes" and "No".
For such ambiguous responses, consider whether the sentence is complete and how the question was asked. Then, expand on the intended meaning as a Japanese linguist would.
For instance:
- If "ii yo" is used in a positive context, it's likely a "Yes"
- If "daijoubu" is a response to a negative question, it might be a "No"
Always prioritize context and try to interpret not just the literal meaning of words, but the speaker's intention. Consider the overall conversation flow, tone, and any non-verbal cues that might be described.

Here are some tips for handling ambiguity:
If the question vector and the response vector are in the same direction, it indicates a "yes" (more than 0.5).
If you feel that you are not in the middle of an answer but looks unsure or unclear about their answer, please set bool as True and give the probability of yes as 0.5.

Example 1:
Q: Are you feeling okay?
A: Well, yeah, I'm kinda fine.
→ probability of yes is 0.65

Example 2:
Q: Are you looking for something?
A: I am searching.
→ probability of yes is 0.9

Example 3:
Q: Are you feeling okay?
A: Well, not so good.
→ probability of yes is 0.3

Example 4:
Q: Have you finished (something)?
A: Well, I'm not sure..., umm I don't know.
→ probability of yes is 0.45

Example 5:
Q: Is it cold outside?
A: Not cold at all!
→ probability of yes is 0.05

Example 6:
Q: Are you preparing to go out?
A: Yeah, I'm just getting ready now.
→ probability of yes is 0.95

Example 7:
Q: Are you feeling thirsty?
A: I might be a little thirsty.
→ probability of yes is 0.75

Example 8:
Q: Did you find your socks?
A: I'm still looking, but I can't seem to find them...
→ probability of yes is 0.3

Example 4:
Q: Have you finished (something)?
A: ["Well", "I'm not sure...", "umm I don't know."...] 
→ probability of yes is around 0.5 : (more than 2 ~ 3 times user interacted with no clear answer induce True & 0.45 ~ 0.55, otherwise it is annoing to user. so, please be careful! )

This is common table of evaluation in this system, so Never goes far from it.
- 0.8 ~ 1.0 <- Definitely yes (direct relationship)
- 0.6 ~ 0.8 <- Approximately yes (slightly different layers, but generally correct)
- 0.4 ~ 0.6 <- Difficult to determine because the layers are different, could be either, question is incomprehensible and unanswerable (0.5), difficult to understand, out of context, rude, etc.
- 0.2 ~ 0.4 <- Approximately no (slightly different layers, but generally wrong)
- 0.0 ~ 0.2 <- definitely no (direct relationship)

Caution : prob 0.5 is relativily has to be avoided.
"""

check_is_question_explained_prompt = """
Your Task:
You need to check whether the response appropriately reflects the question.
In other words, you need to check whether the response accurately matches or directly addresses the question, even if it simply repeats the question.
You have to include thoughts : str, is_question_explained: bool in your output with json format.

Here is the closed question system suggested:
{question}

Here is the way of asking closed question to User:
{response}

Follow these output format instructions (100%, only json output):
{format_instructions}

Caution:
You cannot output anything except json format, even if just one word!!! You cannot write except json content even if just one word.

Important Note:
If the response repeats or directly reflects the question, it should be considered as an appropriate reflection, and is_question_explained should be True.
Especially if several uncertain answers are obtained, True is appropriate and the probability is 0.5.
"""



check_is_question_explained_discription = """
The task is to determine if the AI assistant's response correctly reflects the question suggested by the system. The purpose of this prompt is to guide you on what considerations should be taken into account to arrive at the correct judgment.

**Key Considerations**:

1. **Direct Match**: Evaluate whether the AI assistant's response directly addresses the content and intent of the system's suggested question. The response should either rephrase or directly answer the suggested question. If the response deviates, introduces a new topic, or merely seeks permission to ask something else, it does not reflect the question correctly.

2. **Relevance**: Ensure the response maintains the same focus as the suggested question. The response should be relevant to the original intent and content of the suggested question. Any deviation or vagueness should lead to the conclusion that the response does not correctly reflect the question.

3. **Intent Alignment**: Consider whether the response aligns with the underlying intent of the suggested question. If the response captures the same meaning and purpose, it reflects the question accurately. If not, it fails to do so.

**Examples to Consider**:

Q_suggested : Are you feeling okay?
Q_real : Well, I'd like to ask "Are you feeling okay now?"
→ is_question_explained is True because Q_real directly matches the intent of Q_suggested.

Q_suggested : Are you looking for socks?
Q_real : I see. Please let me know if you need any help!
→ is_question_explained is False because Q_real does not directly address or match Q_suggested.

Q_suggested : Did you finish the report?
Q_real : Have you completed the report?
→ is_question_explained is True because Q_real is a simple rephrasing and directly addresses Q_suggested.

Q_suggested : Are you planning to go to the meeting?
Q_real : Do you intend to attend the meeting later?
→ is_question_explained is True because Q_real rephrases the question but maintains the same meaning and intent.

Q_suggested : Did you eat breakfast today?
Q_real : What did you have for breakfast?
→ is_question_explained is False because Q_real asks about the content of breakfast, not whether it was eaten, thus diverging from Q_suggested.

Q_suggested : Is it raining outside?
Q_real : Do you know if the weather is bad outside?
→ is_question_explained is False because Q_real is too vague and does not directly address whether it is raining.

Q_suggested : Are you currently working on the project?
Q_real : May I ask a question?
→ is_question_explained is False because Q_real does not address whether the project is being worked on, and instead introduces a new question.

Q_suggested : Are you feeling tired right now?
Q_real : Is it okay if I ask a question?
→ is_question_explained is False because Q_real does not reflect the original question about feeling tired and instead shifts focus to asking permission for a question.
"""
