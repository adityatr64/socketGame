import pygame
import socket
import threading
import struct

PORT = 5555
BUFFER_SIZE = 1024
SOCKET_BUFFER_SIZE = 16384  # Increased buffer size
FIXED_WIDTH, FIXED_HEIGHT = 960, 540  # Fixed internal resolution
PADDLE_WIDTH, PADDLE_HEIGHT = 10, 100
BALL_SIZE = 20
BALL_SPEED = 3
PADDLE_SPEED = 5    
GAME_SPEED = 60
NETWORK_UPDATE_FREQUENCY = 3  # Send updates every 3 frames
INTERPOLATION_FACTOR = 0.2  # Lowered for smoother interpoFIXED_HEIGHTlation

pygame.init()
screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
pygame.display.set_caption("P2P Pong")
clock = pygame.time.Clock()

# Track current window size
current_resolution = (FIXED_WIDTH, FIXED_HEIGHT)

def loading_screen():
    font = pygame.font.Font(None, 36)
    input_box_ip = pygame.Rect(200, 200, 400, 50)
    input_box_role = pygame.Rect(200, 300, 400, 50)
    dropdown_box = pygame.Rect(200, 400, 400, 50)

    color_inactive = pygame.Color('darkorange')
    color_active = pygame.Color('gold')
    color_hover = pygame.Color('yellow')

    ip_text = ''
    role_text = ''
    active_box = None

    # Dropdown options
    resolutions = ["400x225","960x540","800x450", "1280x720", "1920x1080"]
    selected_resolution = resolutions[1]  
    dropdown_open = False

    while True:
        screen.fill((0, 0, 0))
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if input_box_ip.collidepoint(event.pos):
                    active_box = 'ip'
                elif input_box_role.collidepoint(event.pos):
                    active_box = 'role'
                elif dropdown_box.collidepoint(event.pos):
                    dropdown_open = not dropdown_open
                else:
                    active_box = None
                    
                    # Only close dropdown if clicking outside dropdown area when it's open
                    if dropdown_open:
                        dropdown_area = pygame.Rect(200, 450, 400, 40 * len(resolutions))
                        if not dropdown_area.collidepoint(event.pos):
                            dropdown_open = False

                # Handle dropdown item selection
                if dropdown_open:
                    for i, res in enumerate(resolutions):
                        option_rect = pygame.Rect(200, 450 + i * 40, 400, 40)
                        if option_rect.collidepoint(event.pos):
                            selected_resolution = res
                            dropdown_open = False  # Close the dropdown
                            # Don't change resolution yet, just store the selection
                            break

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
                        return ip_text, role_text, selected_resolution
                    elif event.key == pygame.K_BACKSPACE:
                        role_text = role_text[:-1]
                    else:
                        role_text += event.unicode

        color_ip = color_active if active_box == 'ip' else color_inactive
        color_role = color_active if active_box == 'role' else color_inactive

        txt_surface_ip = font.render(ip_text, True, color_ip)
        txt_surface_role = font.render(role_text, True, color_role)
        txt_surface_res = font.render(selected_resolution, True, color_active)

        # Render input fields
        screen.blit(font.render("Enter Opponent's IP:", True, (255, 255, 255)), (200, 150))
        screen.blit(font.render("Are you hosting? (yes/no):", True, (255, 255, 255)), (200, 250))
        screen.blit(font.render("Select resolution:", True, (255, 255, 255)), (200, 350))
        screen.blit(txt_surface_ip, (input_box_ip.x + 10, input_box_ip.y + 10))
        screen.blit(txt_surface_role, (input_box_role.x + 10, input_box_role.y + 10))
        screen.blit(txt_surface_res, (dropdown_box.x + 10, dropdown_box.y + 10))

        pygame.draw.rect(screen, color_ip, input_box_ip, 2)
        pygame.draw.rect(screen, color_role, input_box_role, 2)
        pygame.draw.rect(screen, color_active, dropdown_box, 2)

        # Render dropdown options
        if dropdown_open:
            for i, res in enumerate(resolutions):
                option_rect = pygame.Rect(200, 450 + i * 40, 400, 40)

                # Highlight on hover
                if option_rect.collidepoint(mouse_pos):
                    pygame.draw.rect(screen, color_hover, option_rect)
                else:
                    pygame.draw.rect(screen, color_inactive, option_rect)

                screen.blit(font.render(res, True, (0, 0, 0)), (option_rect.x + 10, option_rect.y + 10))

        pygame.display.flip()
        clock.tick(GAME_SPEED)


def setup_network():
    peer_ip, role, res_text = loading_screen()
    is_host = role.lower() == "yes"

    # Parse the resolution
    global current_resolution
    try:
        width, height = map(int, res_text.split('x'))
        current_resolution = (width, height)
        pygame.display.set_mode(current_resolution, pygame.RESIZABLE)
    except:
        print("[ERROR] Invalid resolution format. Using default resolution.")
        current_resolution = (FIXED_WIDTH, FIXED_HEIGHT)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(10)  # Lower timeout for more responsive networking
    
    # Configure socket buffer sizes
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, SOCKET_BUFFER_SIZE)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, SOCKET_BUFFER_SIZE)

    if is_host:
        sock.bind(("0.0.0.0", PORT))
        print(f"[HOST] Waiting for client on {PORT}...")
        
        try:
            msg, peer_addr = sock.recvfrom(BUFFER_SIZE)
            if msg == b"HELLO":
                print(f"[HOST] Client connected from {peer_addr}")
                sock.sendto(b"HELLO_ACK", peer_addr)
            else:
                print("[HOST] Unexpected message. Connection failed.")
                exit()
        except socket.timeout:
            print("[HOST] No client connected. Timeout.")
            exit()
    
    else:
        sock.bind(("0.0.0.0", 0))
        print(f"[CLIENT] Bound to {sock.getsockname()[1]}")
        print(f"[CLIENT] Connecting to host {peer_ip}:{PORT}...")

        # More aggressive connection attempt
        for _ in range(5):  # Try multiple times
            sock.sendto(b"HELLO", (peer_ip, PORT))
            try:
                msg, host_addr = sock.recvfrom(BUFFER_SIZE)
                if msg == b"HELLO_ACK":
                    print("[CLIENT] Connected to host!")
                    peer_addr = host_addr  # Set peer_addr for the client
                    break
                else:
                    print("[CLIENT] Unexpected response from host.")
                    exit()
            except socket.timeout:
                print("[CLIENT] Retrying connection...")
                continue
        else:  # If the loop completes without a break
            print("[CLIENT] No response from host after multiple attempts. Timeout.")
            exit()

    return sock, peer_addr, is_host


def receive_data(sock, is_host, state, running):
    while running[0]:
        try:
            data, _ = sock.recvfrom(BUFFER_SIZE)
            packet_id, paddle_y, ball_x, ball_y, ball_speed_x, ball_speed_y, player_score, opponent_score = struct.unpack('!iiiiiiii', data)
            
            # Store the packet ID to detect packet loss
            last_packet_id = state.get('last_packet_id', 0)
            if packet_id > last_packet_id:
                state['last_packet_id'] = packet_id
                
                # Apply more sophisticated dead reckoning
                previous_y = state.get('opponent_paddle_y_previous', paddle_y)
                velocity = paddle_y - previous_y
                state['opponent_paddle_y_previous'] = paddle_y
                state['opponent_paddle_y_velocity'] = velocity
                state['opponent_paddle_y_target'] = paddle_y
                
                # Update ball state based on role
                if not is_host:
                    state['ball_x'] = ball_x
                    state['ball_y'] = ball_y
                    state['ball_speed_x'] = ball_speed_x
                    state['ball_speed_y'] = ball_speed_y
                
                state['player_score'] = opponent_score  # Opponent's paddle is our score
                state['opponent_score'] = player_score  # Our paddle is opponent's score
        except socket.timeout:
            # If timeout, apply prediction using stored velocity
            if 'opponent_paddle_y_velocity' in state:
                state['opponent_paddle_y_target'] += state['opponent_paddle_y_velocity'] * 0.5  # Reduce prediction effect
            continue
        except Exception as e:
            print(f"[ERROR] Receive error: {e}")
            continue


def handle_input(state):
    keys = pygame.key.get_pressed()
    if keys[pygame.K_w] and state['paddle_y'] > 0:
        state['paddle_y'] -= PADDLE_SPEED
    if keys[pygame.K_s] and state['paddle_y'] < FIXED_HEIGHT - PADDLE_HEIGHT:
        state['paddle_y'] += PADDLE_SPEED
    if keys[pygame.K_ESCAPE] or keys[pygame.K_q]:
        end_game()


