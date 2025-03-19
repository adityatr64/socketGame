import pygame
import socket
import threading
import struct
import time
import json
import random
import string

PORT = 42069
DISCOVERY_PORT = 42070
BUFFER_SIZE = 1024
SOCKET_BUFFER_SIZE = 65536
FIXED_WIDTH, FIXED_HEIGHT = 960, 540
PADDLE_WIDTH, PADDLE_HEIGHT = 10, 100
BALL_SIZE = 20
BALL_SPEED = 3
PADDLE_SPEED = 5
GAME_SPEED = 60
NETWORK_UPDATE_FREQUENCY = 2
INTERPOLATION_FACTOR = 0.5  # Faster opponent paddle smoothing
ROOM_BROADCAST_INTERVAL = 3  # Seconds between room broadcasts
ROOM_TIMEOUT = 15  # Seconds before a room is considered inactive

pygame.init()
screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
pygame.display.set_caption("P2P Pong")
clock = pygame.time.Clock()

# Track current window size
current_resolution = (FIXED_WIDTH, FIXED_HEIGHT)

class Room:
    def __init__(self, name, host_ip, room_id=None):
        self.name = name
        self.host_ip = host_ip
        self.room_id = room_id or self._generate_id()
        self.last_update = time.time()
        self.player_count = 1
        
    def _generate_id(self):
        """Generate a unique room ID"""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
    def to_json(self):
        return json.dumps({
            "name": self.name,
            "host_ip": self.host_ip,
            "room_id": self.room_id,
            "player_count": self.player_count
        })
        
    @classmethod
    def from_json(cls, json_str):
        try:
            data = json.loads(json_str)
            room = cls(data["name"], data["host_ip"], data["room_id"])
            room.player_count = data["player_count"]
            return room
        except:
            return None

# Room discovery and broadcasting
class RoomManager:
    def __init__(self):
        self.rooms = {}  # room_id -> Room
        self.discovery_socket = None
        self.running = False
        self.is_host = False
        self.my_room = None
        
    def start(self, is_host=False):
        self.is_host = is_host
        self.running = True
        self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        if not is_host:
            try:
                self.discovery_socket.bind(("", DISCOVERY_PORT))
            except:
                print("[ERROR] Could not bind to discovery port")
        
        # Start threads for discovery and broadcasting
        if is_host:
            threading.Thread(target=self._broadcast_room, daemon=True).start()
        else:
            threading.Thread(target=self._discover_rooms, daemon=True).start()
    
    def create_room(self, name):
        """Create a new room as host"""
        # Get local IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Doesn't need to be reachable
            s.connect(('10.255.255.255', 1))
            host_ip = s.getsockname()[0]
        except:
            host_ip = '127.0.0.1'
        finally:
            s.close()
            
        self.my_room = Room(name, host_ip)
        return self.my_room
    
    def get_rooms(self):
        """Get all active rooms"""
        # Clean up expired rooms
        current_time = time.time()
        expired_rooms = [room_id for room_id, room in self.rooms.items() 
                         if current_time - room.last_update > ROOM_TIMEOUT]
        for room_id in expired_rooms:
            del self.rooms[room_id]
            
        return list(self.rooms.values())
    
    def _broadcast_room(self):
        """Broadcast room info on the network"""
        if not self.my_room:
            return
            
        while self.running and self.is_host:
            try:
                room_data = self.my_room.to_json()
                self.discovery_socket.sendto(room_data.encode(), ('<broadcast>', DISCOVERY_PORT))
            except:
                pass
            time.sleep(ROOM_BROADCAST_INTERVAL)
    
    def _discover_rooms(self):
        """Listen for room broadcasts"""
        self.discovery_socket.settimeout(1)
        
        while self.running and not self.is_host:
            try:
                data, addr = self.discovery_socket.recvfrom(BUFFER_SIZE)
                room = Room.from_json(data.decode())
                if room:
                    room.last_update = time.time()
                    self.rooms[room.room_id] = room
            except socket.timeout:
                continue
            except:
                pass
    
    def stop(self):
        """Stop all networking"""
        self.running = False
        if self.discovery_socket:
            self.discovery_socket.close()

