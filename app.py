from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os

# --- アプリケーションの基本設定 ---

# データベースファイルのパスを定義
# この設定により、データファイル（todo.db）をプロジェクト内の'instance'フォルダに置きます
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance', 'todo.db')

# Flaskアプリケーションの初期化
app = Flask(__name__)

# データベース設定
# SQLiteを使用し、データベースファイルの場所を指定
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
# 警告を非表示にする設定（初心者は気にしなくてOK）
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# SQLAlchemy（データベース操作ライブラリ：ORM）の初期化
db = SQLAlchemy(app)

# --- データベースモデルの定義（テーブル設計） ---

# Todoテーブルに対応するPythonのクラス
# このクラスを通じて、データベースへの保存や読み出しを行います
class Todo(db.Model):
    # id: タスクの識別番号（主キー: テーブルの行を一意に識別する番号）
    id = db.Column(db.Integer, primary_key=True)
    # content: タスクの内容（文字列、最大200文字、nullable=Falseは「空欄を許さない」の意味）
    content = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        # Pythonでオブジェクトをprintしたときの表示形式を定義
        return f'<Todo {self.id}>'

# --- URLルーティング（ユーザー操作に対する処理の定義） ---

# '@app.route('/')': ブラウザから '/' (トップページ) にアクセスがあったときの処理を定義
# methods=['GET', 'POST']: GET(表示)とPOST(フォーム送信)の両方を受け付ける
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # --- フォーム送信（新規タスクの追加）時の処理 ---
        # フォームから 'content' の値（タスクの内容）を取得
        task_content = request.form['content']

        # 新しいTodoオブジェクト（データベースに保存する準備）を作成
        new_todo = Todo(content=task_content)
        try:
            # データベースのセッションに追加
            db.session.add(new_todo)
            # データベースに実際に保存を確定（コミット）
            db.session.commit()
            # 処理が終わったら、同じページ（'index'関数）にリダイレクトして再送信を防ぐ
            return redirect(url_for('index'))
        except Exception as e:
            # エラーが発生した場合の処理
            print(f"Error adding todo: {e}")
            return 'タスクの追加中にエラーが発生しました', 500

    else:
        # --- GETリクエスト（ページ表示）時の処理 ---
        # データベースから全てのTodo（タスク）を取得
        # .all() ですべての行を取得
        todos = Todo.query.all()
        # 'index.html' テンプレートを読み込み、取得した 'todos' を渡して表示
        return render_template('index.html', todos=todos)

# --- アプリケーションの実行 ---
if __name__ == '__main__':
    # アプリケーションを実行する前に初期設定を行う
    with app.app_context():
        # instanceディレクトリが存在しない場合は作成
        os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)
        # データベースファイルとテーブルが存在しない場合に作成（初回起動時のみ実行される）
        db.create_all()
    # デバッグモード（コード変更時に自動で再起動）でサーバーを起動
    app.run(debug=True, port = 8081)