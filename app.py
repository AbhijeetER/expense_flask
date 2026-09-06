from flask import Flask, redirect, render_template, request, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import json

app = Flask(__name__)
app.secret_key = "super_secret_dev_key_change_me_in_production" 
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///expenses_td.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- DATABASE MODELS ---

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False, default=lambda: datetime.now(timezone.utc).date())

    def __repr__(self)->str:
        return f"Expense {self.id}: {self.description}"

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    complete = db.Column(db.Boolean, default=False)
    date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self)->str:
        return f"Todo {self.id}"


with app.app_context():
    db.create_all()

# --- BACKEND APPLICATION ROUTES ---

@app.route("/", methods=["GET"])
def first_exp():
    
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    todos = Todo.query.order_by(Todo.date.desc()).all()
    
    total_amount = sum(e.amount for e in expenses)
    pending_tasks = Todo.query.filter_by(complete=False).count()
    
    cat_totals = {}
    for e in expenses:
        cat_totals[e.category] = cat_totals.get(e.category, 0) + e.amount
        
    # Standard Categories Array Context used by edit dropdown loops
    categories_list = ["Food", "Transport", "Rent", "Utilities"]
    
    return render_template(
        'index.html', 
        expenses=expenses, 
        todos=todos,
        total_amount=total_amount,
        pending_tasks=pending_tasks,
        categories=categories_list,
        chart_labels=json.dumps(list(cat_totals.keys())),
        chart_values=json.dumps(list(cat_totals.values()))
    )

@app.route("/add", methods=["POST"])
def add():
    description = (request.form.get("description") or "").strip()
    category = (request.form.get("category") or "").strip()
    amount_str = (request.form.get("amount") or "").strip()
    date_str = (request.form.get("date") or "").strip()

    if not description or not category or not amount_str:
        flash("Please fill out all related data fields!", "error")
        return redirect(url_for("first_exp"))
    
    try:
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError
    except ValueError:
        flash("Amount must be a positive number!", "error")
        return redirect(url_for("first_exp"))

    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.now(timezone.utc).date()
    except Exception:
        d = datetime.now(timezone.utc).date()
    
    new_expense = Expense(description=description, amount=amount, category=category, date=d)
    db.session.add(new_expense)
    db.session.commit()
    flash("Expense tracked successfully!")
    return redirect(url_for("first_exp"))

@app.route("/delete-expense/<int:id>")
def delete_expense(id):
    expense = Expense.query.get_or_404(id)
    db.session.delete(expense)
    db.session.commit()
    return redirect(url_for("first_exp"))

@app.route("/edit-expense/<int:expense_id>", methods=["GET", "POST"])
def edit_post(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    categories_list = ["Food", "Transport", "Rent", "Utilities"]
    
    if request.method == "POST":
        expense.description = request.form.get("description")
        expense.amount = float(request.form.get("amount", 0))
        expense.category = request.form.get("category")
        
        date_str = request.form.get("date")
        if date_str:
            expense.date = datetime.strptime(date_str, "%Y-%m-%d").date()
            
        db.session.commit()
        return redirect(url_for("first_exp"))
        
    return render_template('edit.html', expense=expense, categories=categories_list)



@app.route("/add-todo", methods=["POST"])
def add_todo():
    todo_content = request.form.get("content")
    if todo_content:
        new_todo = Todo(content=todo_content)
        db.session.add(new_todo)
        db.session.commit()
    return redirect(url_for("first_exp"))

@app.route("/toggle-todo/<int:id>")
def toggle_todo(id):
    todo = Todo.query.get_or_404(id)
    todo.complete = not todo.complete 
    db.session.commit()
    return redirect(url_for("first_exp"))

@app.route("/delete-todo/<int:id>")
def delete_todo(id):
    todo = Todo.query.get_or_404(id)
    db.session.delete(todo)
    db.session.commit()
    return redirect(url_for("first_exp"))

@app.errorhandler(404)
def non_existent(error):
    return "<h1>This page does not exist. Please return home!</h1>", 404

if __name__ == "__main__":
    app.run(debug=True)
