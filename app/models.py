from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import relationship

from .database import Base

CAPA_STATUSES = ["Open", "Investigation", "Root Cause", "Corrective Action", "Verification", "Closed"]

INJURY_OCCURRED_VALUES = ["Yes", "No", "Unknown"]
INJURY_SEVERITY_VALUES = ["None", "Minor", "Serious", "Death", "Unknown"]
DEVICE_MALFUNCTIONED_VALUES = ["Yes", "No", "Unknown"]
DEVICE_CAUSALITY_VALUES = ["Caused", "Contributed", "Unrelated", "Unknown"]
RECURRENCE_DANGEROUS_VALUES = ["Yes", "No", "Unknown"]
MDR_DECISIONS = ["Reportable", "Not Reportable", "Needs Human Review"]

component_lot = Table(
    "component_lot",
    Base.metadata,
    Column("component_id", String, ForeignKey("components.component_id"), primary_key=True),
    Column("lot_id", String, ForeignKey("raw_material_lots.lot_id"), primary_key=True),
)


class RawMaterialLot(Base):
    __tablename__ = "raw_material_lots"

    lot_id = Column(String, primary_key=True)
    material_type = Column(String, nullable=False)
    supplier_name = Column(String, nullable=False)
    received_date = Column(Date, nullable=False)
    supplier_cert_number = Column(String, nullable=False)

    components = relationship("Component", secondary=component_lot, back_populates="lots")


class Component(Base):
    __tablename__ = "components"

    component_id = Column(String, primary_key=True)
    component_type = Column(String, nullable=False)
    manufactured_date = Column(Date, nullable=False)
    device_id = Column(String, ForeignKey("devices.serial_number"), nullable=True)

    device = relationship("Device", back_populates="components")
    lots = relationship("RawMaterialLot", secondary=component_lot, back_populates="components")


class Device(Base):
    __tablename__ = "devices"

    serial_number = Column(String, primary_key=True)
    device_type = Column(String, nullable=False)
    manufacture_date = Column(Date, nullable=False)
    dhr_status = Column(String, nullable=False)
    shipment_id = Column(String, ForeignKey("shipments.shipment_id"), nullable=True)

    components = relationship("Component", back_populates="device")
    shipment = relationship("Shipment", back_populates="devices")


class Shipment(Base):
    __tablename__ = "shipments"

    shipment_id = Column(String, primary_key=True)
    ship_date = Column(Date, nullable=False)
    destination = Column(String, nullable=False)

    devices = relationship("Device", back_populates="shipment")


class CAPA(Base):
    __tablename__ = "capas"

    capa_id = Column(Integer, primary_key=True, autoincrement=True)
    source_type = Column(String, nullable=False, default="Nonconformance")
    description = Column(Text, nullable=False)
    status = Column(String, nullable=False, default=CAPA_STATUSES[0])
    opened_date = Column(Date, nullable=False)
    closed_date = Column(Date, nullable=True)
    root_cause = Column(Text, nullable=True)
    corrective_action = Column(Text, nullable=True)
    verification_notes = Column(Text, nullable=True)
    related_lot_id = Column(String, ForeignKey("raw_material_lots.lot_id"), nullable=True)
    related_serial_number = Column(String, ForeignKey("devices.serial_number"), nullable=True)

    related_lot = relationship("RawMaterialLot")
    related_device = relationship("Device")
    transitions = relationship(
        "CAPATransitionLog", back_populates="capa", order_by="CAPATransitionLog.log_id"
    )


class CAPATransitionLog(Base):
    __tablename__ = "capa_transition_logs"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    capa_id = Column(Integer, ForeignKey("capas.capa_id"), nullable=False)
    from_status = Column(String, nullable=False)
    to_status = Column(String, nullable=False)
    note = Column(Text, nullable=False)
    changed_date = Column(DateTime, nullable=False)
    changed_by = Column(String, nullable=False)

    capa = relationship("CAPA", back_populates="transitions")


class Complaint(Base):
    __tablename__ = "complaints"

    complaint_id = Column(Integer, primary_key=True, autoincrement=True)
    serial_number = Column(String, ForeignKey("devices.serial_number"), nullable=True)
    date_received = Column(Date, nullable=False)
    complainant = Column(String, nullable=False)
    description = Column(Text, nullable=False)

    # Structured decision inputs. Each allows an explicit "Unknown" — missing
    # information must be representable, never silently defaulted to "No".
    injury_occurred = Column(String, nullable=False, default="Unknown")
    injury_severity = Column(String, nullable=False, default="Unknown")
    device_malfunctioned = Column(String, nullable=False, default="Unknown")
    device_causality = Column(String, nullable=False, default="Unknown")
    recurrence_would_be_dangerous = Column(String, nullable=False, default="Unknown")
    remedial_action_taken = Column(Boolean, nullable=False, default=False)

    # Decision output — always reflects the most recent /evaluate run.
    mdr_decision = Column(String, nullable=True)
    mdr_deadline_days = Column(Integer, nullable=True)
    mdr_due_date = Column(Date, nullable=True)
    mdr_reasoning = Column(Text, nullable=True)
    mdr_evaluated_date = Column(DateTime, nullable=True)
    capa_id = Column(Integer, ForeignKey("capas.capa_id"), nullable=True)

    device = relationship("Device")
    capa = relationship("CAPA")
    evaluation_logs = relationship(
        "ComplaintEvaluationLog", back_populates="complaint", order_by="ComplaintEvaluationLog.log_id"
    )


class ComplaintEvaluationLog(Base):
    """Append-only history of every /evaluate run for a complaint: the input
    field values at that moment plus the decision they produced. Lets an
    auditor see not just the current decision but how/why it changed over
    time as new information came in."""

    __tablename__ = "complaint_evaluation_logs"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    complaint_id = Column(Integer, ForeignKey("complaints.complaint_id"), nullable=False)
    evaluated_date = Column(DateTime, nullable=False)

    injury_occurred = Column(String, nullable=False)
    injury_severity = Column(String, nullable=False)
    device_malfunctioned = Column(String, nullable=False)
    device_causality = Column(String, nullable=False)
    recurrence_would_be_dangerous = Column(String, nullable=False)
    remedial_action_taken = Column(Boolean, nullable=False)

    mdr_decision = Column(String, nullable=False)
    mdr_deadline_days = Column(Integer, nullable=True)
    mdr_due_date = Column(Date, nullable=True)
    mdr_reasoning = Column(Text, nullable=False)

    complaint = relationship("Complaint", back_populates="evaluation_logs")
