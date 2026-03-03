# Shadow Litter — Policy Brief

## Autonomous Satellite Intelligence for Illegal Waste Detection in Madurai

---

### The Problem

Madurai generates **~1,800 tonnes/day** of municipal solid waste.
An estimated **30–40%** leaves the formal system and accumulates in
illegal dump sites on riverbeds, lakeshores, and urban margins.

**Consequences:**
- Vaigai River contamination (leachate seepage)
- Groundwater risk for 200,000+ households
- ₹12–18 crore/year in reactive remediation costs
- Public health burden: vector-borne disease hotspots

**The gap:** Illegal dumps are **invisible** to current monitoring systems
until they reach crisis scale. Field inspection covers <5% of risk areas annually.

---

### Our Solution

**shadow-litter** is an open-source satellite AI system that:

1. Downloads free Sentinel-2 imagery (10m resolution, every 5 days)
2. Runs a deep learning change detector on 5 priority zones
3. Identifies new dump sites automatically
4. Sends georeferenced alerts to ward officers via WhatsApp
5. Generates weekly PDF reports for the Corporation GIS team

**Deployment cost: ₹0**

---

### How It Works

```
Satellite imagery (ESA Copernicus — free)
        ↓
  Band stacking + atmospheric correction
        ↓
  Siamese neural network (change detection)
        ↓
  Dump site identification + classification
        ↓
  Alert → Ward Officer → Corporation Dashboard
```

---

### Sample Detection

| Field | Value |
|-------|-------|
| Zone | Vaigai Riverbed |
| Coordinates | 9.9259°N, 78.1198°E |
| First detected | 2024-03-15 |
| Area | 1,240 m² |
| Type | Fresh household waste |
| Confidence | 89% |
| Water body | Vaigai River (200m) |

---

### Our Ask

**Tier 1 — No budget ask:**
- Share contact for Madurai Corporation ICT/Environment desk
- Provide access to existing complaint data for validation

**Tier 2 — Integration:**
- API access to Madurai Smart City GIS platform
- WhatsApp number for ward-level alert routing

**Tier 3 — Scale:**
- ₹0 operating cost maintained
- Open-source — Coimbatore, Trichy can fork immediately

---

### Contact

**Project:** shadow-litter
**GitHub:** https://github.com/your-org/shadow-litter
**Demo:** https://huggingface.co/spaces/your-org/shadow-litter
**Email:** [your-email]

*Built with fury and satellite imagery. For Madurai.*
