"""
Deterministic chip / automotive supply-chain knowledge graph.

~50 nodes, ~100 edges.  No LLM needed — just Python dicts.
The flagship path that proves Graph RAG's value:

  RiskEvent "Chip Shortage at Factory A"
    -AFFECTS-> Factory "Factory A" (TSMC Fab 18, Tainan)
      -PRODUCES-> Component "NX-7 Microcontroller"
        -USED_IN-> Product "DriveECU-500"
          -SOLD_TO-> Customer "Acme Corp"
"""

from __future__ import annotations

# ── Regions ──────────────────────────────────────────────────────────────
REGIONS: list[dict] = [
    {"name": "East Asia",        "description": "Major semiconductor manufacturing hub covering Taiwan, South Korea, Japan, and China."},
    {"name": "Southeast Asia",   "description": "Assembly and test hub including Malaysia, Vietnam, and the Philippines."},
    {"name": "Europe",           "description": "Automotive OEM and specialty chip region covering Germany, Netherlands, and France."},
    {"name": "North America",    "description": "End-market demand centre and advanced R&D region covering the US and Canada."},
    {"name": "South Asia",       "description": "Emerging electronics manufacturing region covering India."},
    {"name": "Middle East",      "description": "Growing technology investment hub."},
    {"name": "South America",    "description": "Commodity mining and emerging EV market."},
    {"name": "Africa",           "description": "Rare-earth mineral sourcing region."},
]

# ── Factories ────────────────────────────────────────────────────────────
FACTORIES: list[dict] = [
    {"name": "Factory A",  "company": "TSMC",            "site": "Fab 18, Tainan",       "region": "East Asia",      "description": "TSMC advanced 7nm/5nm fab producing automotive and AI chips at its Tainan facility."},
    {"name": "Factory B",  "company": "Samsung",         "site": "Pyeongtaek P2",        "region": "East Asia",      "description": "Samsung foundry producing memory and logic chips for consumer and automotive use."},
    {"name": "Factory C",  "company": "Infineon",        "site": "Dresden Fab",           "region": "Europe",         "description": "Infineon power-semiconductor fab specialising in automotive-grade IGBTs and MOSFETs."},
    {"name": "Factory D",  "company": "GlobalFoundries", "site": "Malta, New York",       "region": "North America",  "description": "GlobalFoundries 12nm/14nm fab serving aerospace, defence, and automotive sectors."},
    {"name": "Factory E",  "company": "ASE Group",       "site": "Kaohsiung OSAT",        "region": "East Asia",      "description": "ASE advanced packaging and test facility for assembled semiconductor modules."},
    {"name": "Factory F",  "company": "Renesas",         "site": "Naka Fab",              "region": "East Asia",      "description": "Renesas automotive-MCU fab producing R-Car and RH850 families."},
]

# ── Suppliers ────────────────────────────────────────────────────────────
SUPPLIERS: list[dict] = [
    {"name": "Supplier Alpha",   "specialty": "Raw silicon wafers",           "region": "East Asia",      "description": "Leading silicon-wafer supplier providing 300mm wafers to major fabs in East Asia."},
    {"name": "Supplier Beta",    "specialty": "Rare-earth metals",            "region": "Africa",         "description": "Rare-earth mining company supplying neodymium and lanthanum for chip substrates."},
    {"name": "Supplier Gamma",   "specialty": "Ceramic substrates",           "region": "Southeast Asia", "description": "Ceramic substrate manufacturer for BGA and flip-chip packages."},
    {"name": "Supplier Delta",   "specialty": "Photoresist chemicals",        "region": "East Asia",      "description": "Specialty chemical supplier providing EUV photoresist to advanced fabs."},
    {"name": "Supplier Epsilon", "specialty": "PCB fabrication",              "region": "Southeast Asia", "description": "High-density interconnect PCB manufacturer for automotive modules."},
    {"name": "Supplier Zeta",    "specialty": "Passive components",           "region": "East Asia",      "description": "Passive-component maker supplying MLCCs, resistors, and inductors globally."},
    {"name": "Supplier Eta",     "specialty": "Assembly & packaging",         "region": "South Asia",     "description": "OSAT provider offering wire-bonding and flip-chip packaging in India."},
    {"name": "Supplier Theta",   "specialty": "Testing equipment",            "region": "North America",  "description": "Automated test equipment (ATE) supplier for wafer and final test."},
]

