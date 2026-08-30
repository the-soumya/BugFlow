import os

# Database configurations
DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql://postgres:1601@localhost:5432/bugflow"
)

# JWT Security configurations
JWT_SECRET = os.environ.get(
    "JWT_SECRET", 
    "d2bdf7859b897931b2694f57c5eb6ef80e81e352ef29b87fcf30f81dcd3f89ee"  # Secure default key for local dev
)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRATION_MINUTES", "60"))
