"""Drop, recreate, and seed the Meridian Spine QMS database.

All linking data below (which lot feeds which component, which component
belongs to which device, which device shipped where) is hand-constructed,
not randomly generated, so the following patterns are guaranteed to exist
in every run:

  - 3 "hot" lots each feed 5+ devices (recall blast-radius scenarios):
      TI-2025-0101 -> 6 devices, PK-2025-0301 -> 7 devices, CO-2025-0401 -> 8 devices
  - 4 devices whose components draw from more than one lot (topped-up batches):
      PS-2001, PS-2010 (Screw Shaft), PS-2008, PS-2020 (Screw Head)
  - Materials span 4 types from 4 suppliers.
  - A handful of components exist unassembled (device_id is null) and a
    handful of devices exist unshipped (shipment_id is null), exercising
    the nullable FKs called out in the data model.

Run with: python -m app.seed
"""

from datetime import date

from .database import Base, SessionLocal, engine
from .models import CAPA, Complaint, Component, Device, RawMaterialLot, Shipment


def reset_schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Raw material lots (25) — 4 material types, 4 suppliers
# ---------------------------------------------------------------------------

TITANFORGE = "TitanForge Alloys"
ALPINE = "Alpine Metalworks"
HELIX = "Helix Polymer Solutions"
CASCADE = "Cascade CoCr Supply"

TI_ELI = "Titanium Ti-6Al-4V ELI"
TI_G5 = "Titanium Grade 5"
PEEK = "PEEK Polymer"
COCR = "Cobalt-Chromium Alloy"

LOTS = [
    # lot_id, material_type, supplier, received_date, cert_number
    ("TI-2025-0101", TI_ELI, TITANFORGE, date(2025, 1, 6), "CERT-TF-1101"),
    ("TI-2025-0102", TI_ELI, TITANFORGE, date(2025, 1, 13), "CERT-TF-1102"),
    ("TI-2025-0103", TI_ELI, TITANFORGE, date(2025, 1, 20), "CERT-TF-1103"),
    ("TI-2025-0104", TI_ELI, TITANFORGE, date(2025, 1, 27), "CERT-TF-1104"),
    ("TI-2025-0105", TI_ELI, TITANFORGE, date(2025, 2, 3), "CERT-TF-1105"),
    ("TI-2025-0106", TI_ELI, TITANFORGE, date(2025, 2, 10), "CERT-TF-1106"),
    ("TI-2025-0107", TI_ELI, TITANFORGE, date(2025, 2, 17), "CERT-TF-1107"),
    ("TI-2025-0108", TI_ELI, TITANFORGE, date(2025, 2, 24), "CERT-TF-1108"),
    ("TI-2025-0201", TI_G5, ALPINE, date(2025, 2, 3), "CERT-AM-2201"),
    ("TI-2025-0202", TI_G5, ALPINE, date(2025, 2, 10), "CERT-AM-2202"),
    ("TI-2025-0203", TI_G5, ALPINE, date(2025, 2, 17), "CERT-AM-2203"),
    ("TI-2025-0204", TI_G5, ALPINE, date(2025, 2, 24), "CERT-AM-2204"),
    ("TI-2025-0205", TI_G5, ALPINE, date(2025, 3, 3), "CERT-AM-2205"),
    ("TI-2025-0206", TI_G5, ALPINE, date(2025, 3, 10), "CERT-AM-2206"),
    ("PK-2025-0301", PEEK, HELIX, date(2025, 1, 13), "CERT-HX-3301"),
    ("PK-2025-0302", PEEK, HELIX, date(2025, 1, 20), "CERT-HX-3302"),
    ("PK-2025-0303", PEEK, HELIX, date(2025, 1, 27), "CERT-HX-3303"),
    ("PK-2025-0304", PEEK, HELIX, date(2025, 2, 3), "CERT-HX-3304"),
    ("PK-2025-0305", PEEK, HELIX, date(2025, 2, 10), "CERT-HX-3305"),
    ("PK-2025-0306", PEEK, HELIX, date(2025, 2, 17), "CERT-HX-3306"),
    ("PK-2025-0307", PEEK, HELIX, date(2025, 2, 24), "CERT-HX-3307"),
    ("CO-2025-0401", COCR, CASCADE, date(2025, 2, 10), "CERT-CC-4401"),
    ("CO-2025-0402", COCR, CASCADE, date(2025, 2, 17), "CERT-CC-4402"),
    ("CO-2025-0403", COCR, CASCADE, date(2025, 2, 24), "CERT-CC-4403"),
    ("CO-2025-0404", COCR, CASCADE, date(2025, 3, 3), "CERT-CC-4404"),
]


