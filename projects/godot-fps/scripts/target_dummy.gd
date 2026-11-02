extends StaticBody3D

@export var max_health: float = 100.0
var current_health: float = 100.0

@onready var mesh: MeshInstance3D = $MeshInstance3D

func _ready() -> void:
	current_health = max_health

func take_damage(amount: float, hit_point: Vector3, hit_normal: Vector3) -> void:
	current_health -= amount
	print("[HIT] Target dummy took %.1f damage! Remaining HP: %.1f" % [amount, current_health])
	
	# Flash red
	var mat = mesh.get_active_material(0)
	if mat is StandardMaterial3D:
		mat.albedo_color = Color(1.0, 0.2, 0.2)
		await get_tree().create_timer(0.08).timeout
		mat.albedo_color = Color(0.8, 0.8, 0.8)

	if current_health <= 0:
		print("[KILL] Target dummy eliminated!")
		current_health = max_health # Respawn
