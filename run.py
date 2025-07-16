from app import myapp_obj, socketio

if __name__ == '__main__':
    socketio.run(myapp_obj, debug=True)