# ---------------------------------------------------------------------------
# Shipments (12)
# ---------------------------------------------------------------------------

SHIPMENTS = [
    ("SH-4001", date(2025, 6, 2), "St. Aurelia Regional Medical Center"),
    ("SH-4002", date(2025, 6, 9), "Blackwood Orthopedic Institute"),
    ("SH-4003", date(2025, 6, 16), "Cascade Ridge Distributors"),
    ("SH-4004", date(2025, 6, 23), "Union Grove Health System"),
    ("SH-4005", date(2025, 6, 30), "Fairhaven Spine & Neuro Center"),
    ("SH-4006", date(2025, 7, 7), "Pinegate Medical Distributors"),
    ("SH-4007", date(2025, 7, 14), "Northbridge Surgical Center"),
    ("SH-4008", date(2025, 7, 21), "Sable Creek Regional Hospital"),
    ("SH-4009", date(2025, 7, 28), "Ashford Neuro Institute"),
    ("SH-4010", date(2025, 8, 4), "Blue Harbor Distributors"),
    ("SH-4011", date(2025, 8, 11), "Ridgeview Community Hospital"),
    ("SH-4012", date(2025, 8, 18), "Thornfield Spine Center"),
]


# ---------------------------------------------------------------------------
# Devices (32) — 20 Pedicle Screws, 12 Interbody Cages
# device_id -> (device_type, manufacture_date, dhr_status, shipment_id)
# ---------------------------------------------------------------------------

PEDICLE_SCREW = "Pedicle Screw"
INTERBODY_CAGE = "Interbody Cage"

