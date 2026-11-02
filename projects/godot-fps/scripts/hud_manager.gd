extends CanvasLayer

@onready var health_label: Label = $HUD/BottomLeft/HealthLabel
@onready var health_bar: ProgressBar = $HUD/BottomLeft/HealthBar
@onready var ammo_label: Label = $HUD/BottomRight/AmmoLabel
@onready var weapon_label: Label = $HUD/BottomRight/WeaponLabel
@onready var damage_overlay: ColorRect = $DamageOverlay
@onready var death_overlay: Control = $DeathOverlay
@onready var killfeed_label: Label = $HUD/TopRight/KillFeedLabel

var damage_fade_alpha: float = 0.0

func _ready() -> void:
	death_overlay.visible = false
	killfeed_label.text = ""

	# Connect signals from Player if found
	var player = get_tree().get_first_node_in_group("player")
	if player:
		connect_player(player)

	# Connect to all tactical bots
	var bots = get_tree().get_nodes_in_group("bot")
	for b in bots:
		if b.has_signal("bot_eliminated"):
			b.bot_eliminated.connect(_on_bot_eliminated)

func connect_player(player: Node) -> void:
	if player.has_signal("health_changed"):
		player.health_changed.connect(_on_health_changed)
	if player.has_signal("ammo_changed"):
		player.ammo_changed.connect(_on_ammo_changed)
	if player.has_signal("weapon_switched"):
		player.weapon_switched.connect(_on_weapon_switched)
	if player.has_signal("damage_taken"):
		player.damage_taken.connect(_on_damage_taken)
	if player.has_signal("player_eliminated"):
		player.player_eliminated.connect(_on_player_eliminated)

func _process(delta: float) -> void:
	if damage_fade_alpha > 0.0:
		damage_fade_alpha = max(0.0, damage_fade_alpha - delta * 3.0)
		damage_overlay.color = Color(0.85, 0.1, 0.1, damage_fade_alpha * 0.4)

func _on_health_changed(current: float, max_val: float) -> void:
	health_label.text = "HP: %d / %d" % [int(current), int(max_val)]
	health_bar.max_value = max_val
	health_bar.value = current
	if current > 0.0 and death_overlay.visible:
		death_overlay.visible = false

func _on_ammo_changed(current: int, reserve: int) -> void:
	ammo_label.text = "%d / %d" % [current, reserve]

func _on_weapon_switched(weapon_name: String) -> void:
	weapon_label.text = weapon_name

func _on_damage_taken() -> void:
	damage_fade_alpha = 1.0

func _on_player_eliminated() -> void:
	death_overlay.visible = true

func _on_bot_eliminated(bot_name: String) -> void:
	killfeed_label.text = "✖ %s ELIMINATED" % bot_name
	await get_tree().create_timer(3.0).timeout
	if killfeed_label.text == "✖ %s ELIMINATED" % bot_name:
		killfeed_label.text = ""
