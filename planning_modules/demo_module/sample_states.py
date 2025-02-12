from typing import List
from planning_modules.demo_module.state import State

def get_init_state_iphone_manipuration() -> List[State]:
    return [
        State(detail="iphoneのmapの使い方を説明します。", name="iphoneのmapの使い方説明", time=0, next_state="iphoneのホーム画面を開く", title="iphoneのmapの使い方説明"),
        State(detail="まずはiphoneを手に取り, 電源を入れてホーム画面を開いてください。", name="iphoneのホーム画面を開く", time=0, next_state="マップ アプリを開く", title="iphoneのホーム画面を開く"),
        State(detail="まずは、mapのアプリの中に入りたいので、画面の右下の方にある「マップ アプリを開いてください」", name="マップ アプリを開く", time=1, next_state="マップで検索をタップ", title="画面右下のマップ アプリを開く"),
        State(detail="マップを開いたら、目的地を検索します。画面の下の方の虫眼鏡のアイコンの横に「マップで検索」と書いてあるところをタップか長押ししてください。キーボードが出てきます。", name="マップで検索をタップ", time=0, next_state="目的地を入力", title="「🔍マップで検索」をタップ"),
        State(detail="キーボードが出てきたら、キーボードで目的地の住所か名前を入力してください。入力後、入力欄の下に表示された候補の中から目的のものを見つけてタップしてください。", name="目的地を入力", time=1, next_state="経路ボタンをタップ", title="目的地をキーボードで入力"),
        State(detail="画面下部に青色のボタンで「経路」と書いてあるボタンがあります。このボタンをタップしてください。そうすれば出発地を選択の画面が出てきます。もしない場合は下に隠れているかもしれないです。", name="経路ボタンをタップ", time=0, next_state="現在地を選択", title="画面下部の青色の経路ボタンをタップ"),
        State(detail="出発地点の入力を求められたら、現在地を選択してください。そのあと、右上の青色の経路を選択します。", name="現在地を選択", time=0, next_state="出発", title="出発地に現在地を選択"),
        State(detail="あとは画面下部右下の出発をタップして、出発です！お気をつけて！", name="出発", time=0, next_state="終了", title="出発をタップしてお気をつけて！"),
    ]


def get_init_state_walk_preparation() -> List[State]:

    return [
        State(
            description="散歩に行きませんか？",
            name="身支度を始める",
            time=0,
            next_state="服装を整える",
            title="散歩に行きませんか？ 身支度を始める",
            detail_name=None
        ),
        State(
            description="靴下を履いたり、上着を着たりしましょう",
            name="服装を整える",
            time=0,
            next_state="トイレに行く",
            title="服装を整える",
            detail_name="靴下を履く"
        ),
        State(
                description="靴下は履いていますか？履いていなければ靴下を履きましょう。",
                name="靴下を履く",
                time=0,
                next_state="上着を着る",
                title="靴下を履く",
                detail_name="靴下を探す"
        ),
        State(
            description="靴下が見つからない場合は、服がかかっているところの下にある引き戸にあるのでそこを見てください。",
            name="靴下を探す",
            time=0,
            next_state="上着を着る",
            title="靴下を探す。引き出しの中",
            detail_name="さらに靴下を探す"
        ),
        State(
            description="それでも靴下が見つからない場合は、窓のそばによく落ちてるのでそこを確認してください。",
            name="さらに靴下を探す",
            time=0,
            next_state="上着を着る",
            title="窓のそばに靴下が落ちていることがあるので確認する",
            detail_name="さらに靴下を探す"
        ), 
        State(
            description="外に行く前に服装だけ整えたいですね。今日は外の気温が低いので、温かい上着を着るのがおすすめですよ。(10度前後みたいですよ)",
            name="上着を着る",
            time=0,
            next_state="トイレに行く",
            title="上着を着る"
        ),
        State(
            description="靴下と上着の準備が済んだので着替えは完了です。あとは必要に応じて念のためトイレを済ませておくと安心ですね。",
            name="トイレに行く",
            time=0,
            next_state="靴箱に向かう",
            title="必要に応じてトイレに行く"
        ),
        State(
            description="それでは、1階の靴箱に向かいましょう。",
            name="靴箱に向かう",
            time=0,
            next_state="終了",
            title="靴箱に向かう",
            detail_name="スリッパはそのままで大丈夫"
        ),
        State(
            description="スリッパのままでいいのか、靴はどこにあるのか不安になることがあるかもしれませんが、下に靴箱があるので大丈夫ですよ。そのまま向かってください。",
            name="靴箱に向かう",
            time=0,
            next_state="終了",
            title="靴箱に向かう",
            detail_name=None
        ),
        State(
            description="これで準備が完了しました。お気をつけていってらっしゃい！",
            name="終了",
            time=0,
            next_state="終了",
            title="お気をつけて！"
        ),
    ]   

