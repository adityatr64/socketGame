import pygame
import socket
import threading
import pickle

# Constants
PORT = 5555
BUFFER_SIZE = 1024
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
PADDLE_WIDTH, PADDLE_HEIGHT = 10, 100
BALL_SIZE = 20
BALL_SPEED = 3
PADDLE_SPEED = 5
GAME_SPEED = 60

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("P2P Pong")
clock = pygame.time.Clock()


def loading_screen():
    font = pygame.font.Font(None, 36)
    input_box_ip = pygame.Rect(200, 200, 400, 50)
    input_box_role = pygame.Rect(200, 300, 400, 50)
    color_inactive = pygame.Color('darkorange')
    color_active = pygame.Color('gold')
    ip_text = ''
    role_text = ''
    active_box = None
    
    while True:
        screen.fill((0, 0, 0))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if input_box_ip.collidepoint(event.pos):
                    active_box = 'ip'
                elif input_box_role.collidepoint(event.pos):
                    active_box = 'role'
                else:
                    active_box = None
            if event.type == pygame.KEYDOWN:
                if active_box == 'ip':
                    if event.key == pygame.K_RETURN:
                        active_box = 'role'
                    elif event.key == pygame.K_BACKSPACE:
                        ip_text = ip_text[:-1]
                    else:
                        ip_text += event.unicode
                elif active_box == 'role':
                    if event.key == pygame.K_RETURN and role_text.lower() in ['yes', 'no']:
                        return ip_text, role_text
                    elif event.key == pygame.K_BACKSPACE:
                        role_text = role_text[:-1]
                    else:
                        role_text += event.unicode

        color_ip = color_active if active_box == 'ip' else color_inactive
        color_role = color_active if active_box == 'role' else color_inactive

        txt_surface_ip = font.render(ip_text, True, color_ip)
        txt_surface_role = font.render(role_text, True, color_role)

        screen.blit(font.render("Enter Opponent's IP:", True, (255, 255, 255)), (200, 150))
        screen.blit(font.render("Are you hosting? (yes/no):", True, (255, 255, 255)), (200, 250))
        screen.blit(txt_surface_ip, (input_box_ip.x + 10, input_box_ip.y + 10))
        screen.blit(txt_surface_role, (input_box_role.x + 10, input_box_role.y + 10))

        pygame.draw.rect(screen, color_ip, input_box_ip, 2)
        pygame.draw.rect(screen, color_role, input_box_role, 2)
        
        pygame.display.flip()
        clock.tick(GAME_SPEED)


def setup_network():
    peer_ip, role = loading_screen()
    is_host = role.lower() == "yes"

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PORT))

    if is_host:
        peer_addr = (peer_ip, PORT)
    else:
        sock.sendto(b"HELLO", (peer_ip, PORT))
        _, peer_addr = sock.recvfrom(BUFFER_SIZE)

    return sock, peer_addr, is_host


def receive_data(sock, is_host, state, running):
    while running[0]:
        try:
            data, _ = sock.recvfrom(BUFFER_SIZE)
            received_data = pickle.loads(data)
            state['opponent_paddle_y'], state['ball_x'], state['ball_y'], state['ball_speed_x'], state['ball_speed_y'] = received_data

            if not is_host:
                state['ball_x'], state['ball_y'] = received_data[1:3]
        except:
            continue


def handle_input(state):
    keys = pygame.key.get_pressed()
    if keys[pygame.K_w] and state['paddle_y'] > 0:
        state['paddle_y'] -= PADDLE_SPEED
    if keys[pygame.K_s] and state['paddle_y'] < SCREEN_HEIGHT - PADDLE_HEIGHT:
        state['paddle_y'] += PADDLE_SPEED
    if keys[pygame.K_ESCAPE] or keys[pygame.K_q]:
        end_game()


def update_ball(state):
    state['ball_x'] += state['ball_speed_x']
    state['ball_y'] += state['ball_speed_y']

    if state['ball_y'] <= 0 or state['ball_y'] + BALL_SIZE >= SCREEN_HEIGHT:
        state['ball_speed_y'] *= -1

    if (50 <= state['ball_x'] <= 50 + PADDLE_WIDTH and state['paddle_y'] <= state['ball_y'] + BALL_SIZE // 2 <= state['paddle_y'] + PADDLE_HEIGHT) or \
       (SCREEN_WIDTH - 50 - PADDLE_WIDTH <= state['ball_x'] + BALL_SIZE <= SCREEN_WIDTH - 50 and state['opponent_paddle_y'] <= state['ball_y'] + BALL_SIZE // 2 <= state['opponent_paddle_y'] + PADDLE_HEIGHT):
        state['ball_speed_x'] *= -1

    if state['ball_x'] <= 0 or state['ball_x'] >= SCREEN_WIDTH:
        state['ball_x'], state['ball_y'] = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        state['ball_speed_x'] *= -1


def draw_game(state, is_host):
    screen.fill((0, 0, 0))
    pygame.draw.rect(screen, (255, 255, 255), (50, state['paddle_y'], PADDLE_WIDTH, PADDLE_HEIGHT))
    pygame.draw.rect(screen, (255, 255, 255), (SCREEN_WIDTH - 50 - PADDLE_WIDTH, state['opponent_paddle_y'], PADDLE_WIDTH, PADDLE_HEIGHT))
    pygame.draw.ellipse(screen, (255, 255, 255), (state['ball_x'], state['ball_y'], BALL_SIZE, BALL_SIZE))
    pygame.draw.aaline(screen, (255, 255, 255), (SCREEN_WIDTH // 2, 0), (SCREEN_WIDTH // 2, SCREEN_HEIGHT))
    pygame.display.flip()


def main():
    sock, peer_addr, is_host = setup_network()

    state = {
        'paddle_y': (SCREEN_HEIGHT - PADDLE_HEIGHT) // 2,
        'opponent_paddle_y': (SCREEN_HEIGHT - PADDLE_HEIGHT) // 2,
        'ball_x': SCREEN_WIDTH // 2,
        'ball_y': SCREEN_HEIGHT // 2,
        'ball_speed_x': BALL_SPEED,
        'ball_speed_y': BALL_SPEED,
    }

    running = [True]

    threading.Thread(target=receive_data, args=(sock, is_host, state, running), daemon=True).start()

    while running[0]:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running[0] = False

        handle_input(state)
        if is_host:
            update_ball(state)

        game_state = pickle.dumps((state['paddle_y'], state['ball_x'], state['ball_y'], state['ball_speed_x'], state['ball_speed_y']))
        sock.sendto(game_state, peer_addr)

        draw_game(state, is_host)
        clock.tick(GAME_SPEED)

    end_game()

def end_game():
    print("Exiting game...")
    socket.socket(socket.AF_INET, socket.SOCK_DGRAM).close()
    pygame.quit()
    exit()

if __name__ == "__main__":
    main()
