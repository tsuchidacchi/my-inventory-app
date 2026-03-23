import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('inventory.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """テーブルが存在しない場合に新規作成する"""
    conn = get_db_connection()
    # QRスキャン側で使っていた構成に合わせつつ、棚番号なども保持
    conn.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            item_id INTEGER PRIMARY KEY,
            item_name TEXT NOT NULL,
            stock_count INTEGER DEFAULT 0,
            shelf_no TEXT
        )
    ''')
    conn.commit()
    conn.close()

# --- ここから追加 ---　Render用
with app.app_context():
    init_db()
# --- ここまで追加 ---

# --- 画面表示（一覧・管理画面） ---
@app.route('/')
def index():
    conn = get_db_connection()
    items = conn.execute('SELECT * FROM inventory').fetchall()
    conn.close()
    return render_template('inventory.html', items=items)

# --- スキャン用画面の表示 ---
@app.route('/scanner')
def scanner():
    return render_template('scanner.html')

# --- 商品登録 ---
@app.route('/add', methods=['POST'])
def add():
    item_id = request.form.get('item_id')
    item_name = request.form.get('item_name')
    stock_count = request.form.get('stock_count')
    shelf_no = request.form.get('shelf_no')

    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO inventory (item_id, item_name, stock_count, shelf_no) VALUES (?, ?, ?, ?)',
            (item_id, item_name, stock_count, shelf_no)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        print("エラー：商品コードが重複しています。")
    finally:
        conn.close()
    return redirect(url_for('index'))

# --- 在庫数更新（手動上書き） ---
@app.route('/update/<int:item_id>', methods=['POST'])
def update(item_id):
    new_stock = request.form.get('new_stock')
    conn = get_db_connection()
    conn.execute('UPDATE inventory SET stock_count = ? WHERE item_id = ?', (new_stock, item_id))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# --- QR読み取り後の在庫マイナス処理 ---
@app.route('/reduce_post', methods=['POST'])
def reduce_post():
    data = request.json
    item_id = data.get('item_id')
    if not item_id:
        return jsonify({"status": "error", "message": "商品コードが不明です"}), 400

    conn = get_db_connection()
    # 在庫を1減らす（0未満にはしない）
    cur = conn.execute(
        'UPDATE inventory SET stock_count = stock_count - 1 WHERE item_id = ? AND stock_count > 0',
        (item_id,)
    )
    conn.commit()
    success = cur.rowcount > 0
    conn.close()

    if success:
        return jsonify({"status": "success", "item_id": item_id})
    else:
        return jsonify({"status": "error", "message": "該当商品がないか、在庫が0です"}), 404

# --- 商品削除 ---
@app.route('/delete/<int:item_id>', methods=['POST'])
def delete(item_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM inventory WHERE item_id = ?', (item_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)