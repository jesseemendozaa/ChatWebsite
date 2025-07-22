from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from wtforms import FormField
from app.models import User, Room
from app.forms import RegistrationForm, LoginForm, RoomForm, GameSelectionForm, GamertagForm, GameTagField
from flask_socketio import join_room, leave_room, send, emit
from flask import session
import random
import string
import threading
import time
import json

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

        return redirect(url_for('select_games', user_id=user.id))
    return render_template('register.html', form=form)

@myapp_obj.route('/select_games/<int:user_id>', methods=['GET', 'POST'])
def select_games(user_id):
    form = GameSelectionForm()
    user = User.query.get(user_id)

    if not user:
        flash('User not found.')
        return redirect(url_for('register'))

    if form.validate_on_submit():
        user.games = ', '.join(form.games.data)
        db.session.commit()
        return redirect(url_for('gamertags', user_id=user.id))

    return render_template('select_games.html', form=form, username=user.username)

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

@myapp_obj.route('/profile')
@login_required
def profile():
    import json

    user = current_user
    platform_tag = user.platform_tag
    selected_games = user.games.split(', ') if user.games else []
    game_tags = json.loads(user.game_tags) if user.game_tags else {}

    return render_template(
        'profile.html',
        username=user.username,
        platform_tag=platform_tag,
        selected_games=selected_games,
        game_tags=game_tags
    )

@myapp_obj.route('/chat/<code>')
@login_required
def chat(code):
    room = Room.query.filter_by(code=code).first()
    if not room:
        flash('Room does not exist.')
        return redirect(url_for('lobby'))
    return render_template('chat.html', username=current_user.username, code=code)

@myapp_obj.route('/gamertags/<int:user_id>', methods=['GET', 'POST'])
def gamertags(user_id):
    import json
    from flask import current_app

    user = User.query.get_or_404(user_id)
    selected_games = user.games.split(', ') if user.games else []

    image_map = {
        'UNO': 'UNO.png',
        'DBD': 'Dead_By_Daylight.png',
        'Dead By Daylight': 'Dead_By_Daylight.png'
    }

    class DynamicGamertagForm(GamertagForm):
        class Meta:
            csrf = False  # only for local testing convenience

    # Dynamically add game fields
    for game in selected_games:
        field_name = game.lower().replace(" ", "_")
        setattr(DynamicGamertagForm, field_name, FormField(GameTagField, label=game))

    form = DynamicGamertagForm()

    # Prevent Jinja error on first GET render
    if not form.platform.data:
        form.platform.data = []

    if request.method == 'POST':
        current_app.logger.info("====== POST received ======")
        current_app.logger.info(f"Platform: {form.platform.data}")
        current_app.logger.info(f"Platform tag: {form.platform_gamertag.data}")
        for game in selected_games:
            field = getattr(form, game.lower().replace(" ", "_"))
            current_app.logger.info(f"{game} same_as_platform: {field.same_as_platform.data}")
            current_app.logger.info(f"{game} gamertag: {field.gamertag.data}")
        current_app.logger.info(f"Form errors: {form.errors}")

        if form.validate_on_submit():
            current_app.logger.info("✅ Form validated successfully. Proceeding to save and redirect.")

            user.platform = ', '.join(form.platform.data or [])
            user.platform_tag = form.platform_gamertag.data

            gamertags = {}
            for game in selected_games:
                field = getattr(form, game.lower().replace(" ", "_"))
                gamertags[game] = (
                    user.platform_tag if field.same_as_platform.data
                    else field.gamertag.data
                )

            user.game_tags = json.dumps(gamertags)
            db.session.commit()

            flash("Gamertags saved. You can now log in.")
            return redirect(url_for('login'))

        current_app.logger.warning("❌ Form did not validate. Staying on page.")

    platform_image_map = {
        'Xbox': 'xboxLogo.png',
        'PlayStation': 'PlayStationLogo.png',
        'PC': 'SteamLogo.png'
    }

    return render_template(
        'gamertags.html',
        form=form,
        username=user.username,
        selected_games=selected_games,
        image_map=image_map,
        platform_image_map=platform_image_map
    )

# ------------------ SocketIO Events ------------------

@socketio.on('join_room')
def handle_join(data):
    username = data['username']
    room = data['room']
    join_room(room)

    user_rooms[request.sid] = {'room': room, 'username': username}

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

        if room in socketio.server.manager.rooms.get('/', {}):
            if len(socketio.server.manager.rooms['/'][room]) == 0:
                if room in room_messages:
                    del room_messages[room]
                    print(f"Room '{room}' messages cleared after last user left.")
        else:
            if room in room_messages:
                del room_messages[room]
                print(f"Room '{room}' messages cleared after last user left.")