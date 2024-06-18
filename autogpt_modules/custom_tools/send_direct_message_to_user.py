import os


from langchain.tools.base import BaseTool



class SendDirectMessageToUser(BaseTool):
    """Tool that updates direct instructions on user's screen"""

    name = "send_direct_message_to_user"
    description = (
        "Updata instruction message on user's screen directry with Generateing text to support user comprehension visually and display (title),"
        " Detailed content for client agents to assist users with dementia in interactive conversations about it (detail)."
        "***注意***注意***注意***出力は日本語でなくてなならない。そして何がどうであるのでどうしたいかを明確にすること。***注意***注意***注意***"
        "Input shold be a string instruction_title and string instruction_detaile."
        "instruction_title is actually displayed on the user's screen, so be careful not to stigmatize the user. "
        "instruction_title can be used to present a summary of a conversation to supplement the user's understanding and short-term memory, "
        "or to present key points for actions and tasks in an easy-to-understand order of execution. Alternatively, it can push the user by presenting key points for action or tasks in a clear and understandable order of execution."
        "instruction is used to decide what to do next or how to explain the next step by interface agent who really support dementia user to empower."
        "instruction_title must be updated relatively frequently to make the conversation better on realtime. but, It is easier for users to understand if the title is somewhat consistent."
        "instruction_detail is used to make client agent know anoud the details of the instruction_title in other word, this detail help cient support agent to do better support for dementia user . It is important to provide detailed information to the user to help them understand the context of the conversation and the actions they need to take."
        "***注意***注意***注意***出力は日本語でなくてなならない。そして何がどうであるのでどうしたいかを明確にすること。またわかりました。`どんなことが考えているのか、お話ししてみませんか？`など鼻につくおせっかいな話し方は避けられるべきである。うまく傾聴と指示、サポートで使い分けること!'お困りですね?'はスティグマでくそ***注意***注意***注意***"
        "特に認知症の当事者の感じている世界を想像して寄り添うことが大切である。通常時は概要を振り返れるように細かく更新し、特別なインストラクションの最中は逐次的なプロンプトを表示すること。"
        "[example お風呂の準備の場面の一幕]"
        "instruction_title : 'タオルを持つ。タオルは{...}の{..}にある。'"
        "instruction_detail : '現在は入浴の準備中。全体像を確認した後で、step-by-stepのインストラクションに移る。まずは、タオルを持ってくる。タオルはXXのYYにある。丁寧に説明し、不安を解消すること。また、この次は着替えの準備をする。'"
        "[example 傾聴中の一幕]"
        "instruction_title : 'AがBした。BはCだった。...'"
        "instruction_detail : 話の全体像をわかりやすくするために要点を抜き出し、'AがBした。BはCだった。'のように共有した。"
        "**注意***注意***注意***出力は日本語でなくてなならない。あくまでユーザーのUXを改善する目的なので重要な要約や指示等を除いて必要以上の更新は避けられるべきだ.一方で重要なものは積極的に行うべき**注意***注意***注意***"
        "この直接の表示の変更は, directにユーザーに表示され, 直接対話や状況, 指示の理解強化に役立てられる. つまりこの直接の表示の変更は, ユーザーが少しでも不快に思いうるものは避けるべきである, 直接彼らのためにならないものは表示してはならない. システムやあなたの状態の表示ではなく, ユーザーの状態の表示である."
    )



    def _run(self, instruction_title, instruction_detail) -> str:
        return f"updates direct instructions on user's screen with {instruction_title} and {instruction_detail}"


    async def _arun(self, instruction_title, instruction_detail) -> str:
        return self._run(instruction_title, instruction_detail)
    
    @classmethod
    def get_tool_name(cls) -> str:
        return "send_direct_message_to_user"
