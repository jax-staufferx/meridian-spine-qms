from datetime import date, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import models, schemas
from .database import get_db
from .mdr_engine import evaluate_mdr

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Meridian Spine QMS")


def _validate_enum(field_name: str, value: str, allowed: list[str]):
    if value not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name} '{value}'; must be one of {allowed}",
        )


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "static" / "index.html")


app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


# ---- List / detail endpoints ----


@app.get("/lots", response_model=list[schemas.LotOut])
def list_lots(db: Session = Depends(get_db)):
    return db.query(models.RawMaterialLot).order_by(models.RawMaterialLot.lot_id).all()


@app.get("/lots/{lot_id}", response_model=schemas.LotOut)
def get_lot(lot_id: str, db: Session = Depends(get_db)):
    lot = db.get(models.RawMaterialLot, lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail=f"Lot '{lot_id}' not found")
    return lot


@app.get("/components", response_model=list[schemas.ComponentOut])
def list_components(db: Session = Depends(get_db)):
    return db.query(models.Component).order_by(models.Component.component_id).all()


@app.get("/components/{component_id}", response_model=schemas.ComponentWithLots)
def get_component(component_id: str, db: Session = Depends(get_db)):
    component = db.get(models.Component, component_id)
    if not component:
        raise HTTPException(status_code=404, detail=f"Component '{component_id}' not found")
    return component


@app.get("/devices", response_model=list[schemas.DeviceOut])
def list_devices(db: Session = Depends(get_db)):
    return db.query(models.Device).order_by(models.Device.serial_number).all()


@app.get("/devices/{serial_number}", response_model=schemas.DeviceOut)
def get_device(serial_number: str, db: Session = Depends(get_db)):
    device = db.get(models.Device, serial_number)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device '{serial_number}' not found")
    return device


@app.get("/shipments", response_model=list[schemas.ShipmentOut])
def list_shipments(db: Session = Depends(get_db)):
    return db.query(models.Shipment).order_by(models.Shipment.shipment_id).all()


@app.get("/shipments/{shipment_id}", response_model=schemas.ShipmentOut)
def get_shipment(shipment_id: str, db: Session = Depends(get_db)):
    shipment = db.get(models.Shipment, shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment '{shipment_id}' not found")
    return shipment


# ---- Traceability ----


@app.get("/devices/{serial_number}/trace-back", response_model=schemas.DeviceTraceBack)
def trace_back(serial_number: str, db: Session = Depends(get_db)):
    """Given a device serial number: the device, its components, and every raw
    material lot each component draws from."""
    device = db.get(models.Device, serial_number)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device '{serial_number}' not found")
    return device


@app.get("/lots/{lot_id}/trace-forward", response_model=schemas.LotTraceForward)
def trace_forward(lot_id: str, db: Session = Depends(get_db)):
    """Given a raw material lot ID: the lot, every component made from it,
    each component's device, and that device's shipment/destination."""
    lot = db.get(models.RawMaterialLot, lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail=f"Lot '{lot_id}' not found")
    return lot


# ---- CAPA / nonconformance workflow ----


@app.post("/capas", response_model=schemas.CAPAOut, status_code=201)
def create_capa(payload: schemas.CAPACreate, db: Session = Depends(get_db)):
    if not payload.description.strip():
        raise HTTPException(status_code=400, detail="description is required")
    if payload.related_lot_id and payload.related_serial_number:
        raise HTTPException(
            status_code=400,
            detail="A CAPA may link to a lot or a device, not both",
        )
    if payload.related_lot_id and not db.get(models.RawMaterialLot, payload.related_lot_id):
        raise HTTPException(status_code=404, detail=f"Lot '{payload.related_lot_id}' not found")
    if payload.related_serial_number and not db.get(models.Device, payload.related_serial_number):
        raise HTTPException(
            status_code=404, detail=f"Device '{payload.related_serial_number}' not found"
        )

    capa = models.CAPA(
        source_type=payload.source_type.strip() or "Nonconformance",
        description=payload.description,
        status=models.CAPA_STATUSES[0],
        opened_date=date.today(),
        related_lot_id=payload.related_lot_id,
        related_serial_number=payload.related_serial_number,
    )
    db.add(capa)
    db.commit()
    db.refresh(capa)
    return capa


@app.get("/capas", response_model=list[schemas.CAPAOut])
def list_capas(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.CAPA)
    if status is not None:
        if status not in models.CAPA_STATUSES:
            raise HTTPException(status_code=400, detail=f"Unknown status '{status}'")
        query = query.filter(models.CAPA.status == status)
    return query.order_by(models.CAPA.capa_id).all()


@app.get("/capas/{capa_id}", response_model=schemas.CAPADetail)
def get_capa(capa_id: int, db: Session = Depends(get_db)):
    capa = db.get(models.CAPA, capa_id)
    if not capa:
        raise HTTPException(status_code=404, detail=f"CAPA {capa_id} not found")
    return capa


@app.post("/capas/{capa_id}/transition", response_model=schemas.CAPADetail)
def transition_capa(
    capa_id: int, payload: schemas.CAPATransitionRequest, db: Session = Depends(get_db)
):
    """Advance a CAPA exactly one step along the fixed sequence
    Open -> Investigation -> Root Cause -> Corrective Action -> Verification -> Closed.
    No skipping ahead and no reopening. Every transition requires a note, and a
    transition into Closed is rejected unless root_cause is already documented."""
    capa = db.get(models.CAPA, capa_id)
    if not capa:
        raise HTTPException(status_code=404, detail=f"CAPA {capa_id} not found")

    if not payload.note.strip():
        raise HTTPException(status_code=400, detail="note is required for every transition")
    if not payload.changed_by.strip():
        raise HTTPException(status_code=400, detail="changed_by is required for every transition")

    current_index = models.CAPA_STATUSES.index(capa.status)
    if current_index == len(models.CAPA_STATUSES) - 1:
        raise HTTPException(
            status_code=400, detail="CAPA is already Closed; no further transitions allowed"
        )

    expected_next = models.CAPA_STATUSES[current_index + 1]
    if payload.to_status != expected_next:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid transition: CAPA is '{capa.status}', must move to "
                f"'{expected_next}' next (got '{payload.to_status}')"
            ),
        )

    if payload.root_cause is not None:
        capa.root_cause = payload.root_cause
    if payload.corrective_action is not None:
        capa.corrective_action = payload.corrective_action
    if payload.verification_notes is not None:
        capa.verification_notes = payload.verification_notes

    if expected_next == "Closed" and not (capa.root_cause and capa.root_cause.strip()):
        raise HTTPException(
            status_code=400, detail="Cannot close a CAPA without a documented root cause"
        )

    db.add(
        models.CAPATransitionLog(
            capa_id=capa.capa_id,
            from_status=capa.status,
            to_status=expected_next,
            note=payload.note,
            changed_date=datetime.utcnow(),
            changed_by=payload.changed_by,
        )
    )

    capa.status = expected_next
    if expected_next == "Closed":
        capa.closed_date = date.today()

    db.commit()
    db.refresh(capa)
    return capa