def get_init_state_dayservice() -> List[State]:
    return [
    #State(description="init", name="init", time=0, next_state="トレリハに行くための身支度", title="init"),
    State(description="トレリハに行く前の準備をします", name="トレリハに行くための身支度を始める", time=0, next_state="服を取りに行く", title="トレリハに行く前の準備"),
    State(description="まずはジャージとジャンパーを「奥のヘヤ（部屋）」に取りに行きましょう。", name="服を取りに行く", time=0, next_state="服の準備", title="奥の部屋に服を取りに行く", call_to_action="奥ヘアに行ってください！お願いします！", detail_instruction="説明が長くなることが想定されるので、ひとまず「着替えのために」服を取りに行く旨を説明して下さい。その次の応答で「奥ヘアに行ってください！お願いします！」と呼びかけを２回に分けてしてください。移動が終わるまでほんの少し待ってください。"),
    State(description="ジャージとジャンパーはタンスのとってのところにハンガーでかかっています。それを持ってくださいね。", name="服の準備", time=0, next_state="着替えのための移動", title="ハンガーにかかったジャージ, ジャンパーのセットをとる", call_to_action="ジャージとジャンパーのセットをとってください", detail_instruction="説明が長くなることが想定されるので、ひとまず「ハンガーの服をとる」旨を伝えてください。終了条件は「手に着替えを持っていますか？」と聞いて「はい」ときたら次に進みます。必ず終了条件を確認してください。"),
    State(description="次は着替えをするために、着替えを持ったままご自身のお部屋に一度戻りましょう。", name="着替えのための移動", time=0, next_state="着替え", title="ご自身のお部屋に戻り着替え", call_to_action="ご自身のお部屋に移動してくださいね", detail_instruction="説明が複雑になることが予想されます。わかりやすくするために「そのまま着替えをこれからすること」、「自分のおへやに戻ること」を両方伝えてください。とくに後者です。"),
    State(description="次は、着替えです。それでは、お着替えをお願いします", name="着替え", time=4, next_state="靴下を取り出す", title="着替えをする", call_to_action="お着替えをお願いします"),
    State(description="次は「くつした」をトレリハ用のものに変えます。くつしたはくつした箱の「下の引き出し」入っているものがトレリハ用のくつしたです。", name="くつしたを取り出す", time=2, next_state="くつしたを履く", title="くつしたを取り出す。くつした箱の下の段の中", call_to_action="くつしたの箱からくつしたを取り出してください。下の段です", detail_instruction="説明が長くなることが想定されるので、ひとまず「くつしたを取り出す」旨を伝えてください。その次の応答で「靴下の場所」について説明して下さい。一度に長くなりすぎてはなりません。場所が分からない時は「いつもくつした出すとこ」ですと追加で説明してください。終了条件は「取り出しましたか？」と聞いて「はい」ときたら次に進みます."),
    State(description="そのまま、取り出したくつしたに着替えてください。", name="くつしたを履く", time=2, next_state="洗濯ものかごに入れる", title="くつしたを履く"),
    State(description="脱いだ靴下を洗濯ものかごに入れるのをお忘れなく！", name="洗濯ものかごに入れる", time=0, next_state="終了", title="脱いだ靴下を洗濯ものかごに入れる"),
    State(description="それでは、トレリハに行くための準備は完了です。あとは、お迎えが来るまでゆっくりしていてくださいね", name="終了", time=0, next_state="", title="お迎えまで待つ"),
]

def get_init_state_dayservice2() -> List[State]:
    return [
    #State(description="init", name="init", time=0, next_state="トレリハに行くための身支度", title="init"),
    State(description="次は「くつした」をトレリハ用のものに変えます。くつしたはくつした箱の「下の引き出し」入っているものがトレリハ用のくつしたです。２列あるうちの左側です。", name="くつしたを取り出す", time=2, next_state="くつしたを履く", title="くつしたを取り出す。くつした箱の下の段の中", call_to_action="くつしたの箱からくつしたを取り出してください。下の段です"),
    State(description="そのまま、取り出したくつしたに着替えてください。", name="くつしたを履く", time=2, next_state="洗濯ものかごに入れる", title="くつしたを履く"),
    State(description="脱いだ靴下を洗濯ものかごに入れるのをお忘れなく！", name="洗濯ものかごに入れる", time=0, next_state="終了", title="脱いだ靴下を洗濯ものかごに入れる"),
    State(description="それでは、トレリハに行くための準備は完了です。あとは、お迎えが来るまでゆっくりしていてくださいね", name="終了", time=0, next_state="", title="お迎えまで待つ"),
]