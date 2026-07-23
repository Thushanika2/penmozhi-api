-- Module 3: Period calendar & daily logs

ALTER TABLE cycle_history_logs
  ADD COLUMN IF NOT EXISTS notes TEXT NULL;

CREATE TABLE IF NOT EXISTS daily_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  profile_id INT NOT NULL,
  log_date DATE NOT NULL,
  flow_level VARCHAR(20) NULL,
  pain_level VARCHAR(20) NULL,
  mood VARCHAR(50) NULL,
  energy VARCHAR(20) NULL,
  sleep_hours FLOAT NULL,
  exercise VARCHAR(50) NULL,
  weight FLOAT NULL,
  basal_temp FLOAT NULL,
  cervical_fluid VARCHAR(20) NULL,
  sexual_activity TINYINT(1) NOT NULL DEFAULT 0,
  notes TEXT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (profile_id) REFERENCES user_profiles(id),
  UNIQUE KEY uq_daily_log_profile_date (profile_id, log_date)
);