DEVICES = {
    "PS-2001": (PEDICLE_SCREW, date(2025, 4, 1), "Complete", "SH-4001"),
    "PS-2002": (PEDICLE_SCREW, date(2025, 4, 1), "Complete", "SH-4001"),
    "PS-2003": (PEDICLE_SCREW, date(2025, 4, 2), "Complete", "SH-4002"),
    "PS-2004": (PEDICLE_SCREW, date(2025, 4, 2), "Complete", "SH-4002"),
    "PS-2005": (PEDICLE_SCREW, date(2025, 4, 3), "Complete", "SH-4003"),
    "PS-2006": (PEDICLE_SCREW, date(2025, 4, 3), "Complete", "SH-4004"),
    "PS-2007": (PEDICLE_SCREW, date(2025, 4, 4), "Complete", "SH-4004"),
    "PS-2008": (PEDICLE_SCREW, date(2025, 4, 4), "Complete", "SH-4005"),
    "PS-2009": (PEDICLE_SCREW, date(2025, 4, 7), "Complete", "SH-4006"),
    "PS-2010": (PEDICLE_SCREW, date(2025, 4, 7), "Complete", "SH-4006"),
    "PS-2011": (PEDICLE_SCREW, date(2025, 4, 8), "Complete", "SH-4007"),
    "PS-2012": (PEDICLE_SCREW, date(2025, 4, 8), "Complete", "SH-4008"),
    "PS-2013": (PEDICLE_SCREW, date(2025, 4, 9), "Complete", "SH-4008"),
    "PS-2014": (PEDICLE_SCREW, date(2025, 4, 9), "Complete", "SH-4009"),
    "PS-2015": (PEDICLE_SCREW, date(2025, 4, 10), "Complete", "SH-4010"),
    "PS-2016": (PEDICLE_SCREW, date(2025, 4, 10), "Complete", "SH-4010"),
    "PS-2017": (PEDICLE_SCREW, date(2025, 4, 11), "Complete", "SH-4011"),
    "PS-2018": (PEDICLE_SCREW, date(2025, 4, 14), "Incomplete", None),
    "PS-2019": (PEDICLE_SCREW, date(2025, 4, 14), "Incomplete", None),
    "PS-2020": (PEDICLE_SCREW, date(2025, 4, 15), "Complete", None),
    "IC-3001": (INTERBODY_CAGE, date(2025, 4, 21), "Complete", "SH-4003"),
    "IC-3002": (INTERBODY_CAGE, date(2025, 4, 21), "Complete", "SH-4005"),
    "IC-3003": (INTERBODY_CAGE, date(2025, 4, 22), "Complete", "SH-4007"),
    "IC-3004": (INTERBODY_CAGE, date(2025, 4, 22), "Complete", "SH-4009"),
    "IC-3005": (INTERBODY_CAGE, date(2025, 4, 23), "Complete", "SH-4009"),
    "IC-3006": (INTERBODY_CAGE, date(2025, 4, 23), "Complete", "SH-4011"),
    "IC-3007": (INTERBODY_CAGE, date(2025, 4, 24), "Complete", "SH-4011"),
    "IC-3008": (INTERBODY_CAGE, date(2025, 4, 24), "Complete", "SH-4012"),
    "IC-3009": (INTERBODY_CAGE, date(2025, 4, 25), "Complete", "SH-4012"),
    "IC-3010": (INTERBODY_CAGE, date(2025, 4, 28), "Incomplete", None),
    "IC-3011": (INTERBODY_CAGE, date(2025, 4, 28), "Incomplete", None),
    "IC-3012": (INTERBODY_CAGE, date(2025, 4, 29), "Complete", None),
}


# ---------------------------------------------------------------------------
# Components (60) — component_id -> (component_type, manufactured_date,
# device_id or None, [lot_ids])
#
# Pedicle screws each get a Screw Shaft + Screw Head. Interbody cages each
# get a Cage Body; the first 4 also get a Cage Endplate. 4 components draw
# from two lots (a topped-up alloy batch) instead of one. 4 components are
# left unassembled (device_id None).
# ---------------------------------------------------------------------------

