import os
import random
import math
import pygame
from os import listdir
from os.path import isfile, join

# Initialize pygame and the sound mixer for music/sfx
pygame.init()
pygame.mixer.init()

pygame.display.set_caption("Platformer")

# Global constants for screen size and frame rate
WIDTH, HEIGHT = 1000, 800
FPS = 60
PLAYER_VEL = 5

window = pygame.display.set_mode((WIDTH, HEIGHT))


# Helper function to flip images horizontally
# We use this so we don't need separate image files for left vs right facing characters
def flip(sprites):
    return [pygame.transform.flip(sprite, True, False) for sprite in sprites]


# This function loads sprite sheets from the assets folder
# It splits a big image sheet into individual animation frames based on width/height
def load_sprite_sheets(dir1, dir2, width, height, direction=False):
    path = join("assets", dir1, dir2)
    # Safety check: make sure the folder actually exists so the game doesn't crash
    if not os.path.exists(path):
        print(f"Error: Directory not found: {path}")
        return {}
        
    images = [f for f in listdir(path) if isfile(join(path, f))]

    all_sprites = {}

    # Loop through every image file in the directory
    for image in images:
        sprite_sheet = pygame.image.load(join(path, image)).convert_alpha()

        sprites = []
        # Cut the sheet into individual frames
        for i in range(sprite_sheet.get_width() // width):
            surface = pygame.Surface((width, height), pygame.SRCALPHA, 32)
            rect = pygame.Rect(i * width, 0, width, height)
            surface.blit(sprite_sheet, (0, 0), rect)
            sprites.append(pygame.transform.scale2x(surface))

        # If direction is needed, we save both right (normal) and left (flipped) versions
        if direction:
            all_sprites[image.replace(".png", "") + "_right"] = sprites
            all_sprites[image.replace(".png", "") + "_left"] = flip(sprites)
        else:
            all_sprites[image.replace(".png", "")] = sprites

    return all_sprites


# Loads the terrain block image
def get_block(size):
    path = join("assets", "Terrain.png")
    image = pygame.image.load(path).convert_alpha()
    surface = pygame.Surface((size, size), pygame.SRCALPHA, 32)
    rect = pygame.Rect(0, 0, size, size)
    surface.blit(image, (0, 0), rect)
    return pygame.transform.scale2x(surface)


# The main Player class containing movement, physics, and animation logic
class Player(pygame.sprite.Sprite):
    COLOR = (255, 0, 0)
    GRAVITY = 1
    # Load the sprites for the player specifically
    SPRITES = load_sprite_sheets("MainCharacters", "Man", 32, 32, True)
    ANIMATION_DELAY = 3

    def __init__(self, x, y, width, height):
        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)
        self.x_vel = 0
        self.y_vel = 0
        self.mask = None
        self.direction = "left"
        self.animation_count = 0
        self.fall_count = 0
        self.jump_count = 0
        self.hit = False
        self.hit_count = 0
        self.lives = 5 # Player health
 
    # Handles jumping physics
    def jump(self):
        self.y_vel = -self.GRAVITY * 13 # Negative velocity moves player UP
        self.animation_count = 0
        self.jump_count += 1
        if self.jump_count == 1:
            self.fall_count = 0

    # Updates the X and Y coordinates of the player
    def move(self, dx, dy):
        self.rect.x += dx
        self.rect.y += dy

    # Logic for when the player gets damaged
    def make_hit(self):
        if not self.hit:
            self.lives -= 1
            self.hit = True
            # Bounce player back slightly on hit
            self.y_vel = -5 
            # Play damage sound if it exists
            if (self, "damage_sound"):
                self.damage_sound.play()

    # Helpers to set velocity and direction
    def move_left(self, vel):
        self.x_vel = -vel
        if self.direction != "left":
            self.direction = "left"
            self.animation_count = 0

    def move_right(self, vel):
        self.x_vel = vel
        if self.direction != "right":
            self.direction = "right"
            self.animation_count = 0

    # The main update loop for the player (called every frame)
    def loop(self, fps):
        # Apply gravity (increases falling speed over time)
        self.y_vel += min(1, (self.fall_count / fps) * self.GRAVITY)
        self.move(self.x_vel, self.y_vel)

        # Handle invulnerability frames after getting hit
        if self.hit:
            self.hit_count += 1
        if self.hit_count > fps * 2:
            self.hit = False
            self.hit_count = 0

        self.fall_count += 1
        self.update_sprite()

    # Reset physics when hitting the ground
    def landed(self):
        self.fall_count = 0
        self.y_vel = 0
        self.jump_count = 0

    # Reset physics when hitting a ceiling
    def hit_head(self):
        self.count = 0
        self.y_vel *= -1

    # Updates the current sprite image based on state (jumping, running, idle)
    def update_sprite(self):
        sprite_sheet = "idle"
        if self.hit:
            sprite_sheet = "hit"
        elif self.y_vel < 0:
            if self.jump_count == 1:
                sprite_sheet = "jump"
            elif self.jump_count == 2:
                sprite_sheet = "double_jump"
        elif self.y_vel > self.GRAVITY * 5:
            sprite_sheet = "fall"
        elif self.x_vel != 0:
            sprite_sheet = "run"

        sprite_sheet_name = sprite_sheet + "_" + self.direction
        sprites = self.SPRITES[sprite_sheet_name]
        
        # Calculate which frame to show for animation
        sprite_index = (self.animation_count //
                        self.ANIMATION_DELAY) % len(sprites)
        self.sprite = sprites[sprite_index]
        self.animation_count += 1
        self.update()

    # Updates the rectangle and collision mask
    def update(self):
        self.rect = self.sprite.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.sprite)

    def draw(self, win, offset_x):
        win.blit(self.sprite, (self.rect.x - offset_x, self.rect.y))

