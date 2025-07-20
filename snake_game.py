import pygame
import json
import math
import random
from enum import Enum

# Initialize Pygame
pygame.init()

# Constants
WINDOW_WIDTH = 1077
WINDOW_HEIGHT = 821
TILE_SIZE = 16
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)
LIGHT_GREEN = (144, 238, 144)
DARK_GREEN = (0, 128, 0)

class GameState(Enum):
    MENU = 1
    PLAYING = 2
    GAME_OVER = 3
    LEVEL_SELECT = 4
    VICTORY = 5

class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

class SnakeSegment:
    def __init__(self, x, y, segment_type="body"):
        self.x = x
        self.y = y
        self.segment_type = segment_type  # "head", "body", "tail"
        
    def get_rect(self):
        return pygame.Rect(self.x, self.y, TILE_SIZE, TILE_SIZE)

class Snake:
    def __init__(self, spawn_x, spawn_y):
        self.segments = [
            SnakeSegment(spawn_x, spawn_y, "head"),
            SnakeSegment(spawn_x - TILE_SIZE, spawn_y, "body"),
            SnakeSegment(spawn_x - TILE_SIZE * 2, spawn_y, "tail")
        ]
        self.direction = Direction.RIGHT
        self.speed = 2.0  # pixels per frame for continuous movement
        self.spawn_x = spawn_x
        self.spawn_y = spawn_y
        
    def update(self):
        # Move head based on direction
        head = self.segments[0]
        dx, dy = self.direction.value
        new_x = head.x + dx * self.speed
        new_y = head.y + dy * self.speed
        
        # Create new head position
        new_head = SnakeSegment(new_x, new_y, "head")
        
        # Move body segments to follow
        for i in range(len(self.segments) - 1, 0, -1):
            self.segments[i].x = self.segments[i-1].x
            self.segments[i].y = self.segments[i-1].y
            
        # Update head position
        self.segments[0] = new_head
        
        # Update segment types
        if len(self.segments) > 1:
            for i in range(1, len(self.segments) - 1):
                self.segments[i].segment_type = "body"
            self.segments[-1].segment_type = "tail"
    
    def change_direction(self, new_direction):
        # Prevent reverse direction
        current_dx, current_dy = self.direction.value
        new_dx, new_dy = new_direction.value
        if current_dx + new_dx != 0 or current_dy + new_dy != 0:
            self.direction = new_direction
    
    def grow(self):
        tail = self.segments[-1]
        new_segment = SnakeSegment(tail.x, tail.y, "body")
        self.segments.append(new_segment)
        # Update tail
        self.segments[-1].segment_type = "tail"
    
    def reset_to_spawn(self):
        self.segments = [
            SnakeSegment(self.spawn_x, self.spawn_y, "head"),
            SnakeSegment(self.spawn_x - TILE_SIZE, self.spawn_y, "body"),
            SnakeSegment(self.spawn_x - TILE_SIZE * 2, self.spawn_y, "tail")
        ]
        self.direction = Direction.RIGHT
    
    def check_self_collision(self):
        head_rect = self.segments[0].get_rect()
        for segment in self.segments[1:]:
            if head_rect.colliderect(segment.get_rect()):
                return True
        return False

