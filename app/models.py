from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Person(Base):
    __tablename__ = "persons"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    age = Column(Integer)
    region = Column(String)

    cellular_events = relationship("CellularEvent", back_populates="person")
    location_events = relationship("LocationEvent", back_populates="person")
    cyber_events = relationship("CyberEvent", back_populates="person")
    feature = relationship("PersonFeature", uselist=False, back_populates="person")


class CellularEvent(Base):
    __tablename__ = "cellular_events"
    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("persons.id"))
    timestamp = Column(DateTime)
    call_duration_sec = Column(Float)
    sms_count = Column(Integer)
    contact_id = Column(Integer)
    call_type = Column(String)  # inbound / outbound

    person = relationship("Person", back_populates="cellular_events")


class LocationEvent(Base):
    __tablename__ = "location_events"
    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("persons.id"))
    timestamp = Column(DateTime)
    lat = Column(Float)
    lon = Column(Float)
    accuracy = Column(Float)

    person = relationship("Person", back_populates="location_events")


class CyberEvent(Base):
    __tablename__ = "cyber_events"
    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("persons.id"))
    timestamp = Column(DateTime)
    domain = Column(String)
    ip_address = Column(String)
    data_volume_kb = Column(Float)
    protocol = Column(String)

    person = relationship("Person", back_populates="cyber_events")


class PersonFeature(Base):
    __tablename__ = "person_features"
    person_id = Column(Integer, ForeignKey("persons.id"), primary_key=True)
    feature_vector = Column(JSON)
    last_computed = Column(DateTime)

    person = relationship("Person", back_populates="feature")
