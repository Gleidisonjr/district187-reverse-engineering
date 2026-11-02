class_name TacticalBot
extends CharacterBody3D

signal bot_eliminated(bot_name: String)

enum BotState { PATROL, CHASE, ENGAGE, TAKE_COVER, DEAD }

# --- Bot Config ---
@export var bot_name: String = "Bot Alpha"
@export var max_health: float = 100.0
@export var move_speed: float = 4.2
@export var sprint_speed: float = 6.5
@export var detection_range: float = 35.0
@export var attack_range: float = 25.0
@export var fire_rate: float = 550.0 # RPM
@export var bullet_damage: float = 18.0
@export var burst_count: int = 3
@export var burst_cooldown: float = 0.8

# --- State Variables ---
var current_health: float = 100.0
var state: BotState = BotState.PATROL
var target_player: Node3D = null
var current_burst_left: int = 0
var shot_timer: float = 0.0
var cooldown_timer: float = 0.0
var patrol_timer: float = 0.0
var respawn_timer: float = 0.0
var initial_spawn_position: Vector3

# --- Node References ---
@onready var nav_agent: NavigationAgent3D = $NavigationAgent3D
@onready var los_ray: RayCast3D = $Head/RayCast3D
@onready var head: Node3D = $Head
@onready var mesh_body: MeshInstance3D = $BodyMesh
@onready var gun_mesh: MeshInstance3D = $Head/GunMesh

func _ready() -> void:
	current_health = max_health
	initial_spawn_position = global_position
	# Find player in tree
	await get_tree().process_frame
	target_player = get_tree().get_first_node_in_group("player")
	pick_random_patrol()

func _physics_process(delta: float) -> void:
	if state == BotState.DEAD:
		respawn_timer -= delta
		if respawn_timer <= 0.0:
			respawn()
		return

	# Gravity
	if not is_on_floor():
		velocity.y -= 14.0 * delta

	# Vision & Line of Sight Check
	var can_see_player = check_line_of_sight()

	match state:
		BotState.PATROL:
			handle_patrol(delta, can_see_player)
		BotState.CHASE:
			handle_chase(delta, can_see_player)
		BotState.ENGAGE:
			handle_engage(delta, can_see_player)

	move_and_slide()

func check_line_of_sight() -> bool:
	if not is_instance_valid(target_player):
		return false

	var dist = global_position.distance_to(target_player.global_position)
	if dist > detection_range:
		return false

	los_ray.target_position = los_ray.to_local(target_player.global_position + Vector3(0, 1.2, 0))
	los_ray.force_raycast_update()

	if los_ray.is_colliding():
		var col = los_ray.get_collider()
		return col == target_player or col.is_in_group("player")
	return false

func handle_patrol(delta: float, can_see_player: bool) -> void:
	if can_see_player:
		state = BotState.ENGAGE
		return

	patrol_timer -= delta
	if patrol_timer <= 0.0 or nav_agent.is_navigation_finished():
		pick_random_patrol()

	move_along_nav(move_speed)

func handle_chase(delta: float, can_see_player: bool) -> void:
	if can_see_player:
		var dist = global_position.distance_to(target_player.global_position)
		if dist <= attack_range:
			state = BotState.ENGAGE
			return

	if is_instance_valid(target_player):
		nav_agent.target_position = target_player.global_position
		move_along_nav(sprint_speed)
	else:
		state = BotState.PATROL

func handle_engage(delta: float, can_see_player: bool) -> void:
	if not can_see_player or not is_instance_valid(target_player):
		state = BotState.CHASE
		return

	# Face towards player smoothly
	var look_target = target_player.global_position
	look_target.y = global_position.y
	look_at(look_target, Vector3.UP)
	head.look_at(target_player.global_position + Vector3(0, 1.2, 0), Vector3.UP)

	# Combat strafe movement
	velocity.x = move_toward(velocity.x, 0, move_speed * delta * 5)
	velocity.z = move_toward(velocity.z, 0, move_speed * delta * 5)

	# Firing logic
	handle_firing(delta)

func handle_firing(delta: float) -> void:
	shot_timer -= delta
	cooldown_timer -= delta

	if cooldown_timer <= 0.0 and current_burst_left == 0:
		current_burst_left = burst_count
		cooldown_timer = burst_cooldown

	if current_burst_left > 0 and shot_timer <= 0.0:
		fire_bullet()
		current_burst_left -= 1
		shot_timer = 60.0 / fire_rate

func fire_bullet() -> void:
	# Add slight bot spread for balanced tactical difficulty
	var spread_offset = Vector3(
		randf_range(-0.06, 0.06),
		randf_range(-0.06, 0.06),
		0
	)
	var ray_target = (target_player.global_position + Vector3(0, 1.2, 0) + spread_offset) - head.global_position
	los_ray.target_position = los_ray.to_local(head.global_position + ray_target.normalized() * attack_range)
	los_ray.force_raycast_update()

	# Visual muzzle kick
	gun_mesh.position.z += 0.04
	await get_tree().create_timer(0.04).timeout
	gun_mesh.position.z -= 0.04

	if los_ray.is_colliding():
		var col = los_ray.get_collider()
		if col.has_method("take_damage"):
			col.take_damage(bullet_damage, los_ray.get_collision_point(), los_ray.get_collision_normal())

func move_along_nav(speed: float) -> void:
	if nav_agent.is_navigation_finished():
		velocity.x = 0
		velocity.z = 0
		return

	var next_path_pos = nav_agent.get_next_path_position()
	var new_velocity = (next_path_pos - global_position).normalized() * speed
	velocity.x = new_velocity.x
	velocity.z = new_velocity.z

	# Face movement direction
	var look_target = next_path_pos
	look_target.y = global_position.y
	if global_position.distance_squared_to(look_target) > 0.1:
		look_at(look_target, Vector3.UP)

func pick_random_patrol() -> void:
	patrol_timer = randf_range(3.0, 6.0)
	var random_offset = Vector3(randf_range(-15, 15), 0, randf_range(-15, 15))
	nav_agent.target_position = initial_spawn_position + random_offset

func take_damage(amount: float, hit_point: Vector3, hit_normal: Vector3) -> void:
	if state == BotState.DEAD:
		return

	# Headshot multiplier if hit near head
	if hit_point.y - global_position.y > 1.35:
		amount *= 2.5
		print("[%s] HEADSHOT! Critical hit: %.1f dmg" % [bot_name, amount])

	current_health -= amount
	print("[%s] Took %.1f dmg. Remaining HP: %.1f" % [bot_name, amount, current_health])

	# Alert bot to attacker
	state = BotState.ENGAGE

	# Flash hurt material
	flash_hurt()

	if current_health <= 0.0:
		die()

func flash_hurt() -> void:
	var mat = mesh_body.get_active_material(0)
	if mat is StandardMaterial3D:
		mat.albedo_color = Color(1.0, 0.1, 0.1)
		await get_tree().create_timer(0.08).timeout
		mat.albedo_color = Color(0.2, 0.35, 0.6) # Standard tactical uniform blue

func die() -> void:
	state = BotState.DEAD
	velocity = Vector3.ZERO
	respawn_timer = 4.0
	bot_eliminated.emit(bot_name)
	print("[%s] Eliminated! Respawning in 4s..." % bot_name)
	# Turn off collision and hide while dead
	set_collision_layer_value(1, false)
	visible = false

func respawn() -> void:
	current_health = max_health
	global_position = initial_spawn_position
	visible = true
	set_collision_layer_value(1, true)
	state = BotState.PATROL
	pick_random_patrol()
	print("[%s] Respawned at base!" % bot_name)
