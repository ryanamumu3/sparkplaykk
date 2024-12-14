from flask import Flask, render_template, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
database_file = "sqlite:///{}".format(os.path.join(project_dir, "bookdatabase.db"))

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = database_file
app.secret_key = os.urandom(24)
db = SQLAlchemy(app)

# Modelos

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))

    def __repr__(self):
        return f"<Category {self.name}>"

class Book(db.Model):
    title = db.Column(db.String(80), unique=True, nullable=False, primary_key=True)
    description = db.Column(db.Text, nullable=True)
    rating = db.Column(db.Float, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)

    user = db.relationship('User', backref='books')
    category = db.relationship('Category', backref='books')

    def __repr__(self):
        return f"<Book {self.title}>"

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_title = db.Column(db.String(80), db.ForeignKey('book.title'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='comments')
    book = db.relationship('Book', backref='comments')

    def __repr__(self):
        return f"<Comment {self.content[:20]}...>"

class ForumTopic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('forum_topics', lazy=True))

    def __repr__(self):
        return f"<ForumTopic {self.title}>"

class ForumComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('forum_topic.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('forum_comments', lazy=True))
    topic = db.relationship('ForumTopic', backref=db.backref('forum_comments', lazy=True))

    def __repr__(self):
        return f"<ForumComment {self.content[:20]}...>"

# Novos Modelos para Grupos e Mensagens de Grupo
class DiscussionGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('discussion_groups', lazy=True))
    
    def __repr__(self):
        return f"<DiscussionGroup {self.name}>"

class GroupMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('discussion_group.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('group_messages', lazy=True))
    group = db.relationship('DiscussionGroup', backref=db.backref('group_messages', lazy=True))

    def __repr__(self):
        return f"<GroupMessage {self.content[:20]}...>"

with app.app_context():
    db.create_all()

# Rotas

@app.route("/", methods=["GET", "POST"])
def home():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        rating = request.form.get("rating")
        category_id = request.form.get("category")

        try:
            book = Book(title=title, description=description, rating=float(rating), user_id=session["user_id"], category_id=category_id)
            db.session.add(book)
            db.session.commit()
            flash("Livro adicionado com sucesso!", "success")
        except Exception as e:
            flash("Falha ao adicionar livro", "danger")
            print("Falha ao adicionar livro:", e)

    categories = Category.query.all()
    books = Book.query.all()
    return render_template("index.html", books=books, categories=categories)

# Fórum - Tópicos e Comentários

@app.route("/forum")
def forum():
    if "user_id" not in session:
        flash("Você precisa estar logado para acessar o fórum.", "warning")
        return redirect("/login")

    topics = ForumTopic.query.all()
    discussion_groups = DiscussionGroup.query.all()  # Adiciona grupos ao fórum
    return render_template("forum.html", topics=topics, discussion_groups=discussion_groups)

@app.route("/add_forum_topic", methods=["POST"])
def add_forum_topic():
    if "user_id" not in session:
        flash("Você precisa estar logado para criar um tópico.", "warning")
        return redirect("/login")

    title = request.form['title']
    content = request.form['content']
    user_id = session['user_id']
    
    new_topic = ForumTopic(title=title, content=content, user_id=user_id)
    db.session.add(new_topic)
    db.session.commit()

    flash("Tópico criado com sucesso!", "success")
    return redirect("/forum")

@app.route("/add_comment/<int:topic_id>", methods=["POST"])
def add_comment(topic_id):
    if "user_id" not in session:
        flash("Você precisa estar logado para comentar.", "warning")
        return redirect("/login")

    content = request.form['content']
    user_id = session['user_id']
    
    new_comment = ForumComment(content=content, user_id=user_id, topic_id=topic_id)
    db.session.add(new_comment)
    db.session.commit()

    flash("Comentário adicionado com sucesso!", "success")
    return redirect(f"/forum_topic/{topic_id}")

@app.route("/forum_topic/<int:topic_id>")
def forum_topic(topic_id):
    topic = ForumTopic.query.get_or_404(topic_id)
    comments = ForumComment.query.filter_by(topic_id=topic_id).all()
    return render_template("forum_topic.html", topic=topic, comments=comments)

# Grupos de Discussão

@app.route("/create_group", methods=["GET", "POST"])
def create_group():
    if "user_id" not in session:
        flash("Você precisa estar logado para criar um grupo.", "warning")
        return redirect("/login")

    if request.method == "POST":
        name = request.form['name']
        description = request.form['description']
        user_id = session['user_id']
        
        new_group = DiscussionGroup(name=name, description=description, user_id=user_id)
        db.session.add(new_group)
        db.session.commit()
        
        flash("Grupo criado com sucesso!", "success")
        return redirect("/forum")

    return render_template("create_group.html")

@app.route("/group/<int:group_id>", methods=["GET", "POST"])
def group(group_id):
    group = DiscussionGroup.query.get_or_404(group_id)
    
    if request.method == "POST":
        content = request.form['content']
        user_id = session['user_id']
        
        new_message = GroupMessage(content=content, user_id=user_id, group_id=group.id)
        db.session.add(new_message)
        db.session.commit()
        
        flash("Mensagem enviada com sucesso!", "success")
        return redirect(f"/group/{group.id}")
    
    messages = GroupMessage.query.filter_by(group_id=group_id).all()
    return render_template("group.html", group=group, messages=messages)

# Registro, Login e Logout

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Nome de usuário já existe. Escolha outro.", "danger")
            return redirect("/register")

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash("E-mail já cadastrado. Use outro.", "danger")
            return redirect("/register")

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash("Usuário cadastrado com sucesso!", "success")
        return redirect("/login")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["username"] = user.username
            flash("Login realizado com sucesso!", "success")
            return redirect("/")
        else:
            flash("Credenciais inválidas. Tente novamente.", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu com sucesso!", "success")
    return redirect("/login")

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