COMPONENTS = {
    # Screw Shafts (component_type="Screw Shaft")
    "CMP-SHF-2001": ("Screw Shaft", date(2025, 3, 3), "PS-2001", ["TI-2025-0101", "TI-2025-0102"]),
    "CMP-SHF-2002": ("Screw Shaft", date(2025, 3, 3), "PS-2002", ["TI-2025-0101"]),
    "CMP-SHF-2003": ("Screw Shaft", date(2025, 3, 4), "PS-2003", ["TI-2025-0101"]),
    "CMP-SHF-2004": ("Screw Shaft", date(2025, 3, 4), "PS-2004", ["TI-2025-0101"]),
    "CMP-SHF-2005": ("Screw Shaft", date(2025, 3, 5), "PS-2005", ["TI-2025-0101"]),
    "CMP-SHF-2006": ("Screw Shaft", date(2025, 3, 5), "PS-2006", ["TI-2025-0101"]),
    "CMP-SHF-2007": ("Screw Shaft", date(2025, 3, 6), "PS-2007", ["TI-2025-0103"]),
    "CMP-SHF-2008": ("Screw Shaft", date(2025, 3, 6), "PS-2008", ["TI-2025-0103"]),
    "CMP-SHF-2009": ("Screw Shaft", date(2025, 3, 7), "PS-2009", ["TI-2025-0104"]),
    "CMP-SHF-2010": ("Screw Shaft", date(2025, 3, 7), "PS-2010", ["TI-2025-0201", "TI-2025-0202"]),
    "CMP-SHF-2011": ("Screw Shaft", date(2025, 3, 10), "PS-2011", ["TI-2025-0201"]),
    "CMP-SHF-2012": ("Screw Shaft", date(2025, 3, 10), "PS-2012", ["TI-2025-0202"]),
    "CMP-SHF-2013": ("Screw Shaft", date(2025, 3, 11), "PS-2013", ["TI-2025-0203"]),
    "CMP-SHF-2014": ("Screw Shaft", date(2025, 3, 11), "PS-2014", ["TI-2025-0204"]),
    "CMP-SHF-2015": ("Screw Shaft", date(2025, 3, 12), "PS-2015", ["TI-2025-0105"]),
    "CMP-SHF-2016": ("Screw Shaft", date(2025, 3, 12), "PS-2016", ["TI-2025-0106"]),
    "CMP-SHF-2017": ("Screw Shaft", date(2025, 3, 13), "PS-2017", ["TI-2025-0107"]),
    "CMP-SHF-2018": ("Screw Shaft", date(2025, 3, 13), "PS-2018", ["TI-2025-0108"]),
    "CMP-SHF-2019": ("Screw Shaft", date(2025, 3, 14), "PS-2019", ["TI-2025-0205"]),
    "CMP-SHF-2020": ("Screw Shaft", date(2025, 3, 14), "PS-2020", ["TI-2025-0206"]),
    # Screw Heads (component_type="Screw Head")
    "CMP-HD-2001": ("Screw Head", date(2025, 3, 17), "PS-2001", ["CO-2025-0401"]),
    "CMP-HD-2002": ("Screw Head", date(2025, 3, 17), "PS-2002", ["CO-2025-0401"]),
    "CMP-HD-2003": ("Screw Head", date(2025, 3, 18), "PS-2003", ["CO-2025-0401"]),
    "CMP-HD-2004": ("Screw Head", date(2025, 3, 18), "PS-2004", ["CO-2025-0401"]),
    "CMP-HD-2005": ("Screw Head", date(2025, 3, 19), "PS-2005", ["CO-2025-0401"]),
    "CMP-HD-2006": ("Screw Head", date(2025, 3, 19), "PS-2006", ["CO-2025-0402"]),
    "CMP-HD-2007": ("Screw Head", date(2025, 3, 20), "PS-2007", ["CO-2025-0402"]),
    "CMP-HD-2008": ("Screw Head", date(2025, 3, 20), "PS-2008", ["CO-2025-0402", "CO-2025-0403"]),
    "CMP-HD-2009": ("Screw Head", date(2025, 3, 21), "PS-2009", ["CO-2025-0403"]),
    "CMP-HD-2010": ("Screw Head", date(2025, 3, 21), "PS-2010", ["CO-2025-0403"]),
    "CMP-HD-2011": ("Screw Head", date(2025, 3, 24), "PS-2011", ["CO-2025-0404"]),
    "CMP-HD-2012": ("Screw Head", date(2025, 3, 24), "PS-2012", ["CO-2025-0404"]),
    "CMP-HD-2013": ("Screw Head", date(2025, 3, 25), "PS-2013", ["CO-2025-0401"]),
    "CMP-HD-2014": ("Screw Head", date(2025, 3, 25), "PS-2014", ["CO-2025-0402"]),
    "CMP-HD-2015": ("Screw Head", date(2025, 3, 26), "PS-2015", ["CO-2025-0403"]),
    "CMP-HD-2016": ("Screw Head", date(2025, 3, 26), "PS-2016", ["CO-2025-0404"]),
    "CMP-HD-2017": ("Screw Head", date(2025, 3, 27), "PS-2017", ["CO-2025-0401"]),
    "CMP-HD-2018": ("Screw Head", date(2025, 3, 27), "PS-2018", ["CO-2025-0402"]),
    "CMP-HD-2019": ("Screw Head", date(2025, 3, 28), "PS-2019", ["CO-2025-0403"]),
    "CMP-HD-2020": ("Screw Head", date(2025, 3, 28), "PS-2020", ["CO-2025-0404", "CO-2025-0401"]),
    # Cage Bodies (component_type="Cage Body")
    "CMP-BDY-3001": ("Cage Body", date(2025, 4, 7), "IC-3001", ["PK-2025-0301"]),
    "CMP-BDY-3002": ("Cage Body", date(2025, 4, 7), "IC-3002", ["PK-2025-0301"]),
    "CMP-BDY-3003": ("Cage Body", date(2025, 4, 8), "IC-3003", ["PK-2025-0301"]),
    "CMP-BDY-3004": ("Cage Body", date(2025, 4, 8), "IC-3004", ["PK-2025-0301"]),
    "CMP-BDY-3005": ("Cage Body", date(2025, 4, 9), "IC-3005", ["PK-2025-0301"]),
    "CMP-BDY-3006": ("Cage Body", date(2025, 4, 9), "IC-3006", ["PK-2025-0301"]),
    "CMP-BDY-3007": ("Cage Body", date(2025, 4, 10), "IC-3007", ["PK-2025-0301"]),
    "CMP-BDY-3008": ("Cage Body", date(2025, 4, 10), "IC-3008", ["PK-2025-0302"]),
    "CMP-BDY-3009": ("Cage Body", date(2025, 4, 11), "IC-3009", ["PK-2025-0303"]),
    "CMP-BDY-3010": ("Cage Body", date(2025, 4, 11), "IC-3010", ["PK-2025-0304"]),
    "CMP-BDY-3011": ("Cage Body", date(2025, 4, 14), "IC-3011", ["PK-2025-0305"]),
    "CMP-BDY-3012": ("Cage Body", date(2025, 4, 14), "IC-3012", ["PK-2025-0306"]),
    # Cage Endplates (component_type="Cage Endplate") — only IC-3001..3004
    "CMP-EP-3001": ("Cage Endplate", date(2025, 4, 15), "IC-3001", ["TI-2025-0203"]),
    "CMP-EP-3002": ("Cage Endplate", date(2025, 4, 15), "IC-3002", ["TI-2025-0204"]),
    "CMP-EP-3003": ("Cage Endplate", date(2025, 4, 16), "IC-3003", ["TI-2025-0205"]),
    "CMP-EP-3004": ("Cage Endplate", date(2025, 4, 16), "IC-3004", ["TI-2025-0206"]),
    # Unassembled components — manufactured, not yet built into a device
    "CMP-SHF-9001": ("Screw Shaft", date(2025, 5, 5), None, ["TI-2025-0102"]),
    "CMP-BDY-9002": ("Cage Body", date(2025, 5, 5), None, ["PK-2025-0307"]),
    "CMP-HD-9003": ("Screw Head", date(2025, 5, 6), None, ["CO-2025-0403"]),
    "CMP-EP-9004": ("Cage Endplate", date(2025, 5, 6), None, ["TI-2025-0201"]),
}


