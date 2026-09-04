from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class LotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lot_id: str
    material_type: str
    supplier_name: str
    received_date: date
    supplier_cert_number: str


class ShipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    shipment_id: str
    ship_date: date
    destination: str


class ComponentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    component_id: str
    component_type: str
    manufactured_date: date
    device_id: str | None


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    serial_number: str
    device_type: str
    manufacture_date: date
    dhr_status: str
    shipment_id: str | None


# ---- Backward trace: device -> components -> lots ----


class ComponentWithLots(ComponentOut):
    lots: list[LotOut]


class DeviceTraceBack(DeviceOut):
    components: list[ComponentWithLots]


# ---- Forward trace: lot -> components -> device -> shipment ----


class DeviceBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    serial_number: str
    device_type: str
    manufacture_date: date
    dhr_status: str
    shipment: ShipmentOut | None


class ComponentWithDevice(ComponentOut):
    device: DeviceBrief | None


class LotTraceForward(LotOut):
    components: list[ComponentWithDevice]


# ---- CAPA / nonconformance workflow ----


class CAPATransitionLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    log_id: int
    capa_id: int
    from_status: str
    to_status: str
    note: str
    changed_date: datetime
    changed_by: str


class CAPAOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    capa_id: int
    source_type: str
    description: str
    status: str
    opened_date: date
    closed_date: date | None
    root_cause: str | None
    corrective_action: str | None
    verification_notes: str | None
    related_lot_id: str | None
    related_serial_number: str | None


class CAPADetail(CAPAOut):
    transitions: list[CAPATransitionLogOut]


class CAPACreate(BaseModel):
    description: str
    source_type: str = "Nonconformance"
    related_lot_id: str | None = None
    related_serial_number: str | None = None


class CAPATransitionRequest(BaseModel):
    to_status: str
    note: str
    changed_by: str
    root_cause: str | None = None
    corrective_action: str | None = None
    verification_notes: str | None = None


# ---- Complaints / MDR reportability ----


class ComplaintEvaluationLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    log_id: int
    complaint_id: int
    evaluated_date: datetime
    injury_occurred: str
    injury_severity: str
    device_malfunctioned: str
    device_causality: str
    recurrence_would_be_dangerous: str
    remedial_action_taken: bool
    mdr_decision: str
    mdr_deadline_days: int | None
    mdr_due_date: date | None
    mdr_reasoning: str


class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    complaint_id: int
    serial_number: str | None
    date_received: date
    complainant: str
    description: str
    injury_occurred: str
    injury_severity: str
    device_malfunctioned: str
    device_causality: str
    recurrence_would_be_dangerous: str
    remedial_action_taken: bool
    mdr_decision: str | None
    mdr_deadline_days: int | None
    mdr_due_date: date | None
    mdr_reasoning: str | None
    mdr_evaluated_date: datetime | None
    capa_id: int | None


class ComplaintDetail(ComplaintOut):
    evaluation_logs: list[ComplaintEvaluationLogOut]


class ComplaintCreate(BaseModel):
    serial_number: str | None = None
    date_received: date
    complainant: str
    description: str
    injury_occurred: str = "Unknown"
    injury_severity: str = "Unknown"
    device_malfunctioned: str = "Unknown"
    device_causality: str = "Unknown"
    recurrence_would_be_dangerous: str = "Unknown"
    remedial_action_taken: bool = False


class ComplaintEvaluateRequest(BaseModel):
    injury_occurred: str | None = None
    injury_severity: str | None = None
    device_malfunctioned: str | None = None
    device_causality: str | None = None
    recurrence_would_be_dangerous: str | None = None
    remedial_action_taken: bool | None = None
    capa_id: int | None = None