# ── Components ───────────────────────────────────────────────────────────
COMPONENTS: list[dict] = [
    {"name": "NX-7 Microcontroller",   "category": "MCU",         "description": "32-bit automotive-grade microcontroller used in powertrain and ADAS ECUs."},
    {"name": "VPower-300 IGBT",        "category": "Power",       "description": "600V automotive IGBT module for EV inverter drives."},
    {"name": "MemX-DDR5 Module",       "category": "Memory",      "description": "DDR5 DRAM module for high-bandwidth in-vehicle computing."},
    {"name": "SensorIQ LiDAR ASIC",    "category": "Sensor",      "description": "Custom ASIC for solid-state LiDAR processing in autonomous vehicles."},
    {"name": "ConnectX-V2X Transceiver","category": "Connectivity","description": "Vehicle-to-everything (V2X) communication transceiver for cooperative driving."},
    {"name": "SecureAuth TPM",         "category": "Security",    "description": "Trusted Platform Module for vehicle cybersecurity and secure boot."},
    {"name": "PixelDrive Display IC",  "category": "Display",     "description": "Display driver IC for automotive HMI instrument clusters."},
    {"name": "RF-5G Modem",            "category": "Connectivity","description": "5G modem chipset enabling high-bandwidth telematics and OTA updates."},
    {"name": "BMS-Controller",         "category": "Power",       "description": "Battery management system controller for monitoring EV cell voltages and temperatures."},
    {"name": "AudioMax DSP",           "category": "Audio",       "description": "Digital signal processor for in-cabin noise cancellation and premium audio."},
]

# ── Products ─────────────────────────────────────────────────────────────
PRODUCTS: list[dict] = [
    {"name": "DriveECU-500",       "type": "ECU",              "description": "Central powertrain ECU for electric and hybrid vehicles."},
    {"name": "ADAS-Platform X",    "type": "ADAS Module",      "description": "Level-3 autonomous driving module combining LiDAR ASIC and DDR5 memory."},
    {"name": "EV-Inverter Pro",    "type": "Power Module",     "description": "High-efficiency EV inverter using VPower-300 IGBTs for drivetrain."},
    {"name": "InCabin-360",        "type": "Infotainment",     "description": "Full-stack infotainment and digital cockpit system with display and audio DSP."},
    {"name": "TeleMatics Hub",     "type": "Connectivity Unit", "description": "Connected vehicle gateway providing 5G, V2X, and OTA update capability."},
    {"name": "BatteryGuard EV",    "type": "BMS",              "description": "Battery monitoring and protection system for 800V EV architectures."},
    {"name": "SecureDrive Module", "type": "Security",         "description": "Hardware security module integrating TPM for vehicle-level cybersecurity."},
    {"name": "ClusterVision HUD",  "type": "Display",          "description": "Augmented-reality head-up display system for next-gen instrument clusters."},
]

# ── Customers ────────────────────────────────────────────────────────────
CUSTOMERS: list[dict] = [
    {"name": "Acme Corp",          "industry": "Automotive OEM",     "region": "North America",  "description": "Major North American automaker producing electric trucks and SUVs."},
    {"name": "Velocity Motors",    "industry": "Automotive OEM",     "region": "Europe",         "description": "European premium EV manufacturer focused on autonomous luxury sedans."},
    {"name": "NovaDrive",          "industry": "Automotive OEM",     "region": "East Asia",      "description": "Fast-growing East Asian EV company specialising in affordable city cars."},
    {"name": "TerraFleet",         "industry": "Fleet Management",   "region": "North America",  "description": "Fleet management company operating 50 000+ connected commercial vehicles."},
    {"name": "OrionAero",          "industry": "Aerospace",          "region": "North America",  "description": "Aerospace tier-1 using automotive-grade MCUs in avionics subsystems."},
    {"name": "MediTech Devices",   "industry": "Medical Devices",    "region": "Europe",         "description": "Medical-device OEM using secure embedded controllers in diagnostic systems."},
]

# ── Risk Events ──────────────────────────────────────────────────────────
RISK_EVENTS: list[dict] = [
    {"name": "Chip Shortage at Factory A",        "severity": "Critical",  "description": "Prolonged wafer contamination incident halting production at a major semiconductor fab. Lead times extend from 12 to 52 weeks."},
    {"name": "Earthquake in East Asia",           "severity": "High",      "description": "Magnitude 7.2 earthquake near Tainan damages semiconductor fabs and disrupts logistics across East Asia for several weeks."},
    {"name": "Rare-Earth Export Ban",              "severity": "High",      "description": "Government export restrictions on rare-earth metals from Africa threaten substrate and magnet supply chains."},
    {"name": "Shipping Lane Disruption",           "severity": "Medium",    "description": "Congestion and security incidents in the Strait of Malacca delay container shipments from Southeast Asia by 3–6 weeks."},
    {"name": "Cybersecurity Breach at Supplier",   "severity": "Medium",    "description": "Ransomware attack on Supplier Epsilon's IT systems halts PCB shipments for two weeks."},
]

