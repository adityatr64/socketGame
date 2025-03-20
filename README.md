# P2P Pong Game

## Overview

P2P Pong is a networked version of the classic Pong game, developed as part of a Computer Networks project. It allows players to **host** or **join** game rooms using a **peer-to-peer (P2P) connection**, eliminating the need for a central server. The game uses **UDP broadcasting** for room discovery and **real-time data synchronization** to ensure smooth gameplay.

## Features

- **Peer-to-Peer Networking**: Direct communication between players without a central server.
- **Room Discovery**: Players can find and join available game rooms via UDP broadcasting.
- **Smooth Gameplay**: Real-time ball physics, paddle movement, and network interpolation for lag compensation.
- **Dynamic Resolution Scaling**: Game adapts to different screen sizes.

## Installation

### **Requirements**

- Python 3.x
- Pygame (`pip install pygame`)

### **Setup**

1. Clone the repository or download the `p2p.py` file:

   ```sh
   git clone https://github.com/adityatr64/socketGame
   # ;; or;;
   git clone https://github.com/aniruddhajoshi100/socketGame
   cd socketGame
   ```

2. Run the file
