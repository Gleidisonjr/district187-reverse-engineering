class_name WeaponData
extends Resource

@export var weapon_id: int = 1120001
@export var weapon_name: String = "AK-47"
@export var category: String = "AssaultRifle"

# Combat & Ballistics (Directly calibrated from District 187 tables)
@export var damage: float = 34.0
@export var fire_rate: float = 600.0 # Rounds Per Minute
@export var clip_size: int = 30
@export var max_reserve_ammo: int = 90
@export var reload_time: float = 2.4 # Seconds

# Recoil & Handling
@export var recoil_vertical: float = 2.2
@export var recoil_horizontal: float = 0.8
@export var recoil_recovery_speed: float = 8.0
@export var base_spread: float = 0.015
@export var max_spread: float = 0.08
@export var effective_range: float = 80.0 # Meters before falloff

# Visuals
@export var mesh_scene: PackedScene
@export var view_model_position: Vector3 = Vector3(0.2, -0.22, -0.4)
@export var ads_position: Vector3 = Vector3(0.0, -0.16, -0.28)

func get_fire_delay() -> float:
	return 60.0 / fire_rate