# ── Relationships ────────────────────────────────────────────────────────
# (source_label, source_name, rel_type, target_label, target_name, props)

RELATIONSHIPS: list[tuple[str, str, str, str, str, dict]] = [
    # Factory → Component (PRODUCES)
    ("Factory", "Factory A",  "PRODUCES", "Component", "NX-7 Microcontroller",    {"volume": "2M units/quarter"}),
    ("Factory", "Factory B",  "PRODUCES", "Component", "MemX-DDR5 Module",        {"volume": "5M units/quarter"}),
    ("Factory", "Factory C",  "PRODUCES", "Component", "VPower-300 IGBT",         {"volume": "800K units/quarter"}),
    ("Factory", "Factory D",  "PRODUCES", "Component", "ConnectX-V2X Transceiver",{"volume": "1M units/quarter"}),
    ("Factory", "Factory D",  "PRODUCES", "Component", "RF-5G Modem",             {"volume": "1.5M units/quarter"}),
    ("Factory", "Factory E",  "PRODUCES", "Component", "SensorIQ LiDAR ASIC",     {"volume": "500K units/quarter"}),
    ("Factory", "Factory F",  "PRODUCES", "Component", "SecureAuth TPM",          {"volume": "3M units/quarter"}),
    ("Factory", "Factory F",  "PRODUCES", "Component", "BMS-Controller",          {"volume": "1.2M units/quarter"}),
    ("Factory", "Factory B",  "PRODUCES", "Component", "PixelDrive Display IC",   {"volume": "2M units/quarter"}),
    ("Factory", "Factory E",  "PRODUCES", "Component", "AudioMax DSP",            {"volume": "1M units/quarter"}),

    # Supplier → Component (SUPPLIES)
    ("Supplier", "Supplier Alpha",   "SUPPLIES", "Component", "NX-7 Microcontroller",    {"material": "300mm silicon wafers"}),
    ("Supplier", "Supplier Delta",   "SUPPLIES", "Component", "NX-7 Microcontroller",    {"material": "EUV photoresist"}),
    ("Supplier", "Supplier Beta",    "SUPPLIES", "Component", "VPower-300 IGBT",         {"material": "Rare-earth substrate"}),
    ("Supplier", "Supplier Gamma",   "SUPPLIES", "Component", "SensorIQ LiDAR ASIC",     {"material": "Ceramic BGA substrate"}),
    ("Supplier", "Supplier Epsilon", "SUPPLIES", "Component", "ConnectX-V2X Transceiver",{"material": "HDI PCB"}),
    ("Supplier", "Supplier Zeta",    "SUPPLIES", "Component", "MemX-DDR5 Module",        {"material": "MLCCs and passives"}),
    ("Supplier", "Supplier Eta",     "SUPPLIES", "Component", "AudioMax DSP",             {"material": "Wire-bond packaging"}),
    ("Supplier", "Supplier Theta",   "SUPPLIES", "Component", "SecureAuth TPM",          {"material": "ATE test services"}),

    # Component → Product (USED_IN)   *** flagship: NX-7 → DriveECU-500 ***
    ("Component", "NX-7 Microcontroller",    "USED_IN", "Product", "DriveECU-500",       {}),
    ("Component", "NX-7 Microcontroller",    "USED_IN", "Product", "ADAS-Platform X",    {}),
    ("Component", "VPower-300 IGBT",         "USED_IN", "Product", "EV-Inverter Pro",    {}),
    ("Component", "MemX-DDR5 Module",        "USED_IN", "Product", "ADAS-Platform X",    {}),
    ("Component", "MemX-DDR5 Module",        "USED_IN", "Product", "InCabin-360",        {}),
    ("Component", "SensorIQ LiDAR ASIC",     "USED_IN", "Product", "ADAS-Platform X",    {}),
    ("Component", "ConnectX-V2X Transceiver","USED_IN", "Product", "TeleMatics Hub",     {}),
    ("Component", "RF-5G Modem",             "USED_IN", "Product", "TeleMatics Hub",     {}),
    ("Component", "SecureAuth TPM",          "USED_IN", "Product", "SecureDrive Module", {}),
    ("Component", "BMS-Controller",          "USED_IN", "Product", "BatteryGuard EV",    {}),
    ("Component", "PixelDrive Display IC",   "USED_IN", "Product", "ClusterVision HUD",  {}),
    ("Component", "PixelDrive Display IC",   "USED_IN", "Product", "InCabin-360",        {}),
    ("Component", "AudioMax DSP",            "USED_IN", "Product", "InCabin-360",        {}),

    # Product → Customer (SOLD_TO)  *** flagship: DriveECU-500 → Acme Corp ***
    ("Product", "DriveECU-500",       "SOLD_TO", "Customer", "Acme Corp",        {}),
    ("Product", "DriveECU-500",       "SOLD_TO", "Customer", "NovaDrive",        {}),
    ("Product", "ADAS-Platform X",    "SOLD_TO", "Customer", "Velocity Motors",  {}),
    ("Product", "ADAS-Platform X",    "SOLD_TO", "Customer", "Acme Corp",        {}),
    ("Product", "EV-Inverter Pro",    "SOLD_TO", "Customer", "Velocity Motors",  {}),
    ("Product", "EV-Inverter Pro",    "SOLD_TO", "Customer", "NovaDrive",        {}),
    ("Product", "InCabin-360",        "SOLD_TO", "Customer", "Acme Corp",        {}),
    ("Product", "TeleMatics Hub",     "SOLD_TO", "Customer", "TerraFleet",       {}),
    ("Product", "TeleMatics Hub",     "SOLD_TO", "Customer", "Acme Corp",        {}),
    ("Product", "SecureDrive Module", "SOLD_TO", "Customer", "OrionAero",        {}),
    ("Product", "BatteryGuard EV",    "SOLD_TO", "Customer", "Velocity Motors",  {}),
    ("Product", "BatteryGuard EV",    "SOLD_TO", "Customer", "NovaDrive",        {}),
    ("Product", "ClusterVision HUD",  "SOLD_TO", "Customer", "Acme Corp",        {}),

    # Entity → Region (LOCATED_IN)
    *[("Factory",  f["name"], "LOCATED_IN", "Region", f["region"], {}) for f in FACTORIES],
    *[("Supplier", s["name"], "LOCATED_IN", "Region", s["region"], {}) for s in SUPPLIERS],
    *[("Customer", c["name"], "LOCATED_IN", "Region", c["region"], {}) for c in CUSTOMERS],

    # Component → Supplier (HAS_ALTERNATIVE)
    ("Component", "NX-7 Microcontroller", "HAS_ALTERNATIVE", "Supplier", "Supplier Eta",   {"note": "Supplier Eta can package compatible MCU dies from Factory F as emergency alternative"}),
    ("Component", "VPower-300 IGBT",      "HAS_ALTERNATIVE", "Supplier", "Supplier Gamma",  {"note": "Supplier Gamma offers ceramic-substrate IGBTs as partial substitute"}),

    # RiskEvent → affected entities (AFFECTS)
    ("RiskEvent", "Chip Shortage at Factory A",       "AFFECTS", "Factory",   "Factory A",            {"impact": "Production halt of NX-7 MCU"}),
    ("RiskEvent", "Chip Shortage at Factory A",       "AFFECTS", "Component", "NX-7 Microcontroller", {"impact": "Lead time 12→52 weeks"}),
    ("RiskEvent", "Earthquake in East Asia",          "AFFECTS", "Region",    "East Asia",            {"impact": "Fab and logistics disruption"}),
    ("RiskEvent", "Earthquake in East Asia",          "AFFECTS", "Factory",   "Factory A",            {"impact": "Structural damage risk"}),
    ("RiskEvent", "Earthquake in East Asia",          "AFFECTS", "Factory",   "Factory B",            {"impact": "Power grid instability"}),
    ("RiskEvent", "Rare-Earth Export Ban",             "AFFECTS", "Supplier",  "Supplier Beta",        {"impact": "Supply cutoff of rare earths"}),
    ("RiskEvent", "Rare-Earth Export Ban",             "AFFECTS", "Component", "VPower-300 IGBT",      {"impact": "Substrate material shortage"}),
    ("RiskEvent", "Shipping Lane Disruption",          "AFFECTS", "Region",    "Southeast Asia",       {"impact": "3-6 week shipping delays"}),
    ("RiskEvent", "Cybersecurity Breach at Supplier",  "AFFECTS", "Supplier",  "Supplier Epsilon",     {"impact": "PCB shipments halted 2 weeks"}),
    ("RiskEvent", "Cybersecurity Breach at Supplier",  "AFFECTS", "Component", "ConnectX-V2X Transceiver", {"impact": "V2X module production delayed"}),
]