def room_selection_screen():
    """Improved UI for selecting or creating a room"""
    font = pygame.font.Font(None, 36)
    small_font = pygame.font.Font(None, 24)

    create_room_button = pygame.Rect(200, 100, 400, 50)
    refresh_button = pygame.Rect(650, 150, 100, 30)
    room_name_input = pygame.Rect(200, 200, 400, 50)

    color_inactive = pygame.Color('darkorange')
    color_active = pygame.Color('gold')
    color_hover = pygame.Color('yellow')
    button_color = color_inactive
    input_color = color_inactive

    active_box = None
    room_name = "My Game Room"
    selected_resolution = "960x540"
    scroll_offset = 0
    max_visible_rooms = 5

    room_manager = RoomManager()
    room_manager.start(False)  # Start in client mode initially
    last_refresh = time.time()

    while True:
        screen.fill((30, 30, 30))  # Dark background
        mouse_pos = pygame.mouse.get_pos()
        current_time = time.time()

        # Auto-refresh room list every 3 seconds
        if current_time - last_refresh > 3:
            last_refresh = current_time

        rooms = room_manager.get_rooms()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                room_manager.stop()
                pygame.quit()
                exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if create_room_button.collidepoint(event.pos):
                    room_manager.stop()
                    return {"role": "host", "room_name": room_name, "resolution": selected_resolution}
                elif refresh_button.collidepoint(event.pos):
                    last_refresh = current_time
                elif room_name_input.collidepoint(event.pos):
                    active_box = 'room_name'
                else:
                    active_box = None

                # Check if clicked on a room in the list
                for i, room in enumerate(rooms[scroll_offset:scroll_offset + max_visible_rooms]):
                    room_rect = pygame.Rect(200, 250 + i * 60, 400, 50)
                    if room_rect.collidepoint(event.pos):
                        room_manager.stop()
                        return {"role": "client", "peer_ip": room.host_ip, "resolution": selected_resolution, "room_name": room.name}

            if event.type == pygame.KEYDOWN and active_box == 'room_name':
                if event.key == pygame.K_RETURN:
                    active_box = None
                elif event.key == pygame.K_BACKSPACE:
                    room_name = room_name[:-1]
                else:
                    room_name += event.unicode

        # Change button color on hover
        button_color = color_hover if create_room_button.collidepoint(mouse_pos) else color_inactive
        input_color = color_active if active_box == 'room_name' else color_inactive

        # Draw UI elements
        pygame.draw.rect(screen, button_color, create_room_button, border_radius=10)
        pygame.draw.rect(screen, color_inactive, refresh_button, border_radius=5)
        pygame.draw.rect(screen, input_color, room_name_input, 2, border_radius=5)

        # Draw text
        screen.blit(font.render("Create Room", True, (0, 0, 0)), (create_room_button.x + 120, create_room_button.y + 10))
        screen.blit(small_font.render("Refresh", True, (0, 0, 0)), (refresh_button.x + 20, refresh_button.y + 8))
        screen.blit(font.render("Room Name:", True, (255, 255, 255)), (200, 165))
        screen.blit(font.render(room_name, True, input_color), (room_name_input.x + 10, room_name_input.y + 10))
        screen.blit(font.render("Available Rooms:", True, (255, 255, 255)), (200, 260))

        # Draw room list
        if not rooms:
            msg = "No rooms found. Create one or wait for broadcasts."
            screen.blit(small_font.render(msg, True, (200, 200, 200)), (250, 310))
        else:
            for i, room in enumerate(rooms[scroll_offset:scroll_offset + max_visible_rooms]):
                room_rect = pygame.Rect(200, 250 + i * 60, 400, 50)
                pygame.draw.rect(screen, (100, 100, 100, 180), room_rect, border_radius=5)
                
                # Room info display
                screen.blit(font.render(room.name, True, (255, 255, 255)), (room_rect.x + 10, room_rect.y + 10))
                player_text = f"Players: {room.player_count}/2"
                screen.blit(small_font.render(player_text, True, (200, 200, 200)), (room_rect.x + 300, room_rect.y + 18))

        pygame.display.flip()
        clock.tick(GAME_SPEED)


