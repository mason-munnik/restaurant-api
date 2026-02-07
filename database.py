from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# create name for my file where data is stored
URL_DATABASE = 'sqlite:///./reviews.db'

# "engine" is connection to that file
engine = create_engine(URL_DATABASE, connect_args={"check_same_thread": False}, echo=True)

# sessionmaker allows me to create new conversations with the database
# autocommit and autoflush turned off to make sure unwanted permanent changes don't occur
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()