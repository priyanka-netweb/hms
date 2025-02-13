class Config:
    # SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:root@localhost:5432/hms_db'
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:root@host.docker.internal:5432/hms_db' #for docker