# ---------------------------------------------------------------------------
# CAPA / nonconformance seed scenarios (6) — all left in Open status only.
# Driving these through Investigation -> Closed is done via the API/UI, not
# scripted here. related_lot_id/related_serial_number reference real IDs
# from the traceability data above.
# ---------------------------------------------------------------------------

CAPA_SEEDS = [
    dict(
        source_type="Nonconformance",
        description=(
            "Incoming inspection found hardness readings below the supplier's "
            "certified range on titanium lot TI-2025-0101. This lot has already "
            "been built into multiple pedicle screws — forward trace needed to "
            "scope the full blast radius before disposition."
        ),
        opened_date=date(2025, 8, 20),
        related_lot_id="TI-2025-0101",
        related_serial_number=None,
    ),
    dict(
        source_type="Nonconformance",
        description=(
            "Final inspection sampling found the hex drive recess on a batch of "
            "pedicle screw heads machined outside tolerance, risking driver slip "
            "during surgical insertion."
        ),
        opened_date=date(2025, 8, 21),
        related_lot_id=None,
        related_serial_number="PS-2014",
    ),
    dict(
        source_type="Nonconformance",
        description=(
            "Hospital reported a pedicle screw's drive recess stripped during "
            "insertion; a backup screw was used and no patient injury occurred."
        ),
        opened_date=date(2025, 8, 25),
        related_lot_id=None,
        related_serial_number="PS-2003",
    ),
    dict(
        source_type="Nonconformance",
        description=(
            "In-process visual inspection flagged discoloration on a batch of "
            "interbody cage coatings, inconsistent with the approved process "
            "spec. Root cause not yet known — coating equipment and material "
            "variability are both plausible."
        ),
        opened_date=date(2025, 8, 26),
        related_lot_id=None,
        related_serial_number=None,
    ),
    dict(
        source_type="Nonconformance",
        description=(
            "Internal quality audit found two production operators performing "
            "final inspection lacked documented training records for the "
            "current revision of the inspection work instruction."
        ),
        opened_date=date(2025, 8, 27),
        related_lot_id=None,
        related_serial_number=None,
    ),
    dict(
        source_type="Nonconformance",
        description=(
            "Routine sterilization validation batch found 3 of 50 sampled "
            "device packages failed peel-seal strength testing, raising a "
            "sterility assurance risk."
        ),
        opened_date=date(2025, 8, 28),
        related_lot_id=None,
        related_serial_number=None,
    ),
]


