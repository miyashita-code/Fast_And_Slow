# Fast_And_Slow

クライアント側の高速な応答エージェントとサーバーサイドの深い思考を行うエージェントを組み合わせた二重プロセスシステムです。非同期での推論とプランニングにより、ユーザーとの対話を途切れさせることなく、深い理解に基づいた制御を実現します。

## システム概要

### デュアルプロセスアーキテクチャ
1. **Fast Process（クライアントサイド）**
   - 即時的なユーザー応答
   - 基本的な対話管理
   - ローカルでの状態管理

2. **Slow Process（サーバーサイド）**
   - 非同期での深い推論処理
   - LendingEarModuleによる状況理解と質問生成
   - Graph Instructionによる段階的プランニング
   - 状態遷移の管理と最適化

### 主要コンポーネント

#### サーバーサイド推論エンジン
- **LendingEarModule**
  - 対話履歴からの文脈理解
  - 適応的な質問生成
  - 知識グラフを用いた推論

- **状態管理システム**
  ```python
  class BackEndProcess:
      def __init__(self, socketio, room, client_data, db, kg_db):
          self.lending_ear_controller = None
          self.conversation_controller = None
          self.llm_client = ChatFireworks(...)
  ```

#### 通信制御
- Socket.IOベースの双方向通信
- JWT認証による安全な接続管理
- FCMを利用した非同期通知

### 状態遷移と制御フロー

```mermaid
sequenceDiagram
    participant User
    participant Fast as Fast Process
    participant Slow as Slow Process
    participant KG as Knowledge Graph

    User->>Fast: ユーザー入力
    Fast-->>User: 即時応答
    Fast->>Slow: 非同期処理要求
    Fast->>User
    User->>Fast: ユーザー入力
    
    ...

    Slow->>KG: コンテキスト分析
    KG-->>Slow: 推論結果
    Slow-->>Fast: 制御指示
    Fast-->>User: 最適化された応答
```

## 概要
Flask-basedのソケットサーバーで、認証機能を備えています。JWT（JSON Web Token）によるAPIキーの発行とハンドシェイク認証を使用し、PostgreSQLデータベースで認証済みユーザー情報を管理します。

## 前提条件
- Python 3.9.16
- Flask
- PostgreSQL
- Firebase Authentication
- ngrok（開発環境でのトンネリング用）

## インストールとセットアップ

### Step 1: Python環境のセットアップ
pyenvを使用してPython 3.9.16をインストールします：
```bash
pyenv install 3.9.16
pyenv local 3.9.16
```

### Step 2: 仮想環境の作成
プロジェクトディレクトリで仮想環境を作成し、有効化します：
```bash
python -m venv .venv
source .venv/bin/activate  # Unix系の場合
.venv\Scripts\activate     # Windowsの場合
```

### Step 3: PostgreSQLのインストール
公式サイトからPostgreSQLをダウンロードしてインストールし、以下のコマンドでデータベースを作成：
```sql
CREATE DATABASE rementia;
```

### Step 4: 環境変数の設定
.env.exampleを.envにコピーし、必要な環境変数を設定します：
- OPENAI_API_KEY
- FIREBASE_API_KEY
- DATABASE_URL
- その他必要な認証情報

### Step 5: 依存パッケージのインストール
```bash
pip install -r requirements.txt
```

### Step 6: データベースのマイグレーション
```bash
flask db init
flask db migrate -m "initial migration"
flask db upgrade
```

### Step 7: ngrokでのトンネリング設定
開発環境で外部からアクセスできるようにngrokを設定：
```bash
ngrok http --domain=<あなたのドメイン> 8080
```

### Step 8: アプリケーションの起動
```bash
python app.py
```

## 認証フロー

1. `/login`エンドポイントにアクセスしてログイン
2. `/create_user`でユーザーを作成し、APIキーを取得
   - 取得したAPIキーは安全に保管（Androidアプリのsecrets等で使用）

