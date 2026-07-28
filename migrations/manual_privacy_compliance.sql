-- Privacy & compliance tables (idempotent companion to Alembic privacy_compliance_003)

CREATE TABLE IF NOT EXISTS privacy_requests (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NULL,
  user_email VARCHAR(120) NOT NULL,
  request_type VARCHAR(20) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  created_at DATETIME NOT NULL,
  completed_at DATETIME NULL,
  completed_by_admin_id INT NULL,
  INDEX ix_privacy_requests_user_id (user_id),
  CONSTRAINT fk_privacy_requests_user FOREIGN KEY (user_id) REFERENCES user_profiles(id) ON DELETE SET NULL,
  CONSTRAINT fk_privacy_requests_admin FOREIGN KEY (completed_by_admin_id) REFERENCES user_profiles(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS user_consents (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  consent_type VARCHAR(50) NOT NULL,
  policy_version VARCHAR(20) NOT NULL,
  granted_at DATETIME NOT NULL,
  context VARCHAR(255) NULL,
  INDEX ix_user_consents_user_id (user_id),
  CONSTRAINT fk_user_consents_user FOREIGN KEY (user_id) REFERENCES user_profiles(id) ON DELETE CASCADE
);
