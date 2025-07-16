from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app.models import User, Room
from app.forms import RegistrationForm, LoginForm, RoomForm
from flask_socketio import join_room, leave_room, send, emit
import random
import string
import threading
import time

# Delay imports to avoid circular
from app import myapp_obj, db, socketio

room_messages = {}
user_rooms = {}
room_users = {}  # New: track users in each room

@myapp_obj.route('/')
def home():
    return render_template('home.html')

@myapp_obj.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Username already exists. Please choose another.')
            return redirect(url_for('register'))
        user = User(username=form.username.data, password=form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@myapp_obj.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.password == form.password.data:
            login_user(user)
            flash('Logged in successfully.')
            return redirect(url_for('lobby'))
        else:
            flash('Invalid username or password.')
    return render_template('login.html', form=form)

@myapp_obj.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('home'))

@myapp_obj.route('/lobby', methods=['GET', 'POST'])
@login_required
def lobby():
    form = RoomForm()
    if form.validate_on_submit():
        code = form.code.data
        room = Room.query.filter_by(code=code).first()
        if not room:
            new_room = Room(code=code, host_id=current_user.id)
            db.session.add(new_room)
            db.session.commit()
        return redirect(url_for('chat', code=code))
    return render_template('lobby.html', form=form)

@myapp_obj.route('/chat/<code>')
@login_required
def chat(code):
    room = Room.query.filter_by(code=code).first()
    if not room:
        flash('Room does not exist.')
        return redirect(url_for('lobby'))
    return render_template('chat.html', username=current_user.username, code=code)

# Helper function to broadcast user list
def send_user_list(room):
    user_list = list(room_users.get(room, []))
    emit('update_user_list', user_list, room=room)

# SocketIO Events
@socketio.on('join_room')
def handle_join(data):
    username = data['username']
    room = data['room']
    join_room(room)

    user_rooms[request.sid] = {'room': room, 'username': username}

    # Add user to room_users
    if room not in room_users:
        room_users[room] = set()
    room_users[room].add(username)

    send(f"{username} has joined the room.", to=room)
    send_user_list(room)

    if room in room_messages:
        for msg in room_messages[room]:
            send(msg, to=request.sid)

@socketio.on('send_message')
def handle_message(data):
    msg = f"{data['username']}: {data['message']}"
    room = data['room']

    if room not in room_messages:
        room_messages[room] = []
    room_messages[room].append(msg)

    send(msg, to=room)

@socketio.on('leave_room')
def handle_leave(data):
    username = data['username']
    room = data['room']
    leave_room(room)

    send(f"{username} has left the room.", to=room)

    if request.sid in user_rooms:
        del user_rooms[request.sid]

    if room in room_users and username in room_users[room]:
        room_users[room].remove(username)
        if not room_users[room]:
            del room_users[room]
        else:
            send_user_list(room)

    # Check if room empty and clear
    if room in socketio.server.manager.rooms.get('/', {}):
        if len(socketio.server.manager.rooms['/'][room]) == 0:
            if room in room_messages:
                del room_messages[room]
                print(f"Room '{room}' messages cleared after last user left.")
    else:
        if room in room_messages:
            del room_messages[room]
            print(f"Room '{room}' messages cleared after last user left.")

@socketio.on('disconnect')
def handle_disconnect():
    user_data = user_rooms.get(request.sid)
    if user_data:
        username = user_data['username']
        room = user_data['room']

        leave_room(room)
        send(f"{username} has left the room.", to=room)

        del user_rooms[request.sid]

        if room in room_users and username in room_users[room]:
            room_users[room].remove(username)
            if not room_users[room]:
                del room_users[room]
            else:
                send_user_list(room)

        # ✅ Immediately check and clear room messages if empty
        if room in socketio.server.manager.rooms.get('/', {}):
            if len(socketio.server.manager.rooms['/'][room]) == 0:
                if room in room_messages:
                    del room_messages[room]
                    print(f"Room '{room}' messages cleared after last user left.")
        else:
            if room in room_messages:
                del room_messages[room]
                print(f"Room '{room}' messages cleared after last user left.")