# ---------------------------------------------------------------------------
# Complaint / MDR seed scenarios (10) — seeded unevaluated (decision fields
# null); running each through POST /complaints/{id}/evaluate is the
# exercise, not something this script does for you. serial_number values
# reference real devices from the traceability seed data above.
#
# Spread:
#   1-2  clear Reportable via death/serious injury
#   3-4  clear Reportable via dangerous malfunction, no injury
#   5-6  clear Not Reportable
#   7-10 genuinely ambiguous, each blocked for a different reason
# ---------------------------------------------------------------------------

COMPLAINT_SEEDS = [
    # 1. Clear Reportable — serious injury, screw fracture requiring revision
    dict(
        serial_number="PS-2005",
        date_received=date(2025, 9, 3),
        complainant="Cascade Ridge Distributors — reporting surgeon Dr. T. Nwosu",
        description=(
            "Patient returned at 4 months post-op with new-onset low back pain. "
            "Imaging showed the pedicle screw shaft had fractured in situ. "
            "Patient underwent revision surgery to remove and replace the "
            "broken hardware. Surgeon reports no other intraoperative "
            "complications during revision."
        ),
        injury_occurred="Yes",
        injury_severity="Serious",
        device_malfunctioned="Yes",
        device_causality="Caused",
        recurrence_would_be_dangerous="Yes",
        remedial_action_taken=True,
    ),
    # 2. Clear Reportable — serious injury, cage migration with nerve damage
    dict(
        serial_number="IC-3003",
        date_received=date(2025, 9, 5),
        complainant="Northbridge Surgical Center — reporting surgeon Dr. A. Faison",
        description=(
            "Interbody cage was found to have migrated posteriorly on 6-week "
            "follow-up imaging, encroaching on the neural foramen. Patient "
            "presented with new radicular pain and numbness. Neurology "
            "consult confirmed a new, persistent sensory deficit in the "
            "affected nerve distribution, assessed as permanent. Revision "
            "surgery performed to reposition/replace the cage."
        ),
        injury_occurred="Yes",
        injury_severity="Serious",
        device_malfunctioned="Yes",
        device_causality="Caused",
        recurrence_would_be_dangerous="Yes",
        remedial_action_taken=False,
    ),
    # 3. Clear Reportable — dangerous malfunction, no injury (caught intraop)
    dict(
        serial_number="PS-2007",
        date_received=date(2025, 9, 8),
        complainant="Union Grove Health System — reporting surgeon Dr. L. Bianchi",
        description=(
            "During screw insertion, the screw head sheared off the shaft "
            "before final seating. Surgeon recognized the failure "
            "intraoperatively, removed the fragment, and substituted a new "
            "screw from a different lot with no further incident. No harm "
            "to the patient. Sheared component retained for engineering "
            "evaluation."
        ),
        injury_occurred="No",
        injury_severity="None",
        device_malfunctioned="Yes",
        device_causality="Unrelated",
        recurrence_would_be_dangerous="Yes",
        remedial_action_taken=False,
    ),
    # 4. Clear Reportable — dangerous malfunction, no injury (trial component)
    dict(
        serial_number="IC-3008",
        date_received=date(2025, 9, 9),
        complainant="Thornfield Spine Center — reporting surgeon Dr. R. Okonkwo",
        description=(
            "Cage endplate separated from the body during trial insertion, "
            "prior to final implantation. Fragment was retrieved in full "
            "before permanent placement; no tissue contact-related injury "
            "occurred. Surgical team proceeded with a replacement unit. "
            "Concern raised that an undetected separation after final "
            "placement could migrate."
        ),
        injury_occurred="No",
        injury_severity="None",
        device_malfunctioned="Yes",
        device_causality="Unrelated",
        recurrence_would_be_dangerous="Yes",
        remedial_action_taken=True,
    ),
    # 5. Clear Not Reportable — cosmetic packaging damage only
    dict(
        serial_number="PS-2019",
        date_received=date(2025, 9, 2),
        complainant="Meridian Spine incoming QA (found at receiving, not yet shipped)",
        description=(
            "Sterile packaging for an in-inventory pedicle screw was found "
            "with a torn outer pouch during routine stock rotation. Inner "
            "sterile barrier was intact and the device itself shows no "
            "visible damage or corrosion. Unit was quarantined and will not "
            "be shipped; packaging vendor notified."
        ),
        injury_occurred="No",
        injury_severity="None",
        device_malfunctioned="No",
        device_causality="Unrelated",
        recurrence_would_be_dangerous="No",
        remedial_action_taken=False,
    ),
    # 6. Clear Not Reportable — instrument ergonomics, no device malfunction
    dict(
        serial_number=None,
        date_received=date(2025, 9, 4),
        complainant="Dr. S. Vance, independent surgeon feedback call",
        description=(
            "Surgeon called to say the driver handle for the pedicle screw "
            "insertion instrument set feels awkward in a gloved hand during "
            "longer cases and would prefer a wider grip. No implant "
            "malfunction, no patient event — feedback is about the "
            "reusable instrument tray, not a specific implanted device."
        ),
        injury_occurred="No",
        injury_severity="None",
        device_malfunctioned="No",
        device_causality="Unrelated",
        recurrence_would_be_dangerous="No",
        remedial_action_taken=False,
    ),
    # 7. Ambiguous — injury occurred, causality unknown (complicating factors)
    dict(
        serial_number="PS-2011",
        date_received=date(2025, 9, 10),
        complainant="Northbridge Surgical Center — case management callback",
        description=(
            "Case manager called about a patient readmitted 5 weeks post-op "
            "with a new neurological deficit. Patient has poorly-controlled "
            "diabetes and developed a surgical site infection during the "
            "same admission; workup is still in progress. Treating team "
            "hasn't yet determined whether the deficit relates to hardware "
            "placement, the infection, or the patient's underlying "
            "condition. No confirmed device malfunction on the imaging "
            "reviewed so far."
        ),
        injury_occurred="Yes",
        injury_severity="Serious",
        device_malfunctioned="No",
        device_causality="Unknown",
        recurrence_would_be_dangerous="Unknown",
        remedial_action_taken=False,
    ),
    # 8. Ambiguous — malfunction confirmed, recurrence risk not yet assessed
    dict(
        serial_number="IC-3005",
        date_received=date(2025, 9, 11),
        complainant="Ashford Neuro Institute — reporting surgeon Dr. P. Renaud",
        description=(
            "Routine 3-month imaging showed measurable subsidence of the "
            "interbody cage into the adjacent vertebral body, beyond what "
            "the surgeon considers typical for this stage of fusion. "
            "Patient is asymptomatic at this time. Surgeon has flagged it "
            "as a device performance concern; engineering has not yet "
            "reviewed whether this subsidence pattern indicates a design or "
            "manufacturing issue that could recur across the lot, or an "
            "isolated bone-quality factor for this patient."
        ),
        injury_occurred="No",
        injury_severity="None",
        device_malfunctioned="Yes",
        device_causality="Unrelated",
        recurrence_would_be_dangerous="Unknown",
        remedial_action_taken=False,
    ),
    # 9. Ambiguous — device involvement confirmed, severity classification unclear
    dict(
        serial_number="PS-2016",
        date_received=date(2025, 9, 12),
        complainant="Blue Harbor Distributors — reporting surgeon Dr. M. Okafor",
        description=(
            "Follow-up imaging at 8 weeks showed the screw had backed out "
            "slightly from its original position. Surgeon elected an "
            "in-office needle-guided adjustment procedure under local "
            "anesthesia rather than a return to the OR, and patient "
            "recovered without further issue. Unclear whether this "
            "level of intervention meets the 'necessitates medical or "
            "surgical intervention to preclude permanent impairment' bar "
            "for a serious injury, or whether it's more properly a minor, "
            "non-reportable outcome — flagging for a documented severity "
            "determination either way."
        ),
        injury_occurred="Yes",
        injury_severity="Unknown",
        device_malfunctioned="Yes",
        device_causality="Contributed",
        recurrence_would_be_dangerous="No",
        remedial_action_taken=False,
    ),
    # 10. Ambiguous — vague secondhand report, unit unidentified
    dict(
        serial_number=None,
        date_received=date(2025, 9, 13),
        complainant="Hospital risk management (relayed secondhand, not the treating surgeon)",
        description=(
            "Voicemail from a hospital risk manager stating that 'one of "
            "the spine cases from a couple months back had some kind of "
            "problem' and that the patient 'may have needed something "
            "else done.' Risk manager did not have the patient name, "
            "surgery date, or device serial number on hand and said "
            "someone would call back with details. No callback received "
            "yet as of logging this complaint. Cannot currently identify "
            "which implanted unit, if any, is involved."
        ),
        injury_occurred="Unknown",
        injury_severity="Unknown",
        device_malfunctioned="Unknown",
        device_causality="Unknown",
        recurrence_would_be_dangerous="Unknown",
        remedial_action_taken=False,
    ),
]


