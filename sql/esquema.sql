-- Esquema de la tabla de productos para MySQL 8.
-- La API también crea esta tabla al iniciar, pero este archivo permite hacerlo
-- manualmente. La base de datos se debe crear antes y coincidir con DB_NAME.

CREATE TABLE IF NOT EXISTS productos (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(80) NOT NULL,
    nombre_normalizado VARCHAR(320)
        CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
    descripcion VARCHAR(200) NOT NULL,
    precio DECIMAL(65, 2) NOT NULL,
    imagen_url TEXT NOT NULL,
    disponible BOOLEAN NOT NULL,
    preparacion ENUM('frio', 'caliente', 'no_aplica') NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_productos_nombre_preparacion (nombre_normalizado, preparacion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
