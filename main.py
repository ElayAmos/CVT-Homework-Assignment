from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase
import json

app = Flask(__name__)
app.config["SECRET_KEY"] = "hjhjsdahhds"
socketio = SocketIO(app)

rooms = {}  # Dictionary to store room information

def generate_unique_code(length):
    """
    Generate a unique room code.

    Args:
        length (int): Length of the room code.

    Returns:
        str: Unique room code.
    """
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        
        if code not in rooms:
            break
    
    return code

def save_message_history():
    """
    Save the message history to a JSON file.

    Returns:
        None
    """
    with open('message_history.json', 'w') as file:
        json.dump(rooms, file)

def load_message_history():
    """
    Load the message history from a JSON file.

    Returns:
        None
    """
    global rooms
    try:
        with open('message_history.json', 'r') as file:
            rooms = json.load(file)
    except FileNotFoundError:
        pass

@app.route("/", methods=["POST", "GET"])
def home():
    """
    Route for the home page.

    Returns:
        Template: Rendered home.html template.
    """
    session.clear()  # Clear the session data
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        # Validate user inputs
        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name)

        if join != False and not code:
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)
        
        room = code
        if create != False:
            room = generate_unique_code(4)  # Generate a unique room code
            rooms[room] = {"members": 0, "messages": []}  # Initialize room information
        elif code not in rooms:
            return render_template("home.html", error="Room does not exist.", code=code, name=name)
        
        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))  # Redirect to the chat room page

    return render_template("home.html")  # Render the home page template

@app.route("/room")
def room():
    """
    Route for the chat room page.

    Returns:
        Template: Rendered room.html template.
    """
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))  # Redirect to the home page if session data is missing or room does not exist

    return render_template("room.html", code=room, messages=rooms[room]["messages"])  # Render the chat room page template with room information

@socketio.on("message")
def message(data):
    """
    Event handler for receiving messages from clients.

    Args:
        data (dict): Data containing the message.

    Returns:
        None
    """
    room = session.get("room")
    if room not in rooms:
        return  # Ignore if the room does not exist
    
    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)  # Send the message to all clients in the room
    rooms[room]["messages"].append(content)  # Add the message to the room's message history

    # Save message history to a JSON file
    save_message_history()

    print(f"{session.get('name')} said: {data['data']}")  # Print message to console

@socketio.on("connect")
def connect(auth):
    """
    Event handler for client connection.

    Args:
        auth: Authentication information.

    Returns:
        None
    """
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)  # Leave the room if it does not exist
        return
    
    join_room(room)  # Join the room
    send({"name": name, "message": "has entered the room"}, to=room)  # Broadcast entry message to the room
    rooms[room]["members"] += 1  # Increment the number of members in the room
    print(f"{name} joined room {room}")  # Print to console

@socketio.on("disconnect")
def disconnect():
    """
    Event handler for client disconnection.

    Returns:
        None
    """
    room = session.get("room")
    name = session.get("name")
    leave_room(room)  # Leave the room

    if room in rooms:
        rooms[room]["members"] -= 1  # Decrement the number of members in the room
        if rooms[room]["members"] <= 0:
            del rooms[room]  # Delete the room if no members are left
    
    send({"name": name, "message": "has left the room"}, to=room)  # Broadcast exit message to the room
    print(f"{name} has left the room {room}")  # Print to console

if __name__ == "__main__":
    load_message_history()  # Load message history from JSON file
    socketio.run(app, debug=True)  # Run the Flask app with SocketIO support
