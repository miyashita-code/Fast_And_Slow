## IO Manager Protocol Documentation

### Overview
IO_ManagerはState MachineとClient間の通信を管理する中核コンポーネントです. WebSocketベースのイベント駆動型通信により駆動されます.

### Core Components

pip install Graphviz


#### 1. Event Management
~~~python
self.state_flags = {
    "go_next": asyncio.Event(),
    "go_detail": asyncio.Event(),
    "back_to_start": asyncio.Event()
}
~~~
- 状態遷移イベントの管理
- 非同期イベントフラグによる制御
- クライアントからの指示を状態遷移に変換

#### 2. Message Queue
~~~python
self.message_queue = asyncio.Queue()
~~~
- 非同期メッセージキュー
- クライアント-サーバー間の双方向通信
- メッセージの順序保証

#### 3. Callback Registry
~~~python
self.event_callbacks: Dict[str, Callable] = {}
~~~
- イベントハンドラの登録システム
- カスタムイベント処理の拡張性
- プラグイン可能なイベントハンドリング

### Communication Protocol

#### 1. Server → Client Events
| Event Name | Data Structure | Description |
|------------|----------------|-------------|
| node_current | `{"node": str, "description": str, "state": str}` | 現在のノード情報 |
| explain | `{"node": str, "description": str, "type": str}` | ノードの説明 |
| enter_detail | `{"node": str, "children": List[Dict]}` | 詳細モード開始 |
| state_changed | `{"node": str, "state": str}` | 状態変更通知 |
| error | `{"message": str}` | エラー通知 |

#### 2. Client → Server Events
| Event Name | Description | State Change |
|------------|-------------|--------------|
| go_next | 次の状態へ進む | Current → Next |
| go_detail | 詳細表示モード | Current → Detail |
| back_to_start | 初期状態に戻る | Current → Init |

### Usage Examples

#### 1. Basic Setup
~~~python
io_manager = IOManager()
io_manager.set_send_socket(websocket_send_function)
~~~

#### 2. Event Registration
~~~python
async def custom_handler(data):
    # Handle custom event
    pass

io_manager.register_callback("custom_event", custom_handler)
~~~

#### 3. Event Handling
~~~python
# クライアントからのイベント処理
await io_manager.handle_websocket_event("go_next")

# サーバーからのイベント送信
io_manager.send_event("node_current", {
    "node": "task_name",
    "description": "task_description",
    "state": "current_state"
})
~~~

### Integration Guidelines

#### 1. Client Side Implementation
- WebSocket接続の確立
- イベントリスナーの設定
- UI状態の同期

#### 2. State Machine Integration
- IOManagerインスタンスの共有
- 状態遷移イベントの処理
- エラーハンドリング

#### 3. Testing
MockIOManagerを使用したテスト例：
~~~python
mock_io = MockIOManager()
mock_io.send_event("test_event", {"data": "test"})
await mock_io.handle_websocket_event("go_next")
~~~

### Future Development
1. **クライアント実装**
   - WebSocketクライアントの実装

2. **内部での状態推移推定機能**
   - Visonモダリティの追加
   - 加速度センサーモダリティの追加
   ...
