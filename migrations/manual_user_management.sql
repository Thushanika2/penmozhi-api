-- Manual migration for user management (run if flask db upgrade is unavailable)
ALTER TABLE user_profiles
  ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active',
  ADD COLUMN token_valid_after DATETIME NULL,
  ADD COLUMN is_test_account TINYINT(1) NOT NULL DEFAULT 0,
  ADD COLUMN last_active_at DATETIME NULL,
  ADD COLUMN login_count INT NOT NULL DEFAULT 0;

CREATE TABLE admin_action_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  admin_id INT NOT NULL,
  action_type VARCHAR(50) NOT NULL,
  target_user_id INT NULL,
  timestamp DATETIME NOT NULL,
  notes VARCHAR(500) NULL,
  FOREIGN KEY (admin_id) REFERENCES user_profiles(id) ON DELETE CASCADE,
  FOREIGN KEY (target_user_id) REFERENCES user_profiles(id) ON DELETE SET NULL,
  INDEX ix_admin_action_logs_target_user_id (target_user_id),
  INDEX ix_admin_action_logs_admin_id (admin_id)
);
