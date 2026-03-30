from flask import Flask, request
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from marshmallow import ValidationError
from datetime import datetime, timedelta
from redis import Redis
from rq import Queue
import os

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/postgres",
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

from .models import Category, Task
from .schemas import CategorySchema, TaskSchema, TaskUpdateSchema
from .jobs import send_due_soon_notification  # if jobs.py is in app/

category_schema = CategorySchema()
task_schema = TaskSchema()
task_update_schema = TaskUpdateSchema()

redis_conn = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
task_queue = Queue(connection=redis_conn)


@app.route("/")
def index():
    return {"message": "Task Manager API is running"}


@app.route("/categories", methods=["GET"])
def get_categories():
    categories = Category.query.all()

    result = []
    for category in categories:
        item = category.to_dict()
        item["task_count"] = len(category.tasks)
        result.append(item)

    return {"categories": result}, 200


@app.route("/categories/<int:category_id>", methods=["GET"])
def get_category(category_id):
    category = Category.query.get(category_id)
    if not category:
        return {"error": "Category not found"}, 404

    return category.to_dict(include_tasks=True), 200


@app.route("/categories", methods=["POST"])
def create_category():
    json_data = request.get_json()
    if not json_data:
        return {"errors": {"json": ["No input data provided"]}}, 400

    try:
        data = category_schema.load(json_data)
    except ValidationError as err:
        return {"errors": err.messages}, 400

    category = Category(**data)
    db.session.add(category)
    db.session.commit()

    return {"category": category.to_dict()}, 201


@app.route("/categories/<int:category_id>", methods=["DELETE"])
def delete_category(category_id):
    category = Category.query.get(category_id)
    if not category:
        return {"error": "Category not found"}, 404

    if category.tasks:
        return {
            "error": "Cannot delete category with existing tasks. Move or delete tasks first."
        }, 400

    db.session.delete(category)
    db.session.commit()
    return {"message": "Category deleted"}, 200


@app.route("/tasks", methods=["GET"])
def get_tasks():
    completed = request.args.get("completed")
    query = Task.query

    if completed is not None:
        if completed.lower() == "true":
            query = query.filter_by(completed=True)
        elif completed.lower() == "false":
            query = query.filter_by(completed=False)

    tasks = query.all()
    return {"tasks": [task.to_dict() for task in tasks]}, 200


@app.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return {"error": "Task not found"}, 404

    return {"task": task.to_dict()}, 200


@app.route("/tasks", methods=["POST"])
def create_task():
    json_data = request.get_json()
    if not json_data:
        return {"errors": {"json": ["No input data provided"]}}, 400

    try:
        data = task_schema.load(json_data)
    except ValidationError as err:
        return {"errors": err.messages}, 400

    task = Task(**data)
    db.session.add(task)
    db.session.commit()

    notification_queued = False

    if task.due_date:
        now = datetime.utcnow()
        if now < task.due_date <= now + timedelta(hours=24):
            task_queue.enqueue(send_due_soon_notification, task.title)
            notification_queued = True

    return {
        "task": task.to_dict(),
        "notification_queued": notification_queued,
    }, 201


@app.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return {"error": "Task not found"}, 404

    json_data = request.get_json()
    if not json_data:
        return {"errors": {"json": ["No input data provided"]}}, 400

    try:
        data = task_update_schema.load(json_data)
    except ValidationError as err:
        return {"errors": err.messages}, 400

    for key, value in data.items():
        setattr(task, key, value)

    db.session.commit()
    return {"task": task.to_dict()}, 200


@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return {"error": "Task not found"}, 404

    db.session.delete(task)
    db.session.commit()
    return {"message": "Task deleted"}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)