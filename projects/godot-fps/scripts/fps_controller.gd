extends CharacterBody3D

signal health_changed(current: float, max_val: float)
signal ammo_changed(current: int, reserve: int)
signal weapon_switched(weapon_name: String)
signal player_eliminated()
signal damage_taken()

# --- Preloaded Weapon Data & Models ---
const WeaponsDatabase = preload("res://scripts/weapons_loader.gd")
const WeaponData = preload("res://scripts/weapon_data.gd")

var mesh_ak47: Mesh = null
var mesh_m4a1: Mesh = null
var mesh_awm: Mesh = null

# --- Movement Parameters ---
@export var walk_speed: float = 5.2
@export var sprint_speed: float = 8.0
@export var crouch_speed: float = 2.6
@export var jump_velocity: float = 4.8
@export var gravity: float = 14.0
@export var mouse_sensitivity: float = 0.0022

# --- Combat Stats ---
@export var max_health: float = 100.0
var current_health: float = 100.0
var is_dead: bool = false
var spawn_point: Vector3 = Vector3.ZERO

# --- References ---
@onready var head: Node3D = $Head
@onready var camera: Camera3D = $Head/Camera3D
@onready var weapon_holder: Node3D = $Head/Camera3D/WeaponHolder
@onready var weapon_mesh: MeshInstance3D = $Head/Camera3D/WeaponHolder/WeaponModel
@onready var raycast: RayCast3D = $Head/Camera3D/RayCast3D

# --- Weapon State ---
var current_weapon: WeaponData
var current_ammo: int = 30
var reserve_ammo: int = 90
var fire_timer: float = 0.0
var is_reloading: bool = false
var reload_timer: float = 0.0
var is_aiming: bool = false

# --- Recoil & Sway ---
var recoil_pitch: float = 0.0
var recoil_yaw: float = 0.0
var target_recoil_pitch: float = 0.0
var target_recoil_yaw: float = 0.0
var mouse_delta: Vector2 = Vector2.ZERO
var sway_offset: Vector3 = Vector3.ZERO
var base_fov: float = 85.0
var ads_fov: float = 65.0

func _ready() -> void:
	Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)
	spawn_point = global_position
	current_health = max_health

	# Load weapon meshes safely
	if ResourceLoader.exists("res://assets/weapons/ak47/AR_AK47.obj"):
		mesh_ak47 = load("res://assets/weapons/ak47/AR_AK47.obj")
	if ResourceLoader.exists("res://assets/weapons/m4a1/Custom_MAR_M4A1.obj"):
		mesh_m4a1 = load("res://assets/weapons/m4a1/Custom_MAR_M4A1.obj")
	if ResourceLoader.exists("res://assets/weapons/awm/SN_AWM300.obj"):
		mesh_awm = load("res://assets/weapons/awm/SN_AWM300.obj")

	switch_weapon(WeaponsDatabase.get_ak47())

func _unhandled_input(event: InputEvent) -> void:
	if is_dead:
		if event.is_action_pressed("jump") or (event is InputEventKey and event.is_pressed() and event.keycode == KEY_SPACE):
			respawn()
		return

	if event is InputEventMouseMotion:
		mouse_delta = event.relative
		rotate_y(-event.relative.x * mouse_sensitivity)
		head.rotate_x(-event.relative.y * mouse_sensitivity)
		head.rotation.x = clamp(head.rotation.x, deg_to_rad(-89), deg_to_rad(89))

	if event.is_action_pressed("ui_cancel"):
		if Input.get_mouse_mode() == Input.MOUSE_MODE_CAPTURED:
			Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
		else:
			Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)

	# Weapon Switch Shortcuts
	if event.is_action_pressed("weapon_1"):
		switch_weapon(WeaponsDatabase.get_ak47())
	elif event.is_action_pressed("weapon_2"):
		switch_weapon(WeaponsDatabase.get_m4a1())
	elif event.is_action_pressed("weapon_3"):
		switch_weapon(WeaponsDatabase.get_awm())

func _physics_process(delta: float) -> void:
	if is_dead:
		# Apply gravity while dead
		if not is_on_floor():
			velocity.y -= gravity * delta
			move_and_slide()
		return

	# Gravity
	if not is_on_floor():
		velocity.y -= gravity * delta

	# Jump
	if Input.is_action_just_pressed("jump") and is_on_floor():
		velocity.y = jump_velocity

	# Movement Speed & State
	var current_speed = walk_speed
	if Input.is_action_pressed("sprint") and is_on_floor() and not is_aiming:
		current_speed = sprint_speed
	elif Input.is_action_pressed("crouch"):
		current_speed = crouch_speed

	# Movement Direction
	var input_dir = Input.get_vector("move_left", "move_right", "move_forward", "move_backward")
	var direction = (transform.basis * Vector3(input_dir.x, 0, input_dir.y)).normalized()

	if direction:
		velocity.x = direction.x * current_speed
		velocity.z = direction.z * current_speed
	else:
		velocity.x = move_toward(velocity.x, 0, current_speed * delta * 10)
		velocity.z = move_toward(velocity.z, 0, current_speed * delta * 10)

	move_and_slide()

	# Weapon Logic
	handle_weapon(delta)
	handle_recoil_and_sway(delta)

