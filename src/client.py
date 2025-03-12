
import pygame
import socket
import pickle
import threading

SERVER_IP = "127.0.0.1"
PORT = 5555

pygame.init()

screen_width = 800
screen_height = 600

black = (0, 0, 0)
white = (255, 255, 255)

paddle_width = 10
paddle_height = 100
ball_size = 20

screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Pong Multiplayer")

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((SERVER_IP, PORT))

player_number = int(client.recv(1024).decode())

paddle_y = (screen_height - paddle_height) // 2
opponent_paddle_y = (screen_height - paddle_height) // 2
ball_x = screen_width // 2
ball_y = screen_height // 2
running = True

def receive_data():
    global paddle_y, opponent_paddle_y, ball_x, ball_y

    while True:
        try:
            data = client.recv(1024)
            if not data:
                break

            paddle1_y, paddle2_y, ball_x, ball_y = pickle.loads(data)
            
            if player_number == 1:
                paddle_y = paddle1_y
                opponent_paddle_y = paddle2_y
            else:
                paddle_y = paddle2_y
                opponent_paddle_y = paddle1_y
        except:
            break

threading.Thread(target=receive_data, daemon=True).start()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()
    if keys[pygame.K_w]:
        client.sendall("UP".encode())
    if keys[pygame.K_s]:
        client.sendall("DOWN".encode())
    if keys[pygame.K_ESCAPE]:
        client.sendall("QUIT".encode())

    screen.fill(black)

    # Draw paddles based on player number
    if player_number == 1:
        pygame.draw.rect(screen, white, (50, paddle_y, paddle_width, paddle_height))  # Your paddle (left)
        pygame.draw.rect(screen, white, (screen_width - 50 - paddle_width, opponent_paddle_y, paddle_width, paddle_height))  # Opponent paddle (right)
    else:
        pygame.draw.rect(screen, white, (screen_width - 50 - paddle_width, paddle_y, paddle_width, paddle_height))  # Your paddle (right)
        pygame.draw.rect(screen, white, (50, opponent_paddle_y, paddle_width, paddle_height))  # Opponent paddle (left)

    pygame.draw.ellipse(screen, white, (ball_x, ball_y, ball_size, ball_size))
    pygame.draw.aaline(screen, white, (screen_width // 2, 0), (screen_width // 2, screen_height))

    pygame.display.flip()
    pygame.time.Clock().tick(60)

client.close()
pygame.quit()