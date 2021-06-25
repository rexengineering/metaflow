import sqlalchemy
from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from flowlib.config import POSTGRES_DB_URI

Base = declarative_base()
# State logs table


class StateLog(Base):

    __tablename__ = "state_log"
    # instance id from the kafka message
    instance_id = Column(String(255))
    # the time the message was received
    timestamp = Column(DateTime, primary_key=True)
    # the current state of the task
    state = Column(String(255))
    # the id of the workflow
    workflow_id = Column(String(255))


class RequestData(Base):
    __tablename__ = "request_data"
    instance_id = Column(String(255))
    workflow_id = Column(String(255))
    # store data sent by the envoy proxy
    data = Column(JSONB)
    # the time the message was received
    timestamp = Column(DateTime, primary_key=True)
    # store the headers sent by the envoy proxy
    headers = Column(JSONB)


# Creates RequestData and StateLogif the don't exist
def create_tables():
    engine = sqlalchemy.create_engine(POSTGRES_DB_URI)
    Base.metadata.create_all(engine)