# Simple class for the bullets the enemies shoot
class Projectile(pygame.sprite.Sprite):
    def __init__(self, x, y, direction):
        super().__init__()
        self.rect = pygame.Rect(x, y, 10, 10) # 10x10 pixel dot
        self.direction = direction
        self.vel = 7 * direction # Speed of shot
        self.color = (0, 0, 0) # Black dot

    def loop(self):
        self.rect.x += self.vel

    def draw(self, win, offset_x):
        pygame.draw.circle(win, self.color, (self.rect.x - offset_x + 5, self.rect.y + 5), 5)


# Enemy class with simple AI (patrol and shoot)
class Enemy(pygame.sprite.Sprite):
    SPRITES = load_sprite_sheets("MainCharacters", "bad_guy", 32, 32, True)
    GRAVITY = 1
    ANIMATION_DELAY = 4

    def __init__(self, x, y, width, height, patrol_distance):
        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)
        self.start_x = x
        self.patrol_distance = patrol_distance
        self.direction = "right"
        self.x_vel = 2
        self.y_vel = 0
        self.animation_count = 0
        self.mask = None
        self.lives = 3 
        self.shoot_cooldown = 0
        self.hit = False
        self.hit_timer = 0
        
        # Default sprite just in case assets are missing
        self.sprite = self.SPRITES.get("run_right", [pygame.Surface((width, height))])[0]

    # AI Logic: Walk back and forth within patrol distance
    def move(self):
        if self.direction == "right":
            self.x_vel = 2
            if self.rect.x > self.start_x + self.patrol_distance:
                self.direction = "left"
        else:
            self.x_vel = -2
            if self.rect.x < self.start_x:
                self.direction = "right"
        
        self.rect.x += self.x_vel

    def loop(self, fps):
        self.move()
        self.update_sprite()
        
        # Decrease cooldown timer for shooting
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        
        # Flash animation if hit
        if self.hit:
            self.hit_timer += 1
            if self.hit_timer > 20:
                self.hit = False
                self.hit_timer = 0

    # Handles shooting logic with a cooldown
    def shoot(self):
        # Shoot every 2 seconds (60fps * 2)
        if self.shoot_cooldown == 0:
            self.shoot_cooldown = 120 
            direction = 1 if self.direction == "right" else -1
            return Projectile(self.rect.x, self.rect.y + 20, direction)
        return None

    def update_sprite(self):
        # We only have "run", so we use run for everything
        sprite_name = "run_" + self.direction
        sprites = self.SPRITES.get(sprite_name)
        
        if not sprites:
            sprites = list(self.SPRITES.values())[0]

        sprite_index = (self.animation_count // self.ANIMATION_DELAY) % len(sprites)
        self.sprite = sprites[sprite_index]
        self.animation_count += 1
        
        self.rect = self.sprite.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.sprite)

    def draw(self, win, offset_x):
        if self.lives > 0:
            win.blit(self.sprite, (self.rect.x - offset_x, self.rect.y))
            # Draw health bars above enemy head
            pygame.draw.rect(win, (255, 0, 0), (self.rect.x - offset_x, self.rect.y - 10, 50, 5))
            pygame.draw.rect(win, (0, 255, 0), (self.rect.x - offset_x, self.rect.y - 10, 50 * (self.lives/3), 5))


