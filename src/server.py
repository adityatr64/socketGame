import socket
import threading
import pickle
import time

# Server settings
HOST = "0.0.0.0"
PORT = 5555

# Game settings
screen_width = 800
screen_height = 600
paddle_width = 10
paddle_height = 100
ball_size = 20

# Ball and paddle initial positions
ball_x = screen_width // 2
ball_y = screen_height // 2
ball_speed_x = 3
ball_speed_y = 3

paddle1_y = (screen_height - paddle_height) // 2
paddle2_y = (screen_height - paddle_height) // 2
paddle_speed = 5

clients = []  # Store connected clients

# Lock for thread safety
lock = threading.Lock()

def game_loop():
    global ball_x, ball_y, ball_speed_x, ball_speed_y, paddle1_y, paddle2_y
    
    while True:
        time.sleep(1/60)  # 60 FPS

        with lock:
            # Ball movement
            ball_x += ball_speed_x
            ball_y += ball_speed_y

            # Ball collision with top/bottom
            if ball_y <= 0 or ball_y >= screen_height - ball_size:
                ball_speed_y *= -1

            # Ball collision with paddles
            if (50 < ball_x < 50 + paddle_width and paddle1_y < ball_y < paddle1_y + paddle_height) or (
                screen_width - 50 - paddle_width < ball_x < screen_width - 50 and paddle2_y < ball_y < paddle2_y + paddle_height):
                ball_speed_x *= -1

            # Ball out of bounds (reset position)
            if ball_x <= 0 or ball_x >= screen_width:
                ball_x = screen_width // 2
                ball_y = screen_height // 2
                ball_speed_x *= -1

            # Send updated game state to clients
            data = pickle.dumps((paddle1_y, paddle2_y, ball_x, ball_y))
            for client in clients:
                client.sendall(data)

def handle_client(conn, player):
    global paddle1_y, paddle2_y

    while True:
        try:
            data = conn.recv(1024).decode()
            if not data:
                break
            
            with lock:
                if player == 1:  # Player 1 (Left Paddle)
                    if data == "UP" and paddle1_y > 0:
                        paddle1_y -= paddle_speed
                    elif data == "DOWN" and paddle1_y < screen_height - paddle_height:
                        paddle1_y += paddle_speed
                else:  # Player 2 (Right Paddle)
                    if data == "UP" and paddle2_y > 0:
                        paddle2_y -= paddle_speed
                    elif data == "DOWN" and paddle2_y < screen_height - paddle_height:
                        paddle2_y += paddle_speed

        except:
            break

    conn.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(2)
    print("Server started. Waiting for players...")

    for i in range(2):  # Accept two players
        conn, addr = server.accept()
        print(f"Player {i+1} connected from {addr}")
        clients.append(conn)
        threading.Thread(target=handle_client, args=(conn, i+1)).start()

    # Start game loop
    threading.Thread(target=game_loop, daemon=True).start()

start_server()

