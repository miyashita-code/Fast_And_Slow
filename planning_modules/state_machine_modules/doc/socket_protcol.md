# Socket Event Protocol

## Overview
このドキュメントは、状態機械モジュールで使用されるSocket Eventプロトコルを定義します。

## Event Types

### 1. State Management Events

#### next_state_info
状態遷移情報を通知
~~~json
{
    "state_info": {
        "current_state": "state_name",
        "description": "state description",
        "title": "state title",
        "has_detail": boolean,
        "has_next": boolean,
        "call_to_action": "action description",
        "detail_instruction": "instruction text"
    }
}
~~~

### 2. Communication Events

#### instruction
AIからの指示やメッセージを送信
~~~json
{
    "instruction": "instruction text",
    "isLendingEar": boolean
}
~~~

#### telluser
ユーザーへの通知（状態変更時など）
~~~json
{
    "titles": "notification title",
    "detail": "notification detail"
}
~~~

#### call_to_action
ユーザーへのアクション要求
~~~json
{
    "action_description": "action description"
}
~~~

### 3. Control Events

#### announce
システム状態の通知
~~~json
{
    "announce": "announcement message"
}
~~~

## Event Usage Guidelines

1. 状態遷移時の通知順序
   - next_state_info
   - telluser（新状態の説明）
   - instruction（必要に応じて）

2. エラー通知
   - next_state_info内でエラー情報を含める
~~~json
{
    "state_info": {
        "error": "error message"
    }
}
~~~

3. タイミング制御
   - call_to_actionは通常10秒の遅延後に送信
   - instructionは即時送信

## Implementation Notes

1. 全てのイベントは非同期で処理される必要がある
2. エラーハンドリングは必ずnext_state_infoを通じて行う
3. 状態変更時は必ずtelluser経由でユーザーに通知
4. 通常の指示はinstruction経由で送信
