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

-- Identidades: solo hashes bcrypt, nunca contraseñas en claro.
CREATE TABLE IF NOT EXISTS usuarios (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    usuario VARCHAR(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL UNIQUE,
    clave_hash VARCHAR(60) NOT NULL,
    rol ENUM('admin', 'cliente') NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Pedidos y precios históricos. Aplicar solo en la etapa de integración autorizada.
CREATE TABLE IF NOT EXISTS pedidos (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT UNSIGNED NOT NULL,
    estado ENUM('pendiente') NOT NULL DEFAULT 'pendiente',
    total DECIMAL(65, 2) NOT NULL,
    KEY ix_pedidos_usuario (usuario_id),
    CONSTRAINT fk_pedidos_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS pedido_detalles (
    pedido_id INT UNSIGNED NOT NULL,
    producto_id INT UNSIGNED NOT NULL,
    cantidad INT UNSIGNED NOT NULL,
    precio_unitario DECIMAL(65, 2) NOT NULL,
    PRIMARY KEY (pedido_id, producto_id),
    CONSTRAINT fk_detalles_pedido FOREIGN KEY (pedido_id)
        REFERENCES pedidos(id) ON DELETE CASCADE,
    CONSTRAINT fk_detalles_producto FOREIGN KEY (producto_id)
        REFERENCES productos(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