class Level:
    def __init__(self, level_data):
        self.width = level_data["width"]
        self.height = level_data["height"]
        self.tile_width = level_data["tilewidth"]
        self.tile_height = level_data["tileheight"]
        
        # Parse layers
        self.floor_layer = None
        self.wall_layer = None
        self.fruit_layer = None
        self.gate_exit_layer = None
        self.snake_spawn = None
        
        for layer in level_data["layers"]:
            if layer["name"] == "floor":
                self.floor_layer = layer["data"]
            elif layer["name"] == "wall":
                self.wall_layer = layer["data"]
            elif layer["name"] == "fruit":
                self.fruit_layer = layer["data"][:]  # Copy to modify
            elif layer["name"] == "gate_exit":
                self.gate_exit_layer = layer["data"]
            elif layer["name"] == "snake_spawn" and layer["type"] == "objectgroup":
                if layer["objects"]:
                    obj = layer["objects"][0]
                    self.snake_spawn = (int(obj["x"]), int(obj["y"]))
        
        self.fruits_collected = 0
        self.total_fruits = sum(1 for tile in self.fruit_layer if tile == 5)
    
    def get_tile_at_position(self, x, y, layer):
        tile_x = int(x // self.tile_width)
        tile_y = int(y // self.tile_height)
        
        if 0 <= tile_x < self.width and 0 <= tile_y < self.height:
            index = tile_y * self.width + tile_x
            return layer[index] if index < len(layer) else 0
        return 0
    
    def is_wall(self, x, y):
        return self.get_tile_at_position(x, y, self.wall_layer) == 3
    
    def is_fruit(self, x, y):
        return self.get_tile_at_position(x, y, self.fruit_layer) == 5
    
    def is_exit(self, x, y):
        return self.get_tile_at_position(x, y, self.gate_exit_layer) == 6
    
    def collect_fruit(self, x, y):
        tile_x = int(x // self.tile_width)
        tile_y = int(y // self.tile_height)
        
        if 0 <= tile_x < self.width and 0 <= tile_y < self.height:
            index = tile_y * self.width + tile_x
            if index < len(self.fruit_layer) and self.fruit_layer[index] == 5:
                self.fruit_layer[index] = 0
                self.fruits_collected += 1
                return True
        return False

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Snake Game")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.large_font = pygame.font.Font(None, 72)
        
        # Game state
        self.state = GameState.MENU
        self.score = 0
        
        # Complete the gate_exit layer data
        complete_gate_exit_data = [0] * 570 + [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 6, 0, 0, 0, 0] + [0] * 0
        
        # Load level data
        self.level_data = {
            "compressionlevel": -1,
            "height": 20,
            "infinite": False,
            "tilewidth": 16,
            "tileheight": 16,
            "width": 30,
            "layers": [
                {
                    "data": [2] * 600,  # Floor layer - all tiles are floor
                    "height": 20,
                    "id": 2,
                    "name": "floor",
                    "opacity": 1,
                    "type": "tilelayer",
                    "visible": True,
                    "width": 30,
                    "x": 0,
                    "y": 0
                },
                {
                    "draworder": "topdown",
                    "id": 3,
                    "name": "snake_spawn",
                    "objects": [
                        {
                            "height": 16.0625,
                            "id": 3,
                            "name": "",
                            "rotation": 0,
                            "type": "",
                            "visible": True,
                            "width": 15.875,
                            "x": 16,
                            "y": 144
                        }
                    ],
                    "opacity": 1,
                    "type": "objectgroup",
                    "visible": True,
                    "x": 0,
                    "y": 0
                },
                {
                    "data": [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                            3, 0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                            3, 0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                            3, 0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                            3, 0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                            3, 0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                            3, 0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                            3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3,
                            3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3,
                            3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0, 0, 0, 3,
                            3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0, 0, 0, 3,
                            3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 3, 3, 3, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 3,
                            3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 3, 3, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3,
                            3, 0, 0, 0, 0, 3, 3, 0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 0, 3, 0, 0, 3,
                            3, 0, 0, 0, 0, 3, 3, 0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0, 0, 0, 3,
                            3, 0, 0, 0, 0, 3, 3, 0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 0, 3, 3, 3,
                            3, 0, 0, 0, 0, 3, 3, 0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0, 0, 3,
                            3, 0, 0, 0, 0, 3, 3, 0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 0, 3,
                            3, 0, 0, 0, 0, 3, 3, 0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 0, 0, 0, 0, 3,
                            3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
                    "height": 20,
                    "id": 1,
                    "name": "wall",
                    "opacity": 1,
                    "type": "tilelayer",
                    "visible": True,
                    "width": 30,
                    "x": 0,
                    "y": 0
                },
                {
                    "data": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                    "height": 20,
                    "id": 5,
                    "name": "fruit",
                    "opacity": 1,
                    "type": "tilelayer",
                    "visible": True,
                    "width": 30,
                    "x": 0,
                    "y": 0
                },
                {
                    "data": complete_gate_exit_data,
                    "height": 20,
                    "id": 6,
                    "name": "gate_exit",
                    "opacity": 1,
                    "type": "tilelayer",
                    "visible": True,
                    "width": 30,
                    "x": 0,
                    "y": 0
                }
            ]
        }
        
        # Initialize level and snake
        self.level = Level(self.level_data)
        spawn_x, spawn_y = self.level.snake_spawn if self.level.snake_spawn else (48, 144)
        self.snake = Snake(spawn_x, spawn_y)
        self.running = True
        
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if self.state == GameState.MENU:
                    if event.key == pygame.K_SPACE:
                        self.start_game()
                elif self.state == GameState.PLAYING:
                    if event.key == pygame.K_UP:
                        self.snake.change_direction(Direction.UP)
                    elif event.key == pygame.K_DOWN:
                        self.snake.change_direction(Direction.DOWN)
                    elif event.key == pygame.K_LEFT:
                        self.snake.change_direction(Direction.LEFT)
                    elif event.key == pygame.K_RIGHT:
                        self.snake.change_direction(Direction.RIGHT)
                elif self.state == GameState.GAME_OVER:
                    if event.key == pygame.K_r:
                        self.restart_game()
                    elif event.key == pygame.K_m:
                        self.state = GameState.MENU
                elif self.state == GameState.VICTORY:
                    if event.key == pygame.K_r:
                        self.restart_game()
                    elif event.key == pygame.K_m:
                        self.state = GameState.MENU
    
    def start_game(self):
        self.state = GameState.PLAYING
        self.score = 0
        self.level = Level(self.level_data)  # Reset level
        spawn_x, spawn_y = self.level.snake_spawn if self.level.snake_spawn else (48, 144)
        self.snake = Snake(spawn_x, spawn_y)
    
    def restart_game(self):
        self.start_game()
    
    def update_game(self):
        if self.state == GameState.PLAYING:
            self.snake.update()
            
            # Check wall collisions
            head = self.snake.segments[0]
            if self.level.is_wall(head.x, head.y):
                self.state = GameState.GAME_OVER
                return
            
            # Check self collision
            if self.snake.check_self_collision():
                self.state = GameState.GAME_OVER
                return
            
            # Check fruit collection
            if self.level.is_fruit(head.x, head.y):
                if self.level.collect_fruit(head.x, head.y):
                    self.snake.grow()
                    self.score += 10
            
            # Check exit condition
            if self.level.is_exit(head.x, head.y) and self.level.fruits_collected >= self.level.total_fruits:
                self.state = GameState.VICTORY
    
    def draw_level(self):
        # Draw floor
        for y in range(self.level.height):
            for x in range(self.level.width):
                rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(self.screen, LIGHT_GREEN, rect)
        
        # Draw walls
        for y in range(self.level.height):
            for x in range(self.level.width):
                if self.level.wall_layer[y * self.level.width + x] == 3:
                    rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    pygame.draw.rect(self.screen, GRAY, rect)
        
        # Draw fruits
        for y in range(self.level.height):
            for x in range(self.level.width):
                if self.level.fruit_layer[y * self.level.width + x] == 5:
                    rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    pygame.draw.rect(self.screen, RED, rect)
        
        # Draw exit
        for y in range(self.level.height):
            for x in range(self.level.width):
                if self.level.gate_exit_layer[y * self.level.width + x] == 6:
                    rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    color = YELLOW if self.level.fruits_collected >= self.level.total_fruits else DARK_GRAY
                    pygame.draw.rect(self.screen, color, rect)
    
    def draw_snake(self):
        for i, segment in enumerate(self.snake.segments):
            rect = segment.get_rect()
            if segment.segment_type == "head":
                pygame.draw.rect(self.screen, DARK_GREEN, rect)
                # Draw eyes
                eye_size = 3
                pygame.draw.circle(self.screen, BLACK, 
                                 (int(rect.centerx - 4), int(rect.centery - 3)), eye_size)
                pygame.draw.circle(self.screen, BLACK, 
                                 (int(rect.centerx + 4), int(rect.centery - 3)), eye_size)
            else:
                pygame.draw.rect(self.screen, GREEN, rect)
    
    def draw_ui(self):
        # Score
        score_text = self.font.render(f"Score: {self.score}", True, BLACK)
        self.screen.blit(score_text, (10, 10))
        
        # Fruits collected
        fruits_text = self.font.render(f"Fruits: {self.level.fruits_collected}/{self.level.total_fruits}",