def seed():
    reset_schema()
    db = SessionLocal()
    try:
        for shipment_id, ship_date, destination in SHIPMENTS:
            db.add(Shipment(shipment_id=shipment_id, ship_date=ship_date, destination=destination))
        db.flush()

        for serial_number, (device_type, manufacture_date, dhr_status, shipment_id) in DEVICES.items():
            db.add(
                Device(
                    serial_number=serial_number,
                    device_type=device_type,
                    manufacture_date=manufacture_date,
                    dhr_status=dhr_status,
                    shipment_id=shipment_id,
                )
            )
        db.flush()

        lots_by_id = {}
        for lot_id, material_type, supplier_name, received_date, cert_number in LOTS:
            lot = RawMaterialLot(
                lot_id=lot_id,
                material_type=material_type,
                supplier_name=supplier_name,
                received_date=received_date,
                supplier_cert_number=cert_number,
            )
            db.add(lot)
            lots_by_id[lot_id] = lot
        db.flush()

        for component_id, (component_type, manufactured_date, device_id, lot_ids) in COMPONENTS.items():
            component = Component(
                component_id=component_id,
                component_type=component_type,
                manufactured_date=manufactured_date,
                device_id=device_id,
            )
            component.lots = [lots_by_id[lot_id] for lot_id in lot_ids]
            db.add(component)
        db.flush()

        for capa_kwargs in CAPA_SEEDS:
            db.add(CAPA(status="Open", **capa_kwargs))
        db.flush()

        for complaint_kwargs in COMPLAINT_SEEDS:
            db.add(Complaint(**complaint_kwargs))

        db.commit()

        print(
            f"Seeded {len(LOTS)} lots, {len(COMPONENTS)} components, "
            f"{len(DEVICES)} devices, {len(SHIPMENTS)} shipments, "
            f"{len(CAPA_SEEDS)} CAPAs, {len(COMPLAINT_SEEDS)} complaints."
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()