# Base class for generic objects in the world
class Object(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, name=None):
        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self.width = width
        self.height = height
        self.name = name

    def draw(self, win, offset_x):
        win.blit(self.image, (self.rect.x - offset_x, self.rect.y))


# Class for Terrain blocks
class Block(Object):
    def __init__(self, x, y, size):
        super().__init__(x, y, size, size)
        block = get_block(size)
        self.image.blit(block, (0, 0))
        self.mask = pygame.mask.from_surface(self.image)


# Class for Fire Traps (includes animation)
class Fire(Object):
    ANIMATION_DELAY = 3

    def __init__(self, x, y, width, height):
        super().__init__(x, y, width, height, "fire")
        self.fire = load_sprite_sheets("Traps", "Fire", width, height)
        self.image = self.fire["off"][0]
        self.mask = pygame.mask.from_surface(self.image)
        self.animation_count = 0
        self.animation_name = "off"

    def on(self):
        self.animation_name = "on"

    def off(self):
        self.animation_name = "off"

    def loop(self):
        sprites = self.fire[self.animation_name]
        sprite_index = (self.animation_count //
                        self.ANIMATION_DELAY) % len(sprites)
        self.image = sprites[sprite_index]
        self.animation_count += 1

        self.rect = self.image.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.image)

        if self.animation_count // self.ANIMATION_DELAY > len(sprites):
            self.animation_count = 0

# Class for the winning objective (Treasure)
class Treasure(Object):
    def __init__(self, x, y, size):
        super().__init__(x, y, size, size, "treasure")
        path = join("assets", "trophy.png")
        if os.path.exists(path):
            img = pygame.image.load(path).convert_alpha()
            # Scale image to fit the block size
            self.image.blit(pygame.transform.scale(img, (size, size)), (0, 0))
        else:
            # Fallback: Gold square if no image found
            self.image.fill((255, 215, 0)) 
        self.mask = pygame.mask.from_surface(self.image)


