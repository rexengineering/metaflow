import sqlalchemy
from sqlalchemy import Column,Integer,String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, func
from sqlalchemy.dialects.postgresql import JSONB
from flowlib.config import POSTGRES_DB_URI

Base = declarative_base()
#State logs table:
class state_log(Base):
    __tablename__ = "state_logs"
    instance_id   = Column(String(255))                 # instance id from the kafka message
    timestamp     = Column(DateTime, primary_key=True)  # the time the message was received
    state         = Column(String(255))                 # the current state of the task
    workflow_id   = Column(String(255))                 # the id of the workflow

class request_data(Base):
    __tablename__ = "request_data"
    instance_id = Column(String(255))
    workflow_id = Column(String(255))
    data        = Column(JSONB)                         # store data sent by the envoy proxy
    timestamp   = Column(DateTime, primary_key=True)    # the time the message was received
    headers     = Column(JSONB)                         # store the headers sent by the envoy proxy

def create_tables(): # Creates request_data and state_logs if the don't exist
    engine = sqlalchemy.create_engine(POSTGRES_DB_URI)
    Base.metadata.create_all(engine)