## 通知機能

FCM（Firebase Cloud Messaging）を使用した通知システムを実装：
- `/fcm/console`で通知管理コンソールにアクセス
- 個別ユーザーまたは全ユーザーへの通知送信が可能

## WebSocket (Socket.IO) の使用

Socket.IOを使用したリアルタイム通信が可能です：

```javascript
// クライアント側の実装例
const socket = io('http://your-server:8080', {
  auth: {
    token: 'your-jwt-token'
  }
});

socket.on('connect', () => {
  console.log('接続成功');
});

socket.on('message', (data) => {
  console.log('メッセージ受信:', data);
});
```

## セキュリティ注意事項
- APIキーは必ず安全に保管してください
- 本番環境では適切なSSL/TLS証明書を使用してください
- 環境変数は適切に管理し、公開リポジトリにコミットしないよう注意してください

## トラブルシューティング
- データベース接続エラーの場合、DATABASE_URLの形式を確認
- Firebase認証エラーの場合、認証情報の正確性を確認
- Socket.IO接続エラーの場合、CORSとポート設定を確認

ご不明な点がございましたら、イシューを作成してください。

## Socket.IO イベントハンドラーとクライアント通信

### 基本的な通信フロー

1. 認証フロー
```javascript
// 1. APIキーを使用してJWTトークンを取得
POST /api/token
Header: {
    'API-Key': 'your-api-key'
}

// 2. 取得したトークンでSocket.IO接続
const socket = io('http://your-server:8080', {
    query: { token: 'your-jwt-token' }
});
```

### 主要なイベントハンドラー

1. チャットメッセージ送信
```javascript
// クライアント側
socket.emit('chat_message', {
    role: "user",
    content: "メッセージ内容"
});

// サーバーからの応答受信
socket.on('message', (data) => {
    console.log('受信メッセージ:', data);
});
```

2. モード切替
```javascript
// 傾聴モード開始
socket.emit('start_lending_ear');

// 指示モード開始
socket.emit('start_instruction');
```

3. 状態遷移制御
```javascript
// 次の状態へ進む
socket.emit('go_next_state');

// 詳細表示へ移行
socket.emit('go_detail');

// 開始状態に戻る
socket.emit('back_to_start');
```

### FCM (Firebase Cloud Messaging) 通知

1. FCMトークン登録
```javascript
POST /api/fcm/token_register
Headers: {
    'API-Key': 'your-api-key',
    'FCM-Token': 'your-fcm-token'
}
```

2. 通知受信
```kotlin
// Androidクライアント側
class MyFirebaseMessagingService : FirebaseMessagingService() {
    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        val notifyDisplayInfo = remoteMessage.data["notifyDisplayInfo"]
        val notifyDetail = remoteMessage.data["notifyDetail"]
        val notifySpeechReading = remoteMessage.data["notifySpeechReading"]
        
        // 通知の表示処理
    }
}
```

### エラーハンドリング

1. 接続エラー
```javascript
socket.on('connect_error', (error) => {
    console.error('接続エラー:', error);
});
```

2. 認証エラー
```javascript
socket.on('error', (error) => {
    if (error.message === 'Invalid token') {
        // トークン再取得処理
    }
});
```

### 切断処理
```javascript
// クライアント側での切断
socket.disconnect();

// 再接続
socket.connect();
```

### 注意事項

- WebSocketの接続は、バックグラウンドでも維持されます
- 長時間の非アクティブ状態後は自動的に再接続を試みます
- FCMトークンは、アプリの起動時に必ず更新・登録してください
- メッセージの送受信は非同期で行われ、順序は保証されません

### デバッグとトラブルシューティング

1. WebSocket接続の確認
```bash
# サーバーログで接続状態を確認
tail -f server.log | grep "socket"
```

2. FCM通知のテスト
- `/fcm/console`エンドポイントにアクセスして通知をテスト送信
- 開発環境での通知テストには、実機を使用することを推奨
