from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_socketio import SocketIO, send

import threading
import time
import random  # For generating random temperature values

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")


class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    complete = db.Column(db.Integer, default=0)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return '<Task %r>' % self.id

class TempSample(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    temp = db.Column(db.Float, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return '<TempSample %r>' % self.id
    

# Tworzenie bazy danych (odkomentuj za pierwszym razem)
# with app.app_context():
#     db.create_all()


@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        task_content = request.form['content']
        new_task = Todo(content=task_content)

        try:
            db.session.add(new_task)
            db.session.commit()

            # Wysłanie wiadomości do wszystkich po dodaniu nowego zadania
            socketio.emit('message', f'Nowe zadanie dodane: {task_content}')

            return redirect('/')
        except:
            return 'There was an issue adding your task'
    else:
        tasks = Todo.query.order_by(Todo.date_created).all()
        return render_template('index.html', tasks=tasks)


@app.route('/delete/<int:id>')
def delete(id):
    task_to_delete = Todo.query.get_or_404(id)

    try:
        db.session.delete(task_to_delete)
        db.session.commit()
        return redirect('/')
    except:
        return 'There was a problem deleting that task'


@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    task = Todo.query.get_or_404(id)

    if request.method == 'POST':
        task.content = request.form['content']

        try:
            db.session.commit()
            return redirect('/')
        except:
            return 'There was an issue updating your task'

    else:
        return render_template('update.html', task=task)
    

# Wydarzenie, gdy klient połączy się z serwerem
@socketio.on('connect')
def handle_connect():
    print('Klient połączony')
    send('Witaj, jesteś połączony z serwerem!')


def temperature_sensor():
    with app.app_context():
        while True:
            simulated_temp = round(random.uniform(20.0, 25.0), 2)  # Symulowana temperatura
            new_sample = TempSample(temp=simulated_temp)

            print("dzialam")
            # Zapisanie odczytu do bazy danych
            
            db.session.add(new_sample)
            db.session.commit()

            # Wysłanie danych przez socket do klienta
            socketio.emit('temperature_update', {'temp': simulated_temp})
            print(f'Nowa próbka temperatury: {simulated_temp}°C')

            time.sleep(10)  # Czas próbkowania co 10 sekund


if __name__ == '__main__':
    # Uruchomienie funkcji temperature_sensor w osobnym wątku
    sensor_thread = threading.Thread(target=temperature_sensor)
    sensor_thread.daemon = True
    sensor_thread.start()

    socketio.run(app, host='127.0.0.1', port=8000)
