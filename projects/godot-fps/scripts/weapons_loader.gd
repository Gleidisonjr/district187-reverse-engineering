class_name WeaponsDatabase
extends RefCounted

static func get_ak47() -> WeaponData:
	var w = WeaponData.new()
	w.weapon_id = 1120001
	w.weapon_name = "AK-47"
	w.category = "AssaultRifle"
	w.damage = 34.0
	w.fire_rate = 600.0
	w.clip_size = 30
	w.max_reserve_ammo = 90
	w.reload_time = 2.4
	w.recoil_vertical = 2.4
	w.recoil_horizontal = 1.1
	w.recoil_recovery_speed = 7.5
	w.base_spread = 0.015
	w.max_spread = 0.085
	w.effective_range = 80.0
	w.view_model_position = Vector3(0.22, -0.25, -0.42)
	w.ads_position = Vector3(0.0, -0.18, -0.32)
	return w

static func get_m4a1() -> WeaponData:
	var w = WeaponData.new()
	w.weapon_id = 1110002
	w.weapon_name = "M4A1"
	w.category = "AssaultRifle"
	w.damage = 28.0
	w.fire_rate = 680.0
	w.clip_size = 30
	w.max_reserve_ammo = 90
	w.reload_time = 2.2
	w.recoil_vertical = 1.6
	w.recoil_horizontal = 0.6
	w.recoil_recovery_speed = 9.0
	w.base_spread = 0.010
	w.max_spread = 0.060
	w.effective_range = 85.0
	w.view_model_position = Vector3(0.20, -0.24, -0.40)
	w.ads_position = Vector3(0.0, -0.17, -0.30)
	return w

static func get_awm() -> WeaponData:
	var w = WeaponData.new()
	w.weapon_id = 1140003
	w.weapon_name = "AWM-300"
	w.category = "Sniper"
	w.damage = 115.0
	w.fire_rate = 42.0
	w.clip_size = 5
	w.max_reserve_ammo = 30
	w.reload_time = 3.5
	w.recoil_vertical = 6.0
	w.recoil_horizontal = 1.8
	w.recoil_recovery_speed = 3.0
	w.base_spread = 0.001
	w.max_spread = 0.150
	w.effective_range = 250.0
	w.view_model_position = Vector3(0.25, -0.28, -0.48)
	w.ads_position = Vector3(0.0, -0.19, -0.35)
	return w