func handle_weapon(delta: float) -> void:
	fire_timer -= delta

	# Reloading
	if is_reloading:
		reload_timer -= delta
		if reload_timer <= 0.0:
			finish_reload()
		return

	if Input.is_action_just_pressed("reload") and current_ammo < current_weapon.clip_size and reserve_ammo > 0:
		start_reload()
		return

	# ADS (Aim Down Sights)
	is_aiming = Input.is_action_pressed("aim")
	var target_pos = current_weapon.ads_position if is_aiming else current_weapon.view_model_position
	weapon_holder.position = weapon_holder.position.lerp(target_pos + sway_offset, delta * 14.0)
	camera.fov = lerp(camera.fov, ads_fov if is_aiming else base_fov, delta * 12.0)

	# Firing
	if Input.is_action_pressed("fire") and fire_timer <= 0.0:
		if current_ammo > 0:
			shoot()
		else:
			if reserve_ammo > 0:
				start_reload()

func shoot() -> void:
	current_ammo -= 1
	fire_timer = current_weapon.get_fire_delay()
	ammo_changed.emit(current_ammo, reserve_ammo)

	# Recoil Kick
	var v_recoil = deg_to_rad(current_weapon.recoil_vertical) * (0.6 if is_aiming else 1.0)
	var h_recoil = deg_to_rad(randf_range(-current_weapon.recoil_horizontal, current_weapon.recoil_horizontal))
	target_recoil_pitch += v_recoil
	target_recoil_yaw += h_recoil

	# Spread & Raycast
	var spread = current_weapon.base_spread
	if not is_on_floor():
		spread *= 4.0
	elif velocity.length() > 1.0:
		spread *= 2.0
	if is_aiming:
		spread *= 0.35

	var spread_offset = Vector3(
		randf_range(-spread, spread),
		randf_range(-spread, spread),
		0
	)

	raycast.target_position = Vector3(0, 0, -current_weapon.effective_range) + spread_offset
	raycast.force_raycast_update()

	if raycast.is_colliding():
		var hit_collider = raycast.get_collider()
		var hit_point = raycast.get_collision_point()
		var hit_normal = raycast.get_collision_normal()
		if hit_collider.has_method("take_damage"):
			hit_collider.take_damage(current_weapon.damage, hit_point, hit_normal)

func handle_recoil_and_sway(delta: float) -> void:
	# Recovery back to center
	target_recoil_pitch = lerp(target_recoil_pitch, 0.0, current_weapon.recoil_recovery_speed * delta)
	target_recoil_yaw = lerp(target_recoil_yaw, 0.0, current_weapon.recoil_recovery_speed * delta)

	# Apply recoil to camera
	head.rotation.x += target_recoil_pitch * delta * 15.0
	rotate_y(-target_recoil_yaw * delta * 15.0)

	# Mouse Sway
	var target_sway = Vector3(
		-mouse_delta.x * 0.0003,
		mouse_delta.y * 0.0003,
		0
	)
	sway_offset = sway_offset.lerp(target_sway, delta * 8.0)
	mouse_delta = Vector2.ZERO

func start_reload() -> void:
	is_reloading = true
	reload_timer = current_weapon.reload_time

func finish_reload() -> void:
	is_reloading = false
	var needed = current_weapon.clip_size - current_ammo
	var to_load = mini(needed, reserve_ammo)
	current_ammo += to_load
	reserve_ammo -= to_load
	ammo_changed.emit(current_ammo, reserve_ammo)

func switch_weapon(new_weapon: WeaponData) -> void:
	if is_reloading:
		is_reloading = false
	current_weapon = new_weapon
	current_ammo = current_weapon.clip_size
	reserve_ammo = current_weapon.max_reserve_ammo
	weapon_holder.position = current_weapon.view_model_position

	# Swap 3D mesh according to weapon
	if is_instance_valid(weapon_mesh):
		match new_weapon.weapon_name:
			"AK-47":
				if mesh_ak47: weapon_mesh.mesh = mesh_ak47
			"M4A1":
				if mesh_m4a1: weapon_mesh.mesh = mesh_m4a1
			"AWM-300":
				if mesh_awm: weapon_mesh.mesh = mesh_awm

	weapon_switched.emit(current_weapon.weapon_name)
	ammo_changed.emit(current_ammo, reserve_ammo)

func take_damage(amount: float, _hit_point: Vector3 = Vector3.ZERO, _hit_normal: Vector3 = Vector3.ZERO) -> void:
	if is_dead:
		return

	current_health = clamp(current_health - amount, 0.0, max_health)
	health_changed.emit(current_health, max_health)
	damage_taken.emit()

	# Trauma punch on camera
	target_recoil_pitch += deg_to_rad(randf_range(-1.2, 1.2))
	target_recoil_yaw += deg_to_rad(randf_range(-1.0, 1.0))

	if current_health <= 0.0:
		die()

func die() -> void:
	is_dead = true
	velocity = Vector3.ZERO
	player_eliminated.emit()
	print("[Player] Eliminated! Press SPACE to respawn.")

func respawn() -> void:
	is_dead = false
	current_health = max_health
	global_position = spawn_point
	health_changed.emit(current_health, max_health)
	ammo_changed.emit(current_ammo, reserve_ammo)
	print("[Player] Respawned!")
