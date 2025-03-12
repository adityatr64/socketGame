import pygame
import socket
import threading
import pickle

# Configurations
PORT = 5555
BUFFER_SIZE = 1024
screen_width, screen_height = 800, 600
paddle_width, paddle_height = 10, 100
ball_size = 20

# Networking Setup
peer_ip = input("Enter opponent's IP: ")
role = input("Are you hosting? (yes/no): ")
is_host = role.lower() == "yes"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", PORT))

if is_host:
    peer_addr = (peer_ip, PORT)
else:
    sock.sendto(b"HELLO", (peer_ip, PORT))
    data, peer_addr = sock.recvfrom(BUFFER_SIZE)

# Pygame Initialization
pygame.init()
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("P2P Pong")

# Game State
paddle_y = (screen_height - paddle_height) // 2
opponent_paddle_y = (screen_height - paddle_height) // 2
ball_x, ball_y = screen_width // 2, screen_height // 2
ball_speed_x, ball_speed_y = 3, 3
running = True

# Function to receive updates
def receive_data():
    global opponent_paddle_y, ball_x, ball_y, ball_speed_x, ball_speed_y
    while running:
        try:
            data, _ = sock.recvfrom(BUFFER_SIZE)
            received_paddle, ball_x, ball_y, ball_speed_x, ball_speed_y = pickle.loads(data)
            opponent_paddle_y = received_paddle
        except:
            break

threading.Thread(target=receive_data, daemon=True).start()

# Main Game Loop
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    keys = pygame.key.get_pressed()
    if keys[pygame.K_w] and paddle_y > 0:
        paddle_y -= 5
    if keys[pygame.K_s] and paddle_y < screen_height - paddle_height:
        paddle_y += 5
    
    # Host manages ball physics
    if is_host:
        ball_x += ball_speed_x
        ball_y += ball_speed_y

        if ball_y <= 0 or ball_y >= screen_height - ball_size:
            ball_speed_y *= -1

        if (50 < ball_x < 60 and paddle_y < ball_y < paddle_y + paddle_height) or \
           (screen_width - 60 < ball_x < screen_width - 50 and opponent_paddle_y < ball_y < opponent_paddle_y + paddle_height):
            ball_speed_x *= -1

        if ball_x <= 0 or ball_x >= screen_width:
            ball_x, ball_y = screen_width // 2, screen_height // 2
            ball_speed_x *= -1
    
    # Send only player's paddle position
    game_state = pickle.dumps((paddle_y, ball_x, ball_y, ball_speed_x, ball_speed_y))
    sock.sendto(game_state, peer_addr)

    # Drawing
    screen.fill((0, 0, 0))
    if is_host:
        pygame.draw.rect(screen, (255, 255, 255), (50, paddle_y, paddle_width, paddle_height))
        pygame.draw.rect(screen, (255, 255, 255), (screen_width - 50 - paddle_width, opponent_paddle_y, paddle_width, paddle_height))
    else:
        pygame.draw.rect(screen, (255, 255, 255), (screen_width - 50 - paddle_width, paddle_y, paddle_width, paddle_height))
        pygame.draw.rect(screen, (255, 255, 255), (50, opponent_paddle_y, paddle_width, paddle_height))
    pygame.draw.ellipse(screen, (255, 255, 255), (ball_x, ball_y, ball_size, ball_size))
    pygame.draw.aaline(screen, (255, 255, 255), (screen_width // 2, 0), (screen_width // 2, screen_height))
    
    pygame.display.flip()
    pygame.time.Clock().tick(60)

sock.close()
pygame.quit()

