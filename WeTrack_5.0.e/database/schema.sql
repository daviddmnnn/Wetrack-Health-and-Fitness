CREATE DATABASE IF NOT EXISTS wetrack CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE wetrack;

CREATE TABLE IF NOT EXISTS users (
    userID INT AUTO_INCREMENT PRIMARY KEY,
    accountID VARCHAR(20) UNIQUE,
    lastname VARCHAR(80) NOT NULL,
    firstname VARCHAR(80) NOT NULL,
    birthdate DATE NOT NULL,
    gender ENUM('Male','Female','Other','Prefer not to say') DEFAULT 'Prefer not to say',
    email VARCHAR(150) NOT NULL UNIQUE,
    contactNo VARCHAR(30),
    username VARCHAR(50) NOT NULL UNIQUE,
    passwordHash VARCHAR(255) NOT NULL,
    profilePicture VARCHAR(255) NULL,
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_info (
    infID INT AUTO_INCREMENT PRIMARY KEY,
    userID INT NOT NULL UNIQUE,
    heightCm DECIMAL(6,2),
    weightKg DECIMAL(6,2),
    bloodType VARCHAR(5),
    updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (userID) REFERENCES users(userID) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS activities (
    actID INT AUTO_INCREMENT PRIMARY KEY,
    userID INT NOT NULL,
    actType VARCHAR(80) NOT NULL,
    durationMin INT NOT NULL,
    intensity ENUM('Light','Moderate','Vigorous') DEFAULT 'Moderate',
    caloriesBurned DECIMAL(8,2) DEFAULT 0,
    steps INT DEFAULT 0,
    activityDate DATE NOT NULL,
    notes VARCHAR(255),
    isPlanRecord BOOLEAN DEFAULT FALSE,
    planProgressID INT NULL,
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (userID) REFERENCES users(userID) ON DELETE CASCADE,
    INDEX idx_activity_user_date (userID, activityDate)
);

CREATE TABLE IF NOT EXISTS foods (
    foodID INT AUTO_INCREMENT PRIMARY KEY,
    foodName VARCHAR(100) NOT NULL,
    foodGroup ENUM('Protein','Carbs','Veggies','Fruits','Sweets','Dairy','Beverage','Other') NOT NULL,
    servingUnit VARCHAR(30) NOT NULL,
    caloriesPerUnit DECIMAL(8,2) NOT NULL,
    UNIQUE KEY uq_food (foodName, servingUnit)
);

CREATE TABLE IF NOT EXISTS diet_logs (
    dietID INT AUTO_INCREMENT PRIMARY KEY,
    userID INT NOT NULL,
    foodID INT NOT NULL,
    mealType ENUM('Breakfast','Lunch','Dinner','Snack') NOT NULL,
    quantity DECIMAL(8,2) NOT NULL,
    calories DECIMAL(8,2) NOT NULL,
    logDate DATE NOT NULL,
    notes VARCHAR(255),
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (userID) REFERENCES users(userID) ON DELETE CASCADE,
    FOREIGN KEY (foodID) REFERENCES foods(foodID),
    INDEX idx_diet_user_date (userID, logDate)
);

CREATE TABLE IF NOT EXISTS sleep_logs (
    sleepID INT AUTO_INCREMENT PRIMARY KEY,
    userID INT NOT NULL,
    sleepDate DATE NOT NULL,
    durationHours DECIMAL(4,2) NOT NULL,
    sleepQuality ENUM('Poor','Fair','Good','Excellent') DEFAULT 'Good',
    notes VARCHAR(255),
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (userID) REFERENCES users(userID) ON DELETE CASCADE,
    INDEX idx_sleep_user_date (userID, sleepDate)
);

CREATE TABLE IF NOT EXISTS goals (
    goalID INT AUTO_INCREMENT PRIMARY KEY,
    userID INT NOT NULL,
    goalType ENUM('Fitness','Diet') NOT NULL,
    title VARCHAR(150) NOT NULL,
    activityType VARCHAR(80),
    targetValue DECIMAL(10,2),
    targetUnit VARCHAR(40),
    targetDescription VARCHAR(255),
    startDate DATE NOT NULL,
    endDate DATE NOT NULL,
    status ENUM('Active','Completed','Cancelled') DEFAULT 'Active',
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (userID) REFERENCES users(userID) ON DELETE CASCADE,
    INDEX idx_goal_user_date (userID, endDate)
);

CREATE TABLE IF NOT EXISTS goal_updates (
    updateID INT AUTO_INCREMENT PRIMARY KEY,
    goalID INT NOT NULL,
    updateDate DATE NOT NULL,
    progressValue DECIMAL(10,2) DEFAULT 0,
    note VARCHAR(255),
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (goalID) REFERENCES goals(goalID) ON DELETE CASCADE,
    INDEX idx_goal_update (goalID, updateDate)
);

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

INSERT IGNORE INTO foods (foodName, foodGroup, servingUnit, caloriesPerUnit) VALUES
('White Rice','Carbs','cup',205),('Brown Rice','Carbs','cup',215),('Bread','Carbs','slice',80),
('Chicken Breast','Protein','100g',165),('Beef','Protein','100g',250),('Egg','Protein','piece',78),
('Fish','Protein','100g',150),('Tofu','Protein','100g',76),('Mixed Vegetables','Veggies','cup',80),
('Banana','Fruits','piece',105),('Apple','Fruits','piece',95),('Orange','Fruits','piece',62),
('Milk','Dairy','cup',122),('Yogurt','Dairy','cup',150),('Cake','Sweets','slice',350),
('Cookies','Sweets','piece',70),('Soft Drink','Beverage','can',150),('Coffee with Sugar','Beverage','cup',80),
('Oatmeal','Carbs','cup',150),('Salad','Veggies','bowl',120);

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
