from typing import List
from demo_module.st import State

def get_init_state_iphone_manipuration(self) -> List[State]:
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


def get_init_state_walk_preparation(self) -> List[State]:

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

