BEGIN;

CREATE TABLE IF NOT EXISTS storage_condition (
	id INT AUTO_INCREMENT PRIMARY KEY,
	label VARCHAR(255)
);
	
DELETE FROM storage_condition;
INSERT INTO storage_condition (label) VALUES
	('Opened'),
	('Unopened'),
	('Cooked'),
	('Uncooked')
;

CREATE TABLE IF NOT EXISTS storage_location (
	id INT AUTO_INCREMENT PRIMARY KEY,
	label VARCHAR(255)
);
	
DELETE FROM storage_location;
INSERT INTO storage_location (label) VALUES
	('Counter'),
	('Pantry'),
	('Refrigerator'),
	('Freezer')
;

CREATE TABLE IF NOT EXISTS category (
	id INT AUTO_INCREMENT PRIMARY KEY,
	label VARCHAR(255)
);

DELETE FROM category;
INSERT INTO category (label) VALUES
	('Dairy'),
	('Protein'),
	('Fruit'),
	('Vegetable'),
	('Grain')
;

CREATE TABLE IF NOT EXISTS product (
	id INT AUTO_INCREMENT PRIMARY KEY,
	label VARCHAR(255),
	category INT,
	FOREIGN KEY (category) REFERENCES category(id)
);

CREATE TABLE IF NOT EXISTS expirations (
	product INT,
	storage_condition INT,
	storage_location INT,
	expiration INT,
	FOREIGN KEY (product) REFERENCES product(id),
	FOREIGN KEY (storage_condition) REFERENCES storage_condition(id),
	FOREIGN KEY (storage_location) REFERENCES storage_location(id)
);

CREATE TABLE IF NOT EXISTS users (
	id INT AUTO_INCREMENT PRIMARY KEY,
	username VARCHAR(255),
	pw_hash BINARY(64),
	salt BINARY(16)
);

CREATE TABLE IF NOT EXISTS items (
	user_ INT,
	description VARCHAR(255),
	product_type INT,
	quantity INT,
	date_added DATETIME,
	date_purchased DATETIME,
	projected_expiration DATETIME,
	storage_condition INT,
	storage_location INT,
	FOREIGN KEY (storage_condition) REFERENCES storage_condition(id),
	FOREIGN KEY (storage_location) REFERENCES storage_location(id)
);

COMMIT;
