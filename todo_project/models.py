# -*- coding: utf-8 -*-
#
# データベースモデル定義ファイル
# - User (ユーザー認証用)
# - Task (ToDoタスク)
#

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# SQLAlchemyの初期化はここでは行わず、app.pyで実行します
db = SQLAlchemy()

# --- ユーザー情報モデル ---
class User(UserMixin, db.Model):
    """ユーザーのデータベースモデル"""
    __tablename__ = 'user' # テーブル名を明示的に指定
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    # Taskテーブルとのリレーション
    tasks = db.relationship('Task', backref='owner', lazy='dynamic')

    def set_password(self, password):
        """パスワードをハッシュ化して保存する"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """保存されたハッシュ値と入力されたパスワードを比較する"""
        return check_password_hash(self.password_hash, password)

# --- ToDoタスクモデル ---
class Task(db.Model):
    """ToDoタスクのデータベースモデル"""
    __tablename__ = 'task' # テーブル名を明示的に指定
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    done = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    priority = db.Column(db.Integer, default=3, nullable=False) # 1:高, 2:中, 3:低
    due_date = db.Column(db.Date, nullable=True) 
    
    # 外部キー: User.idと紐づけ
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Task {self.id}: {self.title}>'