def setup_network(room_data):
    role = room_data["role"]
    is_host = role == "host"
    res_text = room_data["resolution"]
    room_name = room_data.get("room_name", "Game Room")
    
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

    if is_host:
        # Start broadcasting room
        room_manager = RoomManager()
        room = room_manager.create_room(room_name)
        room_manager.start(True)
        
        sock.bind(("0.0.0.0", PORT))
        print(f"[HOST] Created room: {room_name}")
        print(f"[HOST] Waiting for client on {PORT}...")
        
        try:
            msg, peer_addr = sock.recvfrom(BUFFER_SIZE)
            if msg == b"HELLO":
                print(f"[HOST] Client connected from {peer_addr}")
                sock.sendto(b"HELLO_ACK", peer_addr)
                room.player_count = 2  # Update player count
            else:
                print("[HOST] Unexpected message. Connection failed.")
                room_manager.stop()
                exit()
        except socket.timeout:
            print("[HOST] No client connected. Timeout.")
            room_manager.stop()
            exit()
    
    else:
        # Join an existing room
        peer_ip = room_data["peer_ip"]
        sock.bind(("0.0.0.0", 0))
        print(f"[CLIENT] Bound to {sock.getsockname()[1]}")
        print(f"[CLIENT] Connecting to host {peer_ip}:{PORT}...")

        for _ in range(5):
            sock.sendto(b"HELLO", (peer_ip, PORT))
            try:
                msg, host_addr = sock.recvfrom(BUFFER_SIZE)
                if msg == b"HELLO_ACK":
                    print(f"[CLIENT] Connected to room: {room_name}")
                    peer_addr = host_addr
                    break
                else:
                    print("[CLIENT] Unexpected response from host.")
                    exit()
            except socket.timeout:
                print("[CLIENT] Retrying connection...")
                continue
        else:
            print("[CLIENT] No response from host after multiple attempts. Timeout.")
            exit()

    return sock, peer_addr, is_host

def receive_data(sock, is_host, state, running):
    last_received_time = time.time()

    while running[0]:
        try:
            data, _ = sock.recvfrom(BUFFER_SIZE)
            packet_id, paddle_y, ball_x, ball_y, ball_speed_x, ball_speed_y, left_score, right_score, score_changed = struct.unpack('!iiiiiiiii', data)
            
            last_packet_id = state.get('last_packet_id', 0)
            if packet_id > last_packet_id:
                state['last_packet_id'] = packet_id
                state['opponent_paddle_y_target'] = paddle_y
                state['opponent_paddle_y_previous'] = paddle_y

                # Only update ball position if host sent new data
                if not is_host:
                    state['ball_x'] = ball_x
                    state['ball_y'] = ball_y
                    state['ball_speed_x'] = ball_speed_x
                    state['ball_speed_y'] = ball_speed_y

                last_received_time = time.time()
                
                if score_changed:
                    state['left_score'] = left_score
                    state['right_score'] = right_score

        except socket.timeout:
            # If timeout, predict ball movement instead of freezing
            if not is_host and time.time() - last_received_time > 0.1:
                state['ball_x'] += state['ball_speed_x']
                state['ball_y'] += state['ball_speed_y']
                
                if state['ball_y'] <= 0 or state['ball_y'] + BALL_SIZE >= FIXED_HEIGHT:
                    state['ball_speed_y'] *= -1  # Bounce on walls
                
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

    pygame.draw.rect(fixed_surface, (255, 255, 255), (paddle_x, state['paddle_y'], PADDLE_WIDTH, PADDLE_HEIGHT))
    pygame.draw.rect(fixed_surface, (255, 255, 255), (opponent_x, state['opponent_paddle_y'], PADDLE_WIDTH, PADDLE_HEIGHT))
    pygame.draw.ellipse(fixed_surface, (255, 255, 255), (ball_x, state['ball_y'], BALL_SIZE, BALL_SIZE))
    pygame.draw.aaline(fixed_surface, (255, 255, 255), (FIXED_WIDTH // 2, 0), (FIXED_WIDTH // 2, FIXED_HEIGHT))

    font = pygame.font.Font(None, 36)
    score_text = font.render(f"{state['left_score']}   {state['right_score']}", True, (255, 255, 255))
    fixed_surface.blit(score_text, (FIXED_WIDTH // 2 - score_text.get_width() // 2, 10))

    scaled_surface = pygame.transform.scale(fixed_surface, current_resolution)
    screen.blit(scaled_surface, (0, 0))
    pygame.display.flip()

def main():
    # Show room selection instead of loading screen
    room_data = room_selection_screen()
    
    # After selecting a room, set up the network connection
    sock, peer_addr, is_host = setup_network(room_data)

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
        'score_changed': False
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
                    while paused:
                        for pause_event in pygame.event.get():
                            if pause_event.type == pygame.QUIT:
                                running[0] = False
                                paused = False
                            elif pause_event.type == pygame.KEYDOWN and pause_event.key == pygame.K_p:
                                paused = False
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
        send_update = False
        if score_changed:
            send_update = True
        elif frame_counter % NETWORK_UPDATE_FREQUENCY == 0:
            send_update = True
            state['score_changed'] = False            
        if send_update:
            packet_id += 1
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