# ---- Complaints / MDR reportability ----


def _run_mdr_evaluation(complaint: models.Complaint, db: Session) -> None:
    """Run the deterministic MDR engine against a complaint's current field
    values, store the result on the complaint, and append a snapshot to
    ComplaintEvaluationLog. Shared by complaint creation (auto-evaluated
    immediately) and the standalone /evaluate endpoint (re-evaluated after
    fields are updated)."""
    result = evaluate_mdr(
        injury_severity=complaint.injury_severity,
        device_causality=complaint.device_causality,
        device_malfunctioned=complaint.device_malfunctioned,
        recurrence_would_be_dangerous=complaint.recurrence_would_be_dangerous,
        remedial_action_taken=complaint.remedial_action_taken,
        date_received=complaint.date_received,
    )

    now = datetime.utcnow()
    complaint.mdr_decision = result["mdr_decision"]
    complaint.mdr_deadline_days = result["mdr_deadline_days"]
    complaint.mdr_due_date = result["mdr_due_date"]
    complaint.mdr_reasoning = result["mdr_reasoning"]
    complaint.mdr_evaluated_date = now

    db.add(
        models.ComplaintEvaluationLog(
            complaint_id=complaint.complaint_id,
            evaluated_date=now,
            injury_occurred=complaint.injury_occurred,
            injury_severity=complaint.injury_severity,
            device_malfunctioned=complaint.device_malfunctioned,
            device_causality=complaint.device_causality,
            recurrence_would_be_dangerous=complaint.recurrence_would_be_dangerous,
            remedial_action_taken=complaint.remedial_action_taken,
            mdr_decision=result["mdr_decision"],
            mdr_deadline_days=result["mdr_deadline_days"],
            mdr_due_date=result["mdr_due_date"],
            mdr_reasoning=result["mdr_reasoning"],
        )
    )


