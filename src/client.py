import pygame
import socket
import pickle
import threading

# Server details
SERVER_IP = "127.0.0.1"  # Change to server's IP if on a different machine
PORT = 5555

# Initialize Pygame
pygame.init()

# Screen dimensions
screen_width = 800
screen_height = 600

# Colors
black = (0, 0, 0)
white = (255, 255, 255)

# Paddle dimensions
paddle_width = 10
paddle_height = 100
ball_size = 20

# Create screen
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Pong Multiplayer")

# Connect to server
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((SERVER_IP, PORT))

# Paddle positions (initial values)
paddle_x = 50  # Default for Player 1, updated later
paddle_y = (screen_height - paddle_height) // 2

# Ball position
ball_x = screen_width // 2
ball_y = screen_height // 2

# Variable to track if this client is Player 2
is_player_2 = False

def receive_data():
    """Receive game state updates from the server."""
    global paddle_y, ball_x, ball_y, is_player_2

    while True:
        try:
            data = client.recv(1024)
            if not data:
                break

            # Unpack game state from server
            paddle1_y, paddle2_y, ball_x, ball_y = pickle.loads(data)

            # Determine which paddle this client controls
            if is_player_2:
                paddle_y = paddle2_y
            else:
                paddle_y = paddle1_y

        except Exception as e:
            print(f"Error receiving data: {e}")
            break

# Start thread to receive updates from server
threading.Thread(target=receive_data, daemon=True).start()

# Game loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Key press handling
    keys = pygame.key.get_pressed()
    if keys[pygame.K_w]:
        client.sendall("UP".encode())
    if keys[pygame.K_s]:
        client.sendall("DOWN".encode())

    # Drawing
    screen.fill(black)
    pygame.draw.rect(screen, white, (50, paddle_y, paddle_width, paddle_height))  # Player 1 paddle
    pygame.draw.rect(screen, white, (screen_width - 50 - paddle_width, paddle_y, paddle_width, paddle_height))  # Player 2 paddle
    pygame.draw.ellipse(screen, white, (ball_x, ball_y, ball_size, ball_size))  # Ball
    pygame.draw.aaline(screen, white, (screen_width // 2, 0), (screen_width // 2, screen_height))  # Middle line

    pygame.display.flip()
    pygame.time.Clock().tick(60)

client.close()
pygame.quit()

