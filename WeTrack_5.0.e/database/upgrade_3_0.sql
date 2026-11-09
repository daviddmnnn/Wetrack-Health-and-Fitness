-- WeTrack exercise-plan database compatibility migration.
-- Run this once on an existing database if the activities table predates
-- the exercise-plan feature. The application also checks these columns
-- automatically when a plan is completed.

USE wetrack;

SET @has_is_plan = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='activities' AND COLUMN_NAME='isPlanRecord');
SET @sql = IF(@has_is_plan=0, 'ALTER TABLE activities ADD COLUMN isPlanRecord BOOLEAN DEFAULT FALSE', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @has_plan_progress = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='activities' AND COLUMN_NAME='planProgressID');
SET @sql = IF(@has_plan_progress=0, 'ALTER TABLE activities ADD COLUMN planProgressID INT NULL', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

CREATE TABLE IF NOT EXISTS exercise_plans (
    planID INT AUTO_INCREMENT PRIMARY KEY,
    activityType VARCHAR(80) NOT NULL,
    levelMode ENUM('Beginner','Intermediate','Vigorous') NOT NULL,
    levelNumber INT NOT NULL,
    durationMin INT NOT NULL,
    intensity ENUM('Light','Moderate','Vigorous') NOT NULL,
    description VARCHAR(255),
    UNIQUE KEY uq_plan_level (activityType, levelMode, levelNumber)
);

CREATE TABLE IF NOT EXISTS plan_progress (
    progressID INT AUTO_INCREMENT PRIMARY KEY,
    userID INT NOT NULL,
    planID INT NOT NULL,
    completedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    note VARCHAR(255),
    UNIQUE KEY uq_user_plan (userID, planID),
    FOREIGN KEY (userID) REFERENCES users(userID) ON DELETE CASCADE,
    FOREIGN KEY (planID) REFERENCES exercise_plans(planID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reports (
    reportID INT AUTO_INCREMENT PRIMARY KEY,
    userID INT NOT NULL,
    type ENUM('Report','Feedback') NOT NULL DEFAULT 'Report',
    subject VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(30) DEFAULT 'Submitted',
    dateSubmitted DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (userID) REFERENCES users(userID) ON DELETE CASCADE,
    INDEX idx_report_user_date (userID, dateSubmitted)
);
-- Preloaded prototype exercise plans.
INSERT IGNORE INTO exercise_plans (activityType,levelMode,levelNumber,durationMin,intensity,description) VALUES
('Walking','Beginner',1,15,'Light','Easy walking session'),('Walking','Beginner',2,20,'Light','Easy walking session'),('Walking','Beginner',3,25,'Light','Easy walking session'),
('Walking','Intermediate',1,30,'Moderate','Steady walking session'),('Walking','Intermediate',2,35,'Moderate','Steady walking session'),('Walking','Intermediate',3,40,'Moderate','Steady walking session'),('Walking','Intermediate',4,45,'Moderate','Steady walking session'),('Walking','Intermediate',5,50,'Moderate','Steady walking session'),
('Walking','Vigorous',1,30,'Vigorous','Fast-paced walking session'),('Walking','Vigorous',2,35,'Vigorous','Fast-paced walking session'),('Walking','Vigorous',3,40,'Vigorous','Fast-paced walking session'),('Walking','Vigorous',4,45,'Vigorous','Fast-paced walking session'),('Walking','Vigorous',5,50,'Vigorous','Fast-paced walking session'),('Walking','Vigorous',6,55,'Vigorous','Fast-paced walking session'),('Walking','Vigorous',7,60,'Vigorous','Fast-paced walking session'),
('Running','Beginner',1,15,'Light','Introductory running session'),('Running','Beginner',2,20,'Light','Introductory running session'),('Running','Beginner',3,25,'Light','Introductory running session'),
('Running','Intermediate',1,30,'Moderate','Steady running session'),('Running','Intermediate',2,35,'Moderate','Steady running session'),('Running','Intermediate',3,40,'Moderate','Steady running session'),('Running','Intermediate',4,45,'Moderate','Steady running session'),('Running','Intermediate',5,50,'Moderate','Steady running session'),
('Running','Vigorous',1,30,'Vigorous','Vigorous running session'),('Running','Vigorous',2,35,'Vigorous','Vigorous running session'),('Running','Vigorous',3,40,'Vigorous','Vigorous running session'),('Running','Vigorous',4,45,'Vigorous','Vigorous running session'),('Running','Vigorous',5,50,'Vigorous','Vigorous running session'),('Running','Vigorous',6,55,'Vigorous','Vigorous running session'),('Running','Vigorous',7,60,'Vigorous','Vigorous running session'),
('Jogging','Beginner',1,15,'Light','Introductory jogging session'),('Jogging','Beginner',2,20,'Light','Introductory jogging session'),('Jogging','Beginner',3,25,'Light','Introductory jogging session'),
('Jogging','Intermediate',1,30,'Moderate','Steady jogging session'),('Jogging','Intermediate',2,35,'Moderate','Steady jogging session'),('Jogging','Intermediate',3,40,'Moderate','Steady jogging session'),('Jogging','Intermediate',4,45,'Moderate','Steady jogging session'),('Jogging','Intermediate',5,50,'Moderate','Steady jogging session'),
('Jogging','Vigorous',1,30,'Vigorous','Vigorous jogging session'),('Jogging','Vigorous',2,35,'Vigorous','Vigorous jogging session'),('Jogging','Vigorous',3,40,'Vigorous','Vigorous jogging session'),('Jogging','Vigorous',4,45,'Vigorous','Vigorous jogging session'),('Jogging','Vigorous',5,50,'Vigorous','Vigorous jogging session'),('Jogging','Vigorous',6,55,'Vigorous','Vigorous jogging session'),('Jogging','Vigorous',7,60,'Vigorous','Vigorous jogging session'),
('Cycling','Beginner',1,15,'Light','Introductory cycling session'),('Cycling','Beginner',2,20,'Light','Introductory cycling session'),('Cycling','Beginner',3,25,'Light','Introductory cycling session'),
('Cycling','Intermediate',1,30,'Moderate','Steady cycling session'),('Cycling','Intermediate',2,35,'Moderate','Steady cycling session'),('Cycling','Intermediate',3,40,'Moderate','Steady cycling session'),('Cycling','Intermediate',4,45,'Moderate','Steady cycling session'),('Cycling','Intermediate',5,50,'Moderate','Steady cycling session'),
('Cycling','Vigorous',1,30,'Vigorous','Vigorous cycling session'),('Cycling','Vigorous',2,35,'Vigorous','Vigorous cycling session'),('Cycling','Vigorous',3,40,'Vigorous','Vigorous cycling session'),('Cycling','Vigorous',4,45,'Vigorous','Vigorous cycling session'),('Cycling','Vigorous',5,50,'Vigorous','Vigorous cycling session'),('Cycling','Vigorous',6,55,'Vigorous','Vigorous cycling session'),('Cycling','Vigorous',7,60,'Vigorous','Vigorous cycling session');

-- The prototype includes a set of plan levels for the example exercise modes.
INSERT IGNORE INTO exercise_plans (activityType,levelMode,levelNumber,durationMin,intensity,description) VALUES
('Swimming','Beginner',1,15,'Light','Beginner swimming session'),
('Swimming','Beginner',2,20,'Light','Beginner swimming session'),
('Swimming','Beginner',3,25,'Light','Beginner swimming session'),
('Swimming','Intermediate',1,30,'Moderate','Intermediate swimming session'),
('Swimming','Intermediate',2,35,'Moderate','Intermediate swimming session'),
('Swimming','Intermediate',3,40,'Moderate','Intermediate swimming session'),
('Swimming','Intermediate',4,45,'Moderate','Intermediate swimming session'),
('Swimming','Intermediate',5,50,'Moderate','Intermediate swimming session'),
('Swimming','Vigorous',1,30,'Vigorous','Vigorous swimming session'),
('Swimming','Vigorous',2,35,'Vigorous','Vigorous swimming session'),
('Swimming','Vigorous',3,40,'Vigorous','Vigorous swimming session'),
('Swimming','Vigorous',4,45,'Vigorous','Vigorous swimming session'),
('Swimming','Vigorous',5,50,'Vigorous','Vigorous swimming session'),
('Swimming','Vigorous',6,55,'Vigorous','Vigorous swimming session'),
('Swimming','Vigorous',7,60,'Vigorous','Vigorous swimming session'),
('Badminton','Beginner',1,15,'Light','Beginner badminton session'),
('Badminton','Beginner',2,20,'Light','Beginner badminton session'),
('Badminton','Beginner',3,25,'Light','Beginner badminton session'),
('Badminton','Intermediate',1,30,'Moderate','Intermediate badminton session'),
('Badminton','Intermediate',2,35,'Moderate','Intermediate badminton session'),
('Badminton','Intermediate',3,40,'Moderate','Intermediate badminton session'),
('Badminton','Intermediate',4,45,'Moderate','Intermediate badminton session'),
('Badminton','Intermediate',5,50,'Moderate','Intermediate badminton session'),
('Badminton','Vigorous',1,30,'Vigorous','Vigorous badminton session'),
('Badminton','Vigorous',2,35,'Vigorous','Vigorous badminton session'),
('Badminton','Vigorous',3,40,'Vigorous','Vigorous badminton session'),
('Badminton','Vigorous',4,45,'Vigorous','Vigorous badminton session'),
('Badminton','Vigorous',5,50,'Vigorous','Vigorous badminton session'),
('Badminton','Vigorous',6,55,'Vigorous','Vigorous badminton session'),
('Badminton','Vigorous',7,60,'Vigorous','Vigorous badminton session'),
('Basketball','Beginner',1,15,'Light','Beginner basketball session'),
('Basketball','Beginner',2,20,'Light','Beginner basketball session'),
('Basketball','Beginner',3,25,'Light','Beginner basketball session'),
('Basketball','Intermediate',1,30,'Moderate','Intermediate basketball session'),
('Basketball','Intermediate',2,35,'Moderate','Intermediate basketball session'),
('Basketball','Intermediate',3,40,'Moderate','Intermediate basketball session'),
('Basketball','Intermediate',4,45,'Moderate','Intermediate basketball session'),
('Basketball','Intermediate',5,50,'Moderate','Intermediate basketball session'),
('Basketball','Vigorous',1,30,'Vigorous','Vigorous basketball session'),
('Basketball','Vigorous',2,35,'Vigorous','Vigorous basketball session'),
('Basketball','Vigorous',3,40,'Vigorous','Vigorous basketball session'),
('Basketball','Vigorous',4,45,'Vigorous','Vigorous basketball session'),
('Basketball','Vigorous',5,50,'Vigorous','Vigorous basketball session'),
('Basketball','Vigorous',6,55,'Vigorous','Vigorous basketball session'),
('Basketball','Vigorous',7,60,'Vigorous','Vigorous basketball session'),
('Home Workout','Beginner',1,15,'Light','Beginner home workout session'),
('Home Workout','Beginner',2,20,'Light','Beginner home workout session'),
('Home Workout','Beginner',3,25,'Light','Beginner home workout session'),
('Home Workout','Intermediate',1,30,'Moderate','Intermediate home workout session'),
('Home Workout','Intermediate',2,35,'Moderate','Intermediate home workout session'),
('Home Workout','Intermediate',3,40,'Moderate','Intermediate home workout session'),
('Home Workout','Intermediate',4,45,'Moderate','Intermediate home workout session'),
('Home Workout','Intermediate',5,50,'Moderate','Intermediate home workout session'),
('Home Workout','Vigorous',1,30,'Vigorous','Vigorous home workout session'),
('Home Workout','Vigorous',2,35,'Vigorous','Vigorous home workout session'),
('Home Workout','Vigorous',3,40,'Vigorous','Vigorous home workout session'),
('Home Workout','Vigorous',4,45,'Vigorous','Vigorous home workout session'),
('Home Workout','Vigorous',5,50,'Vigorous','Vigorous home workout session'),
('Home Workout','Vigorous',6,55,'Vigorous','Vigorous home workout session'),
('Home Workout','Vigorous',7,60,'Vigorous','Vigorous home workout session');