@app.post("/complaints", response_model=schemas.ComplaintOut, status_code=201)
def create_complaint(payload: schemas.ComplaintCreate, db: Session = Depends(get_db)):
    if not payload.complainant.strip():
        raise HTTPException(status_code=400, detail="complainant is required")
    if not payload.description.strip():
        raise HTTPException(status_code=400, detail="description is required")
    if payload.serial_number and not db.get(models.Device, payload.serial_number):
        raise HTTPException(status_code=404, detail=f"Device '{payload.serial_number}' not found")

    _validate_enum("injury_occurred", payload.injury_occurred, models.INJURY_OCCURRED_VALUES)
    _validate_enum("injury_severity", payload.injury_severity, models.INJURY_SEVERITY_VALUES)
    _validate_enum(
        "device_malfunctioned", payload.device_malfunctioned, models.DEVICE_MALFUNCTIONED_VALUES
    )
    _validate_enum("device_causality", payload.device_causality, models.DEVICE_CAUSALITY_VALUES)
    _validate_enum(
        "recurrence_would_be_dangerous",
        payload.recurrence_would_be_dangerous,
        models.RECURRENCE_DANGEROUS_VALUES,
    )

    complaint = models.Complaint(
        serial_number=payload.serial_number,
        date_received=payload.date_received,
        complainant=payload.complainant,
        description=payload.description,
        injury_occurred=payload.injury_occurred,
        injury_severity=payload.injury_severity,
        device_malfunctioned=payload.device_malfunctioned,
        device_causality=payload.device_causality,
        recurrence_would_be_dangerous=payload.recurrence_would_be_dangerous,
        remedial_action_taken=payload.remedial_action_taken,
    )
    db.add(complaint)
    db.flush()  # assigns complaint.complaint_id, needed by the log FK below
    _run_mdr_evaluation(complaint, db)
    db.commit()
    db.refresh(complaint)
    return complaint


@app.get("/complaints", response_model=list[schemas.ComplaintOut])
def list_complaints(mdr_decision: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Complaint)
    if mdr_decision is not None:
        if mdr_decision not in models.MDR_DECISIONS:
            raise HTTPException(status_code=400, detail=f"Unknown mdr_decision '{mdr_decision}'")
        query = query.filter(models.Complaint.mdr_decision == mdr_decision)
    return query.order_by(models.Complaint.complaint_id).all()


@app.get("/complaints/{complaint_id}", response_model=schemas.ComplaintDetail)
def get_complaint(complaint_id: int, db: Session = Depends(get_db)):
    complaint = db.get(models.Complaint, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail=f"Complaint {complaint_id} not found")
    return complaint


@app.post("/complaints/{complaint_id}/evaluate", response_model=schemas.ComplaintDetail)
def evaluate_complaint(
    complaint_id: int, payload: schemas.ComplaintEvaluateRequest, db: Session = Depends(get_db)
):
    """Optionally update the complaint's structured fields, then run the
    deterministic MDR engine and store the result. Every run is also
    appended to ComplaintEvaluationLog (input snapshot + decision), so the
    full history of how a determination evolved as new information came in
    is preserved even though the Complaint row itself only reflects the
    latest decision."""
    complaint = db.get(models.Complaint, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail=f"Complaint {complaint_id} not found")

    if payload.injury_occurred is not None:
        _validate_enum("injury_occurred", payload.injury_occurred, models.INJURY_OCCURRED_VALUES)
        complaint.injury_occurred = payload.injury_occurred
    if payload.injury_severity is not None:
        _validate_enum("injury_severity", payload.injury_severity, models.INJURY_SEVERITY_VALUES)
        complaint.injury_severity = payload.injury_severity
    if payload.device_malfunctioned is not None:
        _validate_enum(
            "device_malfunctioned", payload.device_malfunctioned, models.DEVICE_MALFUNCTIONED_VALUES
        )
        complaint.device_malfunctioned = payload.device_malfunctioned
    if payload.device_causality is not None:
        _validate_enum(
            "device_causality", payload.device_causality, models.DEVICE_CAUSALITY_VALUES
        )
        complaint.device_causality = payload.device_causality
    if payload.recurrence_would_be_dangerous is not None:
        _validate_enum(
            "recurrence_would_be_dangerous",
            payload.recurrence_would_be_dangerous,
            models.RECURRENCE_DANGEROUS_VALUES,
        )
        complaint.recurrence_would_be_dangerous = payload.recurrence_would_be_dangerous
    if payload.remedial_action_taken is not None:
        complaint.remedial_action_taken = payload.remedial_action_taken
    if payload.capa_id is not None:
        if not db.get(models.CAPA, payload.capa_id):
            raise HTTPException(status_code=404, detail=f"CAPA {payload.capa_id} not found")
        complaint.capa_id = payload.capa_id

    _run_mdr_evaluation(complaint, db)
    db.commit()
    db.refresh(complaint)
    return complaint