# Creates a tiled background so the image doesn't look stretched
def get_background(name):
    image = pygame.image.load(join("assets", "Background", name))
    _, _, width, height = image.get_rect()
    tiles = []

    for i in range(WIDTH // width + 1):
        for j in range(HEIGHT // height + 1):
            pos = (i * width, j * height)
            tiles.append(pos)

    return tiles, image


# The main draw loop - renders background, objects, and player
def draw(window, background, bg_image, player, objects, offset_x):
    for tile in background:
        window.blit(bg_image, tile)

    for obj in objects:
        obj.draw(window, offset_x)

    player.draw(window, offset_x)

    pygame.display.update()


# Checks for collisions above or below the player (floor/ceiling)
def handle_vertical_collision(player, objects, dy):
    collided_objects = []
    for obj in objects:
        if pygame.sprite.collide_mask(player, obj):
            if dy > 0:
                # Landed on top of object
                player.rect.bottom = obj.rect.top
                player.landed()
            elif dy < 0:
                # Hit head on bottom of object
                player.rect.top = obj.rect.bottom
                player.hit_head()

            collided_objects.append(obj)

    return collided_objects


# Checks for horizontal collisions so we don't walk through walls
def collide(player, objects, dx):
    player.move(dx, 0)
    player.update()
    collided_object = None
    for obj in objects:
        if pygame.sprite.collide_mask(player, obj):
            collided_object = obj
            break

    player.move(-dx, 0)
    player.update()
    return collided_object


# Processes keyboard input for movement
def handle_move(player, objects):
    keys = pygame.key.get_pressed()

    player.x_vel = 0
    collide_left = collide(player, objects, -PLAYER_VEL * 2)
    collide_right = collide(player, objects, PLAYER_VEL * 2)

    if keys[pygame.K_LEFT] and not collide_left:
        player.move_left(PLAYER_VEL)
    if keys[pygame.K_RIGHT] and not collide_right:
        player.move_right(PLAYER_VEL)

    vertical_collide = handle_vertical_collision(player, objects, player.y_vel)
    to_check = [collide_left, collide_right, *vertical_collide]

    for obj in to_check:
        if obj and obj.name == "fire":
            player.make_hit()

# UI helper to draw interactive buttons
def button(win, text, x, y ,w ,h):
    mouse = pygame.mouse.get_pos()
    click = pygame.mouse.get_pressed()

    pygame.draw.rect(win,(200,100,150), (x, y ,w ,h))

    font = pygame.font.SysFont("arial", 35)
    text_surf = font.render(text,True, (255,255,255))
    win.blit(
        text_surf,
        (x + (w - text_surf.get_width()) // 2,
         y + (h - text_surf.get_height()) // 2)
    )
    # Check if mouse is hovering over button and clicked
    if x < mouse[0] < x + w and y < mouse[1] < y + h:
        if click[0] == 1:
            return True
    return False

# Draws the Heads-Up Display (Lives, Score, Time)
def draw_hud(win, player, score, start_ticks):
    font = pygame.font.SysFont("arial", 30)
    
    # Check if heart image exists, otherwise draw text
    if isfile("assets/heart.png"):
        heart_img = pygame.image.load("assets/heart.png").convert_alpha()
        for i in range(player.lives):
            win.blit(heart_img,(20 +i * 40, 20))
    else:
        text_lives = font.render(f"Lives: {player.lives}", True, (255,0,0))
        win.blit(text_lives, (20, 20))

    score_text = font.render(f"Score: {score}", True, (102,0,51))
    win.blit(score_text, (20, 60))

    # Calculate time played
    seconds = (pygame.time.get_ticks() - start_ticks) // 1000
    timer_text = font.render(f"Time: {seconds}", True, (0,0,0))
    win.blit(timer_text, (20, 100))

# --- MAIN GAME FUNCTION ---

# Sets up the level, loop, and game state
def main(window):
    clock = pygame.time.Clock()
    background, bg_image = get_background("pink.png")

    block_size = 96

    player = Player(100, 100, 50, 50)

    # --- LEVEL GENERATION START ---
    floor = []
    # Ground ranges: tuples of (start, end) blocks
    ground_ranges = [(-2, 6), (9, 14), (17, 22), (26, 30), (34, 38), (42, 60)]

    for start, end in ground_ranges:
        for i in range(start, end):
            floor.append(Block(i * block_size, HEIGHT - block_size, block_size))

    # Create Floating Blocks for platforming
    blocks = []
    floating_blocks_coords = [
        (7, 4), (8, 4), (15, 3), (23, 3), (24, 4), (31, 2), (32, 2), (39, 4), (40, 4)
    ]
    for x, height in floating_blocks_coords:
        blocks.append(Block(x * block_size, HEIGHT - (block_size * height), block_size))

    # Create Fire traps
    fires = [
        Fire(block_size * 3, HEIGHT - block_size - 64, 16, 32),
        Fire(block_size * 12, HEIGHT - block_size - 64, 16, 32),
        Fire(block_size * 20, HEIGHT - block_size - 64, 16, 32),
        Fire(block_size * 45, HEIGHT - block_size - 64, 16, 32)
    ]
    for f in fires:
        f.on()

    # Create Enemies
    enemies = [
        Enemy(block_size * 44, HEIGHT - block_size - 64, 50, 50, block_size * 4),
        Enemy(block_size * 18, HEIGHT - block_size - 64, 50, 50, block_size * 2)
    ]
    
    projectiles = []

    # Add everything to one list for drawing
    objects = [*floor, *blocks, *fires]

    treasure = None # Will be created when enemies are dead

    offset_x = 0
    scroll_area_width = 200
    game_over = False
    game_won = False 
    score = 0 
    start_ticks = pygame.time.get_ticks()

    # Load and play background music
    pygame.mixer.music.load("assets/sounds/background-music.mp3")
    pygame.mixer.music.set_volume(0.3)
    pygame.mixer.music.play(-1) # -1 means loop forever

    # Load sound effects
    lose_sound = pygame.mixer.Sound("assets/sounds/lose.mp3")
    lose_sound.set_volume(0.7)
    lose_played = False

    jump_sound = pygame.mixer.Sound("assets/sounds/jump.mp3")
    jump_sound.set_volume(0.6)

    win_sound = pygame.mixer.Sound("assets/sounds/win.mp3")
    win_sound.set_volume(0.7)
    win_played = False
    
    damage_sound = pygame.mixer.Sound("assets/sounds/damage.mp3")
    damage_sound.set_volume(0.6)  
    player.damage_sound = damage_sound
   
    run = True
    # --- MAIN LOOP ---
    while run:
        clock.tick(FPS) # Maintain 60 FPS

        # Event Loop (Check for closing window or keys)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                break

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and player.jump_count < 2:
                    player.jump()
                    jump_sound.play()

        player.loop(FPS)
        
        for f in fires:
            f.loop()
            
        handle_move(player, objects)

        # --- CHECK ENEMIES & TREASURE ---
        alive_enemies = [e for e in enemies if e.lives > 0]
        
        # If all enemies are dead and treasure hasn't spawned yet, create it
        if not alive_enemies and treasure is None:
            # Create treasure at the end of the map (approx block 55)
            treasure = Treasure(block_size * 55, HEIGHT - block_size - 96, 96)
            objects.append(treasure) # Add to objects so it gets drawn

        # --- ENEMY LOGIC ---
        for enemy in enemies:
            if enemy.lives > 0:
                enemy.loop(FPS)
                bullet = enemy.shoot()
                if bullet:
                    projectiles.append(bullet)

                # Check collision: Player vs Enemy
                if pygame.sprite.collide_mask(player, enemy):
                    # Goomba Stomp logic (if falling on top of enemy)
                    if player.y_vel > 0 and player.rect.bottom < enemy.rect.centery + 10:
                        enemy.lives -= 1
                        enemy.hit = True
                        player.y_vel = -8
                        player.jump_count = 1
                        score += 100
                    else:
                        player.make_hit()

        # Handle Projectiles (Bullets)
        for bullet in projectiles[:]:
            bullet.loop()
            # If bullet hits player
            if pygame.sprite.collide_rect(player, bullet):
                player.make_hit()
                projectiles.remove(bullet)
            # Remove bullet if it goes off screen to save memory
            elif bullet.rect.x > player.rect.x + 1000 or bullet.rect.x < player.rect.x - 1000:
                if bullet in projectiles:
                    projectiles.remove(bullet)

        # --- CHECK WIN/LOSE CONDITIONS ---
        
        # 1. Lose Condition: Out of lives or fell in hole
        if (player.lives <= 0 or player.rect.top > HEIGHT) and not game_over:
            game_over = True
            if not lose_played:
                pygame.mixer.music.stop()
                lose_sound.play()
                lose_played = True
        
        # 2. Win Condition (Touching Treasure)
        if treasure and pygame.sprite.collide_rect(player, treasure):
            game_won = True
            game_over = True # Stop the game loop logic

            if not win_played:
                pygame.mixer.music.stop()
                win_sound.play()
                win_played =True

        # --- DRAWING ---
        for tile in background:
            window.blit(bg_image, tile)
        
        for obj in objects:
            obj.draw(window, offset_x)
        
        for enemy in enemies:
            if enemy.lives > 0:
                enemy.draw(window, offset_x)
        
        for bullet in projectiles:
            bullet.draw(window, offset_x)
        
        player.draw(window, offset_x)
        draw_hud(window, player, score, start_ticks)

        # --- GAME OVER / WIN SCREEN ---
        if game_over:
            if game_won:
                # WIN SCREEN 
                window.fill((255, 204, 229)) 
                msg = "YOU WIN!"
                color = (255, 255, 255)
            else:
                # LOSE SCREEN 
                window.fill((255, 204, 229))
                msg = "GAME OVER"
                color = (255, 255, 255)

            font = pygame.font.SysFont("arial", 80)
            text = font.render(msg, True, color)
            window.blit(text, (WIDTH // 2 - text.get_width()//2, HEIGHT // 2 - 120))

            if button(window, "Restart",
                     WIDTH // 2 - 150, HEIGHT // 2 + 20, 300, 60):
                main(window)
                return

            if button(window, "Exit",
                     WIDTH // 2 - 150, HEIGHT // 2 + 100, 300, 60):
                pygame.quit()
                quit()

        pygame.display.update()

        # Update scroll based on player position
        # Keeps the player somewhat centered
        if ((player.rect.right - offset_x >= WIDTH - scroll_area_width) and player.x_vel > 0) or (
            (player.rect.left - offset_x <= scroll_area_width) and player.x_vel < 0):
            offset_x += player.x_vel

    pygame.quit()
    quit()

if __name__ == "__main__":
    main(window)