def update_ball(state):
    state['ball_x'] += state['ball_speed_x']
    state['ball_y'] += state['ball_speed_y']

    if state['ball_y'] <= 0 or state['ball_y'] + BALL_SIZE >= FIXED_HEIGHT:
        state['ball_speed_y'] *= -1

    if (50 <= state['ball_x'] <= 50 + PADDLE_WIDTH and state['paddle_y'] <= state['ball_y'] + BALL_SIZE // 2 <= state['paddle_y'] + PADDLE_HEIGHT) or \
       (FIXED_WIDTH - 50 - PADDLE_WIDTH <= state['ball_x'] + BALL_SIZE <= FIXED_WIDTH - 50 and state['opponent_paddle_y'] <= state['ball_y'] + BALL_SIZE // 2 <= state['opponent_paddle_y'] + PADDLE_HEIGHT):
        state['ball_speed_x'] *= -1

    if state['ball_x'] <= 0:  # Ball goes past the left side (Player Loses)
        state['opponent_score'] += 1
        reset_ball(state)

    if state['ball_x'] >= FIXED_WIDTH:  # Ball goes past the right side (Opponent Loses)
        state['player_score'] += 1
        reset_ball(state)


def draw_game(state, is_host):
    fixed_surface = pygame.Surface((FIXED_WIDTH, FIXED_HEIGHT))
    fixed_surface.fill((0, 0, 0))

    ball_x = state['ball_x']
    if not is_host:
        paddle_x = FIXED_WIDTH - 50 - PADDLE_WIDTH
        opponent_x = 50
    else:
        paddle_x = 50
        opponent_x = FIXED_WIDTH - 50 - PADDLE_WIDTH

    # Draw network quality indicator
    network_lag = abs(state['opponent_paddle_y'] - state['opponent_paddle_y_target'])
    indicator_color = (0, 255, 0)  # Green by default
    if network_lag > 20:
        indicator_color = (255, 255, 0)  # Yellow
    if network_lag > 50:
        indicator_color = (255, 0, 0)  # Red
    pygame.draw.circle(fixed_surface, indicator_color, (20, 20), 10)

    # Draw game elements
    pygame.draw.rect(fixed_surface, (255, 255, 255), (paddle_x, state['paddle_y'], PADDLE_WIDTH, PADDLE_HEIGHT))
    pygame.draw.rect(fixed_surface, (255, 255, 255), (opponent_x, state['opponent_paddle_y'], PADDLE_WIDTH, PADDLE_HEIGHT))
    pygame.draw.ellipse(fixed_surface, (255, 255, 255), (ball_x, state['ball_y'], BALL_SIZE, BALL_SIZE))
    pygame.draw.aaline(fixed_surface, (255, 255, 255), (FIXED_WIDTH // 2, 0), (FIXED_WIDTH // 2, FIXED_HEIGHT))

    font = pygame.font.Font(None, 36)
    score_text = font.render(f"{state['player_score']}   {state['opponent_score']}", True, (255, 255, 255))
    fixed_surface.blit(score_text, (FIXED_WIDTH // 2 - score_text.get_width() // 2, 10))

    scaled_surface = pygame.transform.scale(fixed_surface, current_resolution)
    screen.blit(scaled_surface, (0, 0))
    pygame.display.flip()


def main():
    sock, peer_addr, is_host = setup_network()

    state = {
        'paddle_y': (FIXED_HEIGHT - PADDLE_HEIGHT) // 2,
        'opponent_paddle_y': (FIXED_HEIGHT - PADDLE_HEIGHT) // 2,
        'opponent_paddle_y_target': (FIXED_HEIGHT - PADDLE_HEIGHT) // 2,
        'opponent_paddle_y_previous': (FIXED_HEIGHT - PADDLE_HEIGHT) // 2,
        'opponent_paddle_y_velocity': 0,
        'ball_x': FIXED_WIDTH // 2,
        'ball_y': FIXED_HEIGHT // 2,
        'ball_speed_x': BALL_SPEED * (1 if is_host else -1),  # Ensure initial direction is correct
        'ball_speed_y': BALL_SPEED,
        'player_score': 0,
        'opponent_score': 0,
        'last_packet_id': 0
    }

    running = [True]
    frame_counter = 0
    packet_id = 0

    threading.Thread(target=receive_data, args=(sock, is_host, state, running), daemon=True).start()

    while running[0]:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running[0] = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:  # Add pause functionality
                    paused = True
                    while paused:
                        for pause_event in pygame.event.get():
                            if pause_event.type == pygame.QUIT:
                                running[0] = False
                                paused = False
                            elif pause_event.type == pygame.KEYDOWN and pause_event.key == pygame.K_p:
                                paused = False
                        pygame.time.wait(100)

        handle_input(state)
        if is_host:
            update_ball(state)
        elif frame_counter % 2 == 0:  # Client-side prediction for smoother ball movement
            # Only apply client prediction if not receiving frequent updates
            if state.get('last_update_time', 0) + 0.1 < pygame.time.get_ticks() / 1000:
                state['ball_x'] += state['ball_speed_x']
                state['ball_y'] += state['ball_speed_y']
                
                # Basic collision prediction
                if state['ball_y'] <= 0 or state['ball_y'] + BALL_SIZE >= FIXED_HEIGHT:
                    state['ball_speed_y'] *= -1

        # Send network updates less frequently to reduce network load
        if frame_counter % NETWORK_UPDATE_FREQUENCY == 0:
            packet_id += 1
            game_state = struct.pack('!iiiiiiii',
                packet_id,
                state['paddle_y'], 
                state['ball_x'], 
                state['ball_y'],
                state['ball_speed_x'], 
                state['ball_speed_y'],
                state['player_score'], 
                state['opponent_score']
            )
            sock.sendto(game_state, peer_addr)
            
        # More gradual interpolation for smoother movement
        state['opponent_paddle_y'] += (state['opponent_paddle_y_target'] - state['opponent_paddle_y']) * INTERPOLATION_FACTOR
        
        draw_game(state, is_host)
        frame_counter += 1
        clock.tick(GAME_SPEED)

    end_game()


def end_game():
    print("Exiting game...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.close()
    except:
        pass
    pygame.quit()
    exit()


def reset_ball(state):
    state['ball_x'], state['ball_y'] = FIXED_WIDTH // 2, FIXED_HEIGHT // 2
    state['ball_speed_x'] = BALL_SPEED
    state['ball_speed_y'] = BALL_SPEED


if __name__ == "__main__":
    main()