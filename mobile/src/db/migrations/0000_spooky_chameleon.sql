CREATE TABLE `food_micronutrients` (
	`id` text PRIMARY KEY NOT NULL,
	`food_id` text NOT NULL,
	`nutrient_code` text NOT NULL,
	`amount_per_100g` real NOT NULL,
	`updated_at` text NOT NULL,
	`deleted_at` text
);
--> statement-breakpoint
CREATE TABLE `food_nutrients` (
	`id` text PRIMARY KEY NOT NULL,
	`food_id` text NOT NULL,
	`calories_kcal` real NOT NULL,
	`protein_g` real NOT NULL,
	`carbs_g` real NOT NULL,
	`fat_g` real NOT NULL,
	`updated_at` text NOT NULL,
	`deleted_at` text
);
--> statement-breakpoint
CREATE TABLE `foods` (
	`id` text PRIMARY KEY NOT NULL,
	`source` text NOT NULL,
	`source_id` text,
	`barcode` text,
	`name` text NOT NULL,
	`brand` text,
	`serving_size_g` real,
	`serving_unit_label` text,
	`image_url` text,
	`is_custom` integer DEFAULT false NOT NULL,
	`created_by_user_id` text,
	`updated_at` text NOT NULL,
	`deleted_at` text
);
--> statement-breakpoint
CREATE TABLE `local_meta` (
	`id` integer PRIMARY KEY DEFAULT 1 NOT NULL,
	`device_id` text NOT NULL,
	`user_id` text,
	`server_base_url` text,
	`timezone` text DEFAULT 'UTC' NOT NULL,
	`last_synced_at` text
);
--> statement-breakpoint
CREATE TABLE `log_entries` (
	`id` text PRIMARY KEY NOT NULL,
	`user_id` text NOT NULL,
	`food_id` text,
	`recipe_id` text,
	`quantity_g` real,
	`quantity_servings` real,
	`meal_type` text NOT NULL,
	`logged_at` text NOT NULL,
	`log_date` text NOT NULL,
	`notes` text,
	`updated_at` text NOT NULL,
	`deleted_at` text
);
--> statement-breakpoint
CREATE TABLE `nutrient_reference` (
	`code` text PRIMARY KEY NOT NULL,
	`display_name` text NOT NULL,
	`unit` text NOT NULL,
	`category` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `recipe_items` (
	`id` text PRIMARY KEY NOT NULL,
	`recipe_id` text NOT NULL,
	`food_id` text NOT NULL,
	`quantity_g` real NOT NULL
);
--> statement-breakpoint
CREATE TABLE `recipes` (
	`id` text PRIMARY KEY NOT NULL,
	`user_id` text NOT NULL,
	`name` text NOT NULL,
	`servings` real DEFAULT 1 NOT NULL,
	`instructions` text,
	`updated_at` text NOT NULL,
	`deleted_at` text
);
--> statement-breakpoint
CREATE TABLE `sync_conflicts` (
	`id` text PRIMARY KEY NOT NULL,
	`entity_type` text NOT NULL,
	`entity_id` text NOT NULL,
	`local_version_json` text NOT NULL,
	`server_version_json` text NOT NULL,
	`created_at` text NOT NULL,
	`resolved` integer DEFAULT false NOT NULL
);
--> statement-breakpoint
CREATE TABLE `user_profile` (
	`id` text PRIMARY KEY NOT NULL,
	`user_id` text NOT NULL,
	`display_name` text,
	`date_of_birth` text,
	`sex` text,
	`height_cm` real,
	`weight_kg` real,
	`activity_level` text,
	`goal` text,
	`weekly_goal_rate_kg` real,
	`timezone` text DEFAULT 'UTC' NOT NULL,
	`updated_at` text NOT NULL,
	`deleted_at` text
);
--> statement-breakpoint
CREATE TABLE `user_targets` (
	`id` text PRIMARY KEY NOT NULL,
	`user_id` text NOT NULL,
	`effective_date` text NOT NULL,
	`calories_kcal` real NOT NULL,
	`protein_g` real NOT NULL,
	`carbs_g` real NOT NULL,
	`fat_g` real NOT NULL,
	`fiber_g` real,
	`source` text NOT NULL,
	`updated_at` text NOT NULL,
	`deleted_at` text
);
