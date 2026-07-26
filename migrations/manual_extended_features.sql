-- Extended features migration (manual SQL companion to Flask-Migrate revision)
-- Run via: mysql -u ... -p penmozhi_db < migrations/manual_extended_features.sql

ALTER TABLE user_profiles
  ADD COLUMN mode VARCHAR(30) NOT NULL DEFAULT 'period',
  ADD COLUMN pin_hash VARCHAR(255) NULL;

ALTER TABLE symptom_tracking_logs
  ADD COLUMN tracking_category_id INT NULL,
  ADD COLUMN custom_tag_id INT NULL,
  ADD CONSTRAINT fk_symptom_tracking_category
    FOREIGN KEY (tracking_category_id) REFERENCES tracking_categories(id),
  ADD CONSTRAINT fk_symptom_custom_tag
    FOREIGN KEY (custom_tag_id) REFERENCES custom_tags(id);

ALTER TABLE daily_logs ADD COLUMN sleep_source VARCHAR(50) NULL;

ALTER TABLE health_profiles ADD COLUMN last_notified_for DATE NULL;

CREATE TABLE IF NOT EXISTS tracking_categories (
  id INT AUTO_INCREMENT PRIMARY KEY,
  `key` VARCHAR(100) NOT NULL UNIQUE,
  label VARCHAR(255) NOT NULL,
  label_ta VARCHAR(255) NOT NULL,
  `group` VARCHAR(50) NOT NULL,
  is_default TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS custom_tags (
  id INT AUTO_INCREMENT PRIMARY KEY,
  profile_id INT NOT NULL,
  label VARCHAR(255) NOT NULL,
  icon VARCHAR(100) NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_custom_tag_profile_label (profile_id, label),
  FOREIGN KEY (profile_id) REFERENCES user_profiles(id)
);

CREATE TABLE IF NOT EXISTS pregnancy_profiles (
  id INT AUTO_INCREMENT PRIMARY KEY,
  profile_id INT NOT NULL UNIQUE,
  last_menstrual_period DATE NULL,
  due_date DATE NULL,
  current_trimester INT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (profile_id) REFERENCES user_profiles(id)
);

CREATE TABLE IF NOT EXISTS perimenopause_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  profile_id INT NOT NULL,
  log_date DATE NOT NULL,
  hot_flashes TINYINT(1) NOT NULL DEFAULT 0,
  night_sweats TINYINT(1) NOT NULL DEFAULT 0,
  mood_changes VARCHAR(255) NULL,
  sleep_disruption TINYINT(1) NOT NULL DEFAULT 0,
  notes TEXT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_perimenopause_log_profile_date (profile_id, log_date),
  FOREIGN KEY (profile_id) REFERENCES user_profiles(id)
);

CREATE TABLE IF NOT EXISTS push_subscriptions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  profile_id INT NOT NULL,
  endpoint TEXT NOT NULL,
  p256dh VARCHAR(255) NOT NULL,
  auth VARCHAR(255) NOT NULL,
  device_type VARCHAR(50) NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (profile_id) REFERENCES user_profiles(id)
);

CREATE TABLE IF NOT EXISTS cycle_shares (
  id INT AUTO_INCREMENT PRIMARY KEY,
  owner_profile_id INT NOT NULL,
  shared_with_email VARCHAR(120) NOT NULL,
  shared_with_profile_id INT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  permissions JSON NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (owner_profile_id) REFERENCES user_profiles(id),
  FOREIGN KEY (shared_with_profile_id) REFERENCES user_profiles(id)
);

CREATE TABLE IF NOT EXISTS wearable_connections (
  id INT AUTO_INCREMENT PRIMARY KEY,
  profile_id INT NOT NULL,
  provider VARCHAR(50) NOT NULL,
  access_token TEXT NULL,
  refresh_token TEXT NULL,
  last_synced_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_wearable_profile_provider (profile_id, provider),
  FOREIGN KEY (profile_id) REFERENCES user_profiles(id)
);

CREATE TABLE IF NOT EXISTS subscriptions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  profile_id INT NOT NULL UNIQUE,
  plan VARCHAR(20) NOT NULL DEFAULT 'free',
  status VARCHAR(50) NOT NULL DEFAULT 'active',
  current_period_end DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (profile_id) REFERENCES user_profiles(id)
);
