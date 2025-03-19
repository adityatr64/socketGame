import pygame
import socket
import threading
import struct
import json
import time
import random
import string

PORT = 42069
BUFFER_SIZE = 1024
SOCKET_BUFFER_SIZE = 16384 
FIXED_WIDTH, FIXED_HEIGHT = 960, 540
PADDLE_WIDTH, PADDLE_HEIGHT = 10, 100
BALL_SIZE = 20
BALL_SPEED = 3
PADDLE_SPEED = 5    
GAME_SPEED = 60
NETWORK_UPDATE_FREQUENCY = 3
INTERPOLATION_FACTOR = 0.2  

pygame.init()
screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
pygame.display.set_caption("P2P Pong")
clock = pygame.time.Clock()

# Track current window size
current_resolution = (FIXED_WIDTH, FIXED_HEIGHT)

def generate_room_id():
    """Generate a random 6-character room ID"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def draw_text_input(screen, rect, text, active, font, color_inactive, color_active):
    """Helper function for drawing text input boxes"""
    color = color_active if active else color_inactive
    pygame.draw.rect(screen, color, rect, 2)
    text_surface = font.render(text, True, color)
    screen.blit(text_surface, (rect.x + 5, rect.y + 5))

def loading_screen():
    font = pygame.font.Font(None, 36)

    input_box_username = pygame.Rect(200, 150, 400, 50)
    input_box_room = pygame.Rect(200, 250, 400, 50)  # Moved up since IP is removed

    host_button = pygame.Rect(200, 350, 195, 50)
    join_button = pygame.Rect(405, 350, 195, 50)

    dropdown_box = pygame.Rect(200, 450, 400, 50)  # Moved up

    color_inactive = pygame.Color('darkorange')
    color_active = pygame.Color('gold')

    username_text = 'Player'
    room_text = ''
    active_box = None
    mode = None

    resolutions = ["400x225", "960x540", "800x450", "1280x720", "1920x1080"]
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
                if input_box_username.collidepoint(event.pos):
                    active_box = 'username'
                elif input_box_room.collidepoint(event.pos):
                    active_box = 'room'
                elif host_button.collidepoint(event.pos):
                    mode = 'host'
                    room_text = generate_room_id()
                elif join_button.collidepoint(event.pos):
                    mode = 'join'
                elif dropdown_box.collidepoint(event.pos):
                    dropdown_open = not dropdown_open
                else:
                    active_box = None
                    if dropdown_open:
                        dropdown_area = pygame.Rect(200, 500, 400, 40 * len(resolutions))
                        if not dropdown_area.collidepoint(event.pos):
                            dropdown_open = False

                if dropdown_open:
                    for i, res in enumerate(resolutions):
                        option_rect = pygame.Rect(200, 500 + i * 40, 400, 40)
                        if option_rect.collidepoint(event.pos):
                            selected_resolution = res
                            dropdown_open = False
                            break

            if event.type == pygame.KEYDOWN:
                if active_box:
                    if event.key == pygame.K_RETURN:
                        if mode and active_box == 'room' and (mode == 'join' and room_text or mode == 'host'):
                            return username_text, mode, room_text, selected_resolution
                    elif event.key == pygame.K_BACKSPACE:
                        if active_box == 'username':
                            username_text = username_text[:-1]
                        elif active_box == 'room':
                            room_text = room_text[:-1]
                    else:
                        if active_box == 'username':
                            username_text += event.unicode
                        elif active_box == 'room':
                            room_text += event.unicode.upper()

        # UI rendering
        screen.blit(font.render("P2P Pong Room System", True, (255, 255, 255)), (270, 50))

        # Username field
        screen.blit(font.render("Username:", True, (255, 255, 255)), (200, 120))
        draw_text_input(screen, input_box_username, username_text, active_box == 'username', font, color_inactive, color_active)

        # Room ID field
        room_label = "Room ID:" if mode == 'join' else "Your Room ID:"
        screen.blit(font.render(room_label, True, (255, 255, 255)), (200, 220))
        draw_text_input(screen, input_box_room, room_text, active_box == 'room', font, color_inactive, color_active)

        # Host/Join buttons
        host_color = color_active if mode == 'host' else color_inactive
        join_color = color_active if mode == 'join' else color_inactive

        pygame.draw.rect(screen, host_color, host_button, 0)
        pygame.draw.rect(screen, join_color, join_button, 0)

        screen.blit(font.render("Host", True, (0, 0, 0)), (host_button.x + 70, host_button.y + 12))
        screen.blit(font.render("Join", True, (0, 0, 0)), (join_button.x + 70, join_button.y + 12))

        # Resolution dropdown
        screen.blit(font.render("Resolution:", True, (255, 255, 255)), (200, 420))
        txt_surface_res = font.render(selected_resolution, True, color_active)
        screen.blit(txt_surface_res, (dropdown_box.x + 10, dropdown_box.y + 10))
        pygame.draw.rect(screen, color_active, dropdown_box, 2)

        # Play button
        if mode:
            play_button = pygame.Rect(300, 550, 200, 60)
            play_color = color_active if (mode == 'host' or (mode == 'join' and room_text)) else color_inactive
            pygame.draw.rect(screen, play_color, play_button, 0)
            screen.blit(font.render("PLAY", True, (0, 0, 0)), (play_button.x + 70, play_button.y + 15))

            if event.type == pygame.MOUSEBUTTONDOWN and play_button.collidepoint(event.pos):
                if mode == 'host' or (mode == 'join' and room_text):
                    return username_text, mode, room_text, selected_resolution

        # Render dropdown options
        if dropdown_open:
            for i, res in enumerate(resolutions):
                option_rect = pygame.Rect(200, 500 + i * 40, 400, 40)

                if option_rect.collidepoint(mouse_pos):
                    pygame.draw.rect(screen, pygame.Color('yellow'), option_rect)
                else:
                    pygame.draw.rect(screen, color_inactive, option_rect)

                screen.blit(font.render(res, True, (0, 0, 0)), (option_rect.x + 10, option_rect.y + 10))

        pygame.display.flip()
        clock.tick(GAME_SPEED)

def discover_host(room_id, timeout=5):
    """Send a UDP broadcast to discover a host with the given room ID."""
    discovery_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    discovery_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    discovery_sock.settimeout(timeout)

    message = json.dumps({"type": "DISCOVER", "room": room_id}).encode('utf-8')

    print(f"[CLIENT] Broadcasting discovery request for room {room_id}...")
    discovery_sock.sendto(message, ('255.255.255.255', PORT))

    try:
        while True:
            response, addr = discovery_sock.recvfrom(BUFFER_SIZE)
            print(f"[CLIENT] Received response from {addr}: {response}")  # Debugging log

            data = json.loads(response.decode('utf-8'))
            if data.get("type") == "HOST_FOUND" and data.get("room") == room_id:
                print(f"[CLIENT] Host found at {addr[0]}")
                return addr[0]
    except socket.timeout:
        print("[CLIENT] No host found.")
        return None
    finally:
        discovery_sock.close()



def handle_discovery_requests(sock, room_id):
    """Continuously listen for discovery requests and respond to clients."""
    sock.settimeout(5)  # Prevent infinite blocking

    while True:
        try:
            data, addr = sock.recvfrom(BUFFER_SIZE)
            print(f"[HOST] Received message from {addr}: {data}")  # Debugging log

            request = json.loads(data.decode('utf-8'))

            if request.get("type") == "DISCOVER":
                print(f"[HOST] Received discovery request for room {request.get('room')}")

            if request.get("type") == "DISCOVER" and request.get("room") == room_id:
                print(f"[HOST] Sending discovery response to {addr}")
                response = json.dumps({"type": "HOST_FOUND", "room": room_id}).encode('utf-8')
                sock.sendto(response, addr)  # Send the host's IP back

        except socket.timeout:
            continue  # Keep listening
        except json.JSONDecodeError:
            print("[HOST] Invalid discovery message received")



def setup_network():
    username, mode, room_id, res_text = loading_screen()
    is_host = mode == 'host'

    global current_resolution
    try:
        width, height = map(int, res_text.split('x'))
        current_resolution = (width, height)
        pygame.display.set_mode(current_resolution, pygame.RESIZABLE)
    except:
        print("[ERROR] Invalid resolution format. Using default resolution.")
        current_resolution = (FIXED_WIDTH, FIXED_HEIGHT)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(10)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, SOCKET_BUFFER_SIZE)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, SOCKET_BUFFER_SIZE)

    font = pygame.font.Font(None, 48)
    
    if is_host:
        sock.bind(("0.0.0.0", PORT))  # Ensure binding to all interfaces
        print(f"[HOST] Room created: {room_id}")
        print(f"[HOST] Waiting for player to join...")

        # Start the discovery response thread
        discovery_thread = threading.Thread(target=handle_discovery_requests, args=(sock, room_id), daemon=True)
        discovery_thread.start()


        waiting_text = f"Waiting for players to join Room: {room_id}..."
        waiting_surface = font.render(waiting_text, True, (255, 255, 255))
        screen.fill((0, 0, 0))
        screen.blit(waiting_surface, (current_resolution[0]//2 - waiting_surface.get_width()//2, 
                                     current_resolution[1]//2 - waiting_surface.get_height()//2))
        pygame.display.flip()

        try:
            while True:
                msg, peer_addr = sock.recvfrom(BUFFER_SIZE)
                try:
                    data = json.loads(msg.decode('utf-8'))
                    if data.get('type') == 'JOIN' and data.get('room') == room_id:
                        peer_username = data.get('username', 'Player 2')
                        print(f"[HOST] Player {peer_username} joined from {peer_addr}")
                        
                        ack_data = {
                            'type': 'JOIN_ACK',
                            'username': username,
                            'room': room_id
                        }
                        sock.sendto(json.dumps(ack_data).encode('utf-8'), peer_addr)
                        break
                    else:
                        print(f"[HOST] Invalid join request: {data}")
                except json.JSONDecodeError:
                    print(f"[HOST] Received invalid message format")
        except socket.timeout:
            print("[HOST] No player joined. Timeout.")
            exit()
    
    else:  # Client mode
        sock.bind(("0.0.0.0", 0))
        print(f"[CLIENT] Bound to {sock.getsockname()[1]}")

        server_ip = discover_host(room_id)
        if not server_ip:
            print("[CLIENT] Failed to find host. Exiting.")
            exit()

        print(f"[CLIENT] Joining room {room_id} on {server_ip}...")

        connecting_text = f"Connecting to Room: {room_id}..."
        connecting_surface = font.render(connecting_text, True, (255, 255, 255))
        screen.fill((0, 0, 0))
        screen.blit(connecting_surface, (current_resolution[0]//2 - connecting_surface.get_width()//2, 
                                        current_resolution[1]//2 - connecting_surface.get_height()//2))
        pygame.display.flip()

        join_data = {
            'type': 'JOIN',
            'username': username,
            'room': room_id
        }
        
        for attempt in range(5):
            sock.sendto(json.dumps(join_data).encode('utf-8'), (server_ip, PORT))
            try:
                msg, host_addr = sock.recvfrom(BUFFER_SIZE)
                data = json.loads(msg.decode('utf-8'))
                if data.get('type') == 'JOIN_ACK' and data.get('room') == room_id:
                    peer_username = data.get('username', 'Host')
                    print(f"[CLIENT] Connected to host {peer_username}!")
                    peer_addr = host_addr
                    break
                else:
                    print(f"[CLIENT] Unexpected response: {data}")
            except (json.JSONDecodeError, socket.timeout):
                print(f"[CLIENT] Connection attempt {attempt+1} timed out. Retrying...")
                connecting_text = f"Connecting to Room: {room_id}... (Attempt {attempt+2}/5)"
                connecting_surface = font.render(connecting_text, True, (255, 255, 255))
                screen.fill((0, 0, 0))
                screen.blit(connecting_surface, (current_resolution[0]//2 - connecting_surface.get_width()//2, 
                                              current_resolution[1]//2 - connecting_surface.get_height()//2))
                pygame.display.flip()
                continue
        else:
            print("[CLIENT] Failed to join room after multiple attempts.")
            exit()

    for i in range(3, 0, -1):
        screen.fill((0, 0, 0))
        countdown_text = f"Starting game in {i}..."
        countdown_surface = font.render(countdown_text, True, (255, 255, 255))
        screen.blit(countdown_surface, (current_resolution[0]//2 - countdown_surface.get_width()//2, 
                                       current_resolution[1]//2 - countdown_surface.get_height()//2))
        pygame.display.flip()
        time.sleep(1)

    pygame.display.set_caption(f"P2P Pong - Room: {room_id} - {username} vs {peer_username}")
    
    return sock, peer_addr, is_host, username, peer_username



def receive_data(sock, is_host, state, running):
    while running[0]:
        try:
            data, _ = sock.recvfrom(BUFFER_SIZE)
            
            # First try to decode as JSON for system messages
            try:
                json_data = json.loads(data.decode('utf-8'))
                if json_data.get('type') == 'DISCONNECT':
                    print(f"[INFO] Peer disconnected: {json_data.get('reason', 'No reason provided')}")
                    state['disconnected'] = True
                    running[0] = False
                    continue
            except:
                # Not JSON, try to unpack game state
                try:
                    packet_id, paddle_y, ball_x, ball_y, ball_speed_x, ball_speed_y, left_score, right_score, score_changed = struct.unpack('!iiiiiiiii', data)
                    
                    last_packet_id = state.get('last_packet_id', 0)
                    if packet_id > last_packet_id:
                        state['last_packet_id'] = packet_id
                        
                        previous_y = state.get('opponent_paddle_y_previous', paddle_y)
                        velocity = paddle_y - previous_y
                        state['opponent_paddle_y_previous'] = paddle_y
                        state['opponent_paddle_y_velocity'] = velocity
                        state['opponent_paddle_y_target'] = paddle_y
                        
                        if not is_host:
                            state['ball_x'] = ball_x
                            state['ball_y'] = ball_y
                            state['ball_speed_x'] = ball_speed_x
                            state['ball_speed_y'] = ball_speed_y
                        
                        if score_changed:
                            state['left_score'] = left_score
                            state['right_score'] = right_score
                            state['last_score_packet_id'] = packet_id
                except:
                    print("[ERROR] Failed to parse game state data")
                    
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
        end_game(state)


def update_ball(state):
    score_changed = False
    state['ball_x'] += state['ball_speed_x']
    state['ball_y'] += state['ball_speed_y']

    if state['ball_y'] <= 0 or state['ball_y'] + BALL_SIZE >= FIXED_HEIGHT:
        state['ball_speed_y'] *= -1

    if (50 <= state['ball_x'] <= 50 + PADDLE_WIDTH and state['paddle_y'] <= state['ball_y'] + BALL_SIZE // 2 <= state['paddle_y'] + PADDLE_HEIGHT) or \
       (FIXED_WIDTH - 50 - PADDLE_WIDTH <= state['ball_x'] + BALL_SIZE <= FIXED_WIDTH - 50 and state['opponent_paddle_y'] <= state['ball_y'] + BALL_SIZE // 2 <= state['opponent_paddle_y'] + PADDLE_HEIGHT):
        state['ball_speed_x'] *= -1

    if state['ball_x'] <= 0:  
        state['right_score'] += 1  
        score_changed = True
        reset_ball(state)

    if state['ball_x'] >= FIXED_WIDTH:
        state['left_score'] += 1 
        score_changed = True
        reset_ball(state)
        
    return score_changed


def draw_game(state, is_host, username, peer_username):
    fixed_surface = pygame.Surface((FIXED_WIDTH, FIXED_HEIGHT))
    fixed_surface.fill((0, 0, 0))

    ball_x = state['ball_x']
    if not is_host:
        paddle_x = FIXED_WIDTH - 50 - PADDLE_WIDTH
        opponent_x = 50
        left_name = peer_username
        right_name = username
    else:
        paddle_x = 50
        opponent_x = FIXED_WIDTH - 50 - PADDLE_WIDTH
        left_name = username
        right_name = peer_username

    # Draw network quality indicator
    network_lag = abs(state['opponent_paddle_y'] - state['opponent_paddle_y_target'])
    indicator_color = (0, 255, 0)  # Green by default
    if network_lag > 20:
        indicator_color = (255, 255, 0)  # Yellow
    if network_lag > 50:
        indicator_color = (255, 0, 0)  # Red
    pygame.draw.circle(fixed_surface, indicator_color, (20, 20), 10)

    # Draw paddles and ball
    pygame.draw.rect(fixed_surface, (255, 255, 255), (paddle_x, state['paddle_y'], PADDLE_WIDTH, PADDLE_HEIGHT))
    pygame.draw.rect(fixed_surface, (255, 255, 255), (opponent_x, state['opponent_paddle_y'], PADDLE_WIDTH, PADDLE_HEIGHT))
    pygame.draw.ellipse(fixed_surface, (255, 255, 255), (ball_x, state['ball_y'], BALL_SIZE, BALL_SIZE))
    pygame.draw.aaline(fixed_surface, (255, 255, 255), (FIXED_WIDTH // 2, 0), (FIXED_WIDTH // 2, FIXED_HEIGHT))

    # Draw score and player names
    font = pygame.font.Font(None, 36)
    score_text = font.render(f"{state['left_score']}   {state['right_score']}", True, (255, 255, 255))
    fixed_surface.blit(score_text, (FIXED_WIDTH // 2 - score_text.get_width() // 2, 10))
    
    # Add player names
    left_name_text = font.render(left_name, True, (255, 255, 255))
    right_name_text = font.render(right_name, True, (255, 255, 255))
    fixed_surface.blit(left_name_text, (50, 10))
    fixed_surface.blit(right_name_text, (FIXED_WIDTH - 50 - right_name_text.get_width(), 10))

    # Check for disconnection
    if state.get('disconnected', False):
        disconnect_font = pygame.font.Font(None, 48)
        disconnect_text = disconnect_font.render("Opponent disconnected!", True, (255, 0, 0))
        fixed_surface.blit(disconnect_text, (FIXED_WIDTH // 2 - disconnect_text.get_width() // 2, FIXED_HEIGHT // 2 - 24))
        
        instruction_text = font.render("Press ESC to exit", True, (255, 255, 255))
        fixed_surface.blit(instruction_text, (FIXED_WIDTH // 2 - instruction_text.get_width() // 2, FIXED_HEIGHT // 2 + 24))

    # Display controls
    controls_text = font.render("W/S - Move | P - Pause | ESC - Exit", True, (200, 200, 200))
    fixed_surface.blit(controls_text, (FIXED_WIDTH // 2 - controls_text.get_width() // 2, FIXED_HEIGHT - 30))

    scaled_surface = pygame.transform.scale(fixed_surface, current_resolution)
    screen.blit(scaled_surface, (0, 0))
    pygame.display.flip()


def main():
    sock, peer_addr, is_host, username, peer_username = setup_network()

    state = {
        'paddle_y': (FIXED_HEIGHT - PADDLE_HEIGHT) // 2,
        'opponent_paddle_y': (FIXED_HEIGHT - PADDLE_HEIGHT) // 2,
        'opponent_paddle_y_target': (FIXED_HEIGHT - PADDLE_HEIGHT) // 2,
        'opponent_paddle_y_previous': (FIXED_HEIGHT - PADDLE_HEIGHT) // 2,
        'opponent_paddle_y_velocity': 0,
        'ball_x': FIXED_WIDTH // 2,
        'ball_y': FIXED_HEIGHT // 2,
        'ball_speed_x': BALL_SPEED * (1 if is_host else -1),
        'ball_speed_y': BALL_SPEED,
        'left_score': 0,
        'right_score': 0,
        'last_packet_id': 0,
        'last_score_packet_id': 0,
        'score_changed': False,
        'disconnected': False
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
                if event.key == pygame.K_p:
                    paused = True
                    pause_font = pygame.font.Font(None, 48)
                    pause_text = pause_font.render("PAUSED", True, (255, 255, 255))
                    
                    while paused and running[0]:
                        for pause_event in pygame.event.get():
                            if pause_event.type == pygame.QUIT:
                                running[0] = False
                                paused = False
                            elif pause_event.type == pygame.KEYDOWN:
                                if pause_event.key == pygame.K_p:
                                    paused = False
                                elif pause_event.key == pygame.K_ESCAPE:
                                    running[0] = False
                                    paused = False
                        
                        # Draw pause message
                        scaled_surface = pygame.transform.scale(pygame.Surface((FIXED_WIDTH, FIXED_HEIGHT)), current_resolution)
                        scaled_surface.fill((0, 0, 0))
                        scaled_surface.blit(pause_text, (current_resolution[0]//2 - pause_text.get_width()//2, 
                                                      current_resolution[1]//2 - pause_text.get_height()//2))
                        screen.blit(scaled_surface, (0, 0))
                        pygame.display.flip()
                        pygame.time.wait(100)

        handle_input(state)
        score_changed = False
        
        if is_host:
            # Host controls ball physics and score
            score_changed = update_ball(state)
            if score_changed:
                state['score_changed'] = True
        elif frame_counter % 2 == 0:
            # Client-side prediction for smoother ball movement
            # Only apply client prediction if not receiving frequent updates
            if state.get('last_update_time', 0) + 0.1 < pygame.time.get_ticks() / 1000:
                state['ball_x'] += state['ball_speed_x']
                state['ball_y'] += state['ball_speed_y']
                
                if state['ball_y'] <= 0 or state['ball_y'] + BALL_SIZE >= FIXED_HEIGHT:
                    state['ball_speed_y'] *= -1

        # Send network updates
        if not state.get('disconnected', False):
            send_update = False
            if score_changed:
                send_update = True
            elif frame_counter % NETWORK_UPDATE_FREQUENCY == 0:
                send_update = True
                state['score_changed'] = False            
            if send_update:
                packet_id += 1
                try:
                    game_state = struct.pack('!iiiiiiiii',
                        packet_id,
                        state['paddle_y'], 
                        state['ball_x'], 
                        state['ball_y'],
                        state['ball_speed_x'], 
                        state['ball_speed_y'],
                        state['left_score'],
                        state['right_score'], 
                        1 if state['score_changed'] else 0  # Score changed flag
                    )
                    sock.sendto(game_state, peer_addr)
                except:
                    print("[ERROR] Failed to send game state")
            
        # More gradual interpolation for smoother movement
        state['opponent_paddle_y'] += (state['opponent_paddle_y_target'] - state['opponent_paddle_y']) * INTERPOLATION_FACTOR
        
        draw_game(state, is_host, username, peer_username)
        frame_counter += 1
        clock.tick(GAME_SPEED)

    end_game(state, sock, peer_addr)


def end_game(state=None, sock=None, peer_addr=None):
    print("Exiting game...")
    
    # Send disconnect message
    if sock and peer_addr and not state.get('disconnected', False):
        try:
            disconnect_msg = {
                'type': 'DISCONNECT',
                'reason': 'Player left the game'
            }
            sock.sendto(json.dumps(disconnect_msg).encode('utf-8'), peer_addr)
        except:
            pass
    
    try:
        if sock:
            sock.close()
    except:
        pass
        
    pygame.quit()
    exit()


def reset_ball(state):
    state['ball_x'], state['ball_y'] = FIXED_WIDTH // 2, FIXED_HEIGHT // 2
    state['ball_speed_x'] = BALL_SPEED * (1 if state['ball_speed_x'] > 0 else -1)  # Preserve direction
    state['ball_speed_y'] = BALL_SPEED * (1 if random.random() > 0.5 else -1)  # Random vertical direction


if __name__ == "__main__":
    main()
