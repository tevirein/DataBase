# -*- coding: utf-8 -*-
#
# Flaskメインアプリケーションファイル
# - データベースの初期化、ルーティング、認証処理を定義します
#

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from models import db, User, Task # models.py から db とモデルをインポート
from datetime import datetime
import os

# --- 1. アプリとデータベースの設定 ---
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'todo_auth_separated.db') # ファイル名を変更

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_strong_secret_key' 
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# SQLAlchemyとLoginManagerを初期化
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' 
login_manager.login_message = "ログインが必要です。"

# --- 2. Flask-Login ユーザーローダー ---
@login_manager.user_loader
def load_user(user_id):
    """Flask-LoginがユーザーIDからユーザーオブジェクトをロードするために使用"""
    # models.py で定義した User クラスを使用
    return db.session.execute(db.select(User).filter_by(id=int(user_id))).scalar_one_or_none()


# --- 3. 認証関連のルート (新規登録, ログイン, ログアウト) ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    """新規ユーザー登録"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_exists = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
        
        if user_exists:
            flash('そのユーザー名はすでに使われています。', 'error')
        elif len(password) < 4:
            flash('パスワードは4文字以上で設定してください。', 'error')
        else:
            new_user = User(username=username)
            new_user.set_password(password) # ハッシュ化して保存
            db.session.add(new_user)
            db.session.commit()
            flash('登録が完了しました。ログインしてください。', 'message')
            return redirect(url_for('login'))

    # templates/register.html をレンダリング
    return render_template('register.html', title='新規登録')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """ユーザーログイン"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
        
        if user and user.check_password(password):
            login_user(user)
            flash('ログインに成功しました！', 'message')
            return redirect(url_for('index'))
        else:
            flash('ユーザー名またはパスワードが違います。', 'error')
            
    # templates/login.html をレンダリング
    return render_template('login.html', title='ログイン')

@app.route('/logout')
@login_required 
def logout():
    """ユーザーログアウト"""
    logout_user()
    flash('ログアウトしました。', 'message')
    return redirect(url_for('login'))


# --- 4. タスク管理のルート (CRUD + 検索) ---

@app.route('/', methods=['GET'])
@login_required 
def index():
    """タスク一覧表示と検索"""
    base_query = db.select(Task).filter_by(user_id=current_user.id)
    
    # 検索処理
    search_query = request.args.get('q', '')
    if search_query:
        # タスクタイトルにキーワードが含まれるものをフィルタリング
        # Task モデルは models.py からインポートしています
        base_query = base_query.filter(Task.title.like(f'%{search_query}%'))

    # ソート処理: 未完了が上で、優先度高、期限日早い順
    tasks = db.session.execute(
        base_query.order_by(
            Task.done.asc(), 
            Task.priority.asc(), 
            Task.due_date.asc()
        )
    ).scalars()
    
    # templates/index.html をレンダリング
    return render_template('index.html', title='ToDoリスト', tasks=tasks, current_query=search_query)

@app.route('/add', methods=['POST'])
@login_required
def add():
    """新しいタスクを追加"""
    title = request.form.get('title')
    priority = request.form.get('priority', 3) 
    due_date_str = request.form.get('due_date') 
    
    if title:
        due_date = None
        try:
            if due_date_str:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('期限日の形式が正しくありません。', 'error')
            
        new_task = Task(
            title=title.strip(), 
            priority=int(priority),
            due_date=due_date,
            done=False,
            user_id=current_user.id 
        )
        db.session.add(new_task)
        db.session.commit()
        flash('タスクを追加しました。', 'message')
    
    return redirect(url_for('index'))

@app.route('/update/<int:id>', methods=['POST'])
@login_required
def update(id):
    """タスクを編集（タイトル, 優先度, 期限日）"""
    task = db.session.execute(db.select(Task).filter_by(id=id, user_id=current_user.id)).scalar_one_or_none()
    
    if not task:
        flash('指定されたタスクが見つからないか、編集権限がありません。', 'error')
        return redirect(url_for('index'))

    new_title = request.form.get('title')
    new_priority = request.form.get('priority')
    new_due_date_str = request.form.get('due_date')

    if new_title:
        task.title = new_title.strip()
    
    if new_priority:
        task.priority = int(new_priority)
        
    try:
        due_date = None
        if new_due_date_str:
            due_date = datetime.strptime(new_due_date_str, '%Y-%m-%d').date()
        task.due_date = due_date
    except ValueError:
        flash('期限日の形式が正しくありません。', 'error')

    db.session.commit()
    flash('タスクを更新しました。', 'message')
    return redirect(url_for('index'))

@app.route('/done/<int:id>')
@login_required
def done(id):
    """タスクの完了/未完了を切り替え"""
    task = db.session.execute(db.select(Task).filter_by(id=id, user_id=current_user.id)).scalar_one_or_none()
    
    if not task:
        flash('タスクが見つからないか、権限がありません。', 'error')
        return redirect(url_for('index'))
    
    task.done = not task.done
    db.session.commit()
    flash(f'タスク「{task.title}」の状態を更新しました。', 'message')
    
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
@login_required
def delete(id):
    """タスクを削除"""
    task = db.session.execute(db.select(Task).filter_by(id=id, user_id=current_user.id)).scalar_one_or_none()
    
    if not task:
        flash('タスクが見つからないか、削除権限がありません。', 'error')
        return redirect(url_for('index'))

    db.session.delete(task)
    db.session.commit()
    flash(f'タスク「{task.title}」を削除しました。', 'message')
    
    return redirect(url_for('index'))

# --- 5. アプリの実行 ---

if __name__ == '__main__':
    # アプリケーション起動時にDBを初期化
    with app.app_context():
        # UserテーブルとTaskテーブルを作成
        db.create_all()
    
    app.run(